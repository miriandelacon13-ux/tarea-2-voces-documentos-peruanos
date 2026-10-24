"""Genera los clips WAV (mono, 16 kHz, PCM 16 bit) desde las copias normalizadas y los valida.

Diseño (reproducible y sin selección a conveniencia):
- Los clips se generan por LOTES. El lote 1 (A–E, aud_001–aud_020) está congelado: al
  re-ejecutar se verifica que cada WAV sea idéntico y nunca se sobrescribe. Los lotes
  posteriores reciben IDs nuevos a continuación (aud_021, ...).
- Lote 1: 20 clips repartidos entre fuentes en proporción a su duración (resto mayor).
  Lotes siguientes: round(duración / DURACION_OBJETIVO_S) clips por fuente.
- Cada fuente se segmenta de forma CONTIGUA (cubre el 100 % del audio).
- Cada corte interno se desplaza a la pausa de menor energía dentro de ±VENTANA_AJUSTE_S
  para no partir palabras.
- Downmix a mono y remuestreo a 16 kHz con libswresample (FFmpeg, opciones por defecto).
- No se asigna número de hablantes: se determinará con diarización y revisión humana.

Validación de cada WAV: ffprobe (códec, frecuencia, canales, duración), decodificación
completa sin errores y nivel RMS (detecta archivos silenciosos).
Los clips defectuosos antiguos (Tarea2_Python/audio/clips) se registran como
descartados en datos/reportes/descartes_audio.csv; no se borran ni se versionan.
"""
from __future__ import annotations

import subprocess
import wave
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from utilidades import DESCARGAS, RAW, REPORTES, a_float, binario, ffprobe, sha256

NORMALIZADOS = RAW / "audio" / "normalizados"
CLIPS = RAW / "audio" / "clips"
CLIPS_ANTIGUOS = DESCARGAS / "audio" / "clips"
LOTES = [
    {"lote": 1, "fuentes": ["audio_A", "audio_B", "audio_C", "audio_D", "audio_E"], "n_clips": 20},
    {"lote": 2, "fuentes": ["audio_F", "audio_G"], "n_clips": None},  # audio adicional (00b_...)
]
DURACION_OBJETIVO_S = 75.0  # ≈ duración media de los clips del lote 1 (75,8 s)
SR = 16_000
VENTANA_AJUSTE_S = 4.0
DURACION_MINIMA_S = 10.0
UMBRAL_SILENCIO_DBFS = -50.0
UMBRAL_FRAME_ENERGIA_DBFS = -40.0


def decodificar_16k_mono(ruta) -> np.ndarray:
    salida = subprocess.run(
        [binario("ffmpeg"), "-nostdin", "-v", "error", "-i", str(ruta), "-map", "0:a:0",
         "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
        capture_output=True, check=True,
    )
    if salida.stderr.strip():
        raise RuntimeError(salida.stderr.decode("utf-8", "replace"))
    return np.frombuffer(salida.stdout, dtype=np.int16)


def asignar_clips(duraciones: dict[str, float], total: int) -> dict[str, int]:
    """Reparto proporcional por el método del resto mayor (al menos 1 clip por fuente)."""
    suma = sum(duraciones.values())
    cuotas = {k: total * d / suma for k, d in duraciones.items()}
    asignacion = {k: max(1, int(c)) for k, c in cuotas.items()}
    restos = sorted(cuotas, key=lambda k: cuotas[k] - int(cuotas[k]), reverse=True)
    for k in restos[: total - sum(asignacion.values())]:
        asignacion[k] += 1
    return asignacion


def energia_suavizada(x: np.ndarray, paso: int = 160, ventana_suave: int = 30) -> np.ndarray:
    """RMS por tramos de 10 ms suavizado con media móvil de 300 ms."""
    n = len(x) // paso
    tramos = x[: n * paso].astype(np.float64).reshape(n, paso)
    rms = np.sqrt((tramos**2).mean(axis=1))
    return np.convolve(rms, np.ones(ventana_suave) / ventana_suave, mode="same")


def cortes_en_pausas(x: np.ndarray, k: int) -> list[int]:
    """Límites (en muestras) de k segmentos contiguos con cortes internos en pausas."""
    energia = energia_suavizada(x)
    nominales = np.linspace(0, len(x), k + 1)
    cortes = [0]
    for t in nominales[1:-1]:
        centro = int(t) // 160
        radio = int(VENTANA_AJUSTE_S * SR) // 160
        a, b = max(0, centro - radio), min(len(energia), centro + radio)
        cortes.append((a + int(np.argmin(energia[a:b]))) * 160)
    cortes.append(len(x))
    return cortes


def dbfs(x: np.ndarray) -> float:
    rms = np.sqrt(np.mean(x.astype(np.float64) ** 2)) / 32768
    return float(20 * np.log10(rms)) if rms > 0 else float("-inf")


def escribir_wav(ruta, muestras: np.ndarray) -> str:
    if ruta.exists():
        with wave.open(str(ruta)) as w:
            existente = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
        if not np.array_equal(existente, muestras):
            raise RuntimeError(f"{ruta.name} ya existe con contenido distinto; no se sobrescribe.")
        return "ya_existia_identico"
    with wave.open(str(ruta), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(muestras.tobytes())
    return "creado"


def validar_wav(ruta, duracion_esperada: float) -> dict:
    datos = ffprobe(ruta)
    s = datos["streams"][0]
    duracion = a_float(datos["format"]["duration"])
    prueba = subprocess.run([binario("ffmpeg"), "-nostdin", "-v", "error", "-i", str(ruta), "-f", "null", "-"],
                            capture_output=True, text=True)
    decodifica = prueba.returncode == 0 and not prueba.stderr.strip()
    with wave.open(str(ruta)) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    tramos = x[: len(x) // 320 * 320].reshape(-1, 320).astype(np.float64)
    frames_db = 20 * np.log10(np.sqrt((tramos**2).mean(axis=1)) / 32768 + 1e-12)
    fila = {
        "codec": s["codec_name"], "sample_rate": int(s["sample_rate"]), "canales": s["channels"],
        "duracion_real_s": round(duracion, 3), "duracion_real_min": round(duracion / 60, 2),
        "tamano_bytes": ruta.stat().st_size, "tamano_mb": round(ruta.stat().st_size / 1024**2, 2),
        "sha256": sha256(ruta),
        "rms_dbfs": round(dbfs(x), 1),
        "pct_tramos_con_energia": round(float((frames_db > UMBRAL_FRAME_ENERGIA_DBFS).mean() * 100), 1),
        "silencio": bool(dbfs(x) < UMBRAL_SILENCIO_DBFS),
        "decodifica_sin_error": decodifica,
    }
    problemas = []
    if (fila["codec"], fila["sample_rate"], fila["canales"]) != ("pcm_s16le", SR, 1):
        problemas.append("formato incorrecto")
    if not decodifica:
        problemas.append("error al decodificar")
    if duracion < DURACION_MINIMA_S:
        problemas.append(f"duración < {DURACION_MINIMA_S:.0f} s")
    if abs(duracion - duracion_esperada) > 0.01:
        problemas.append("duración distinta a la esperada")
    if fila["silencio"]:
        problemas.append("silencioso")
    fila["valido"] = not problemas
    fila["observacion"] = "; ".join(problemas)
    return fila


def registrar_clips_antiguos() -> pd.DataFrame:
    filas = []
    for ruta in sorted(CLIPS_ANTIGUOS.glob("*.wav")):
        with wave.open(str(ruta)) as w:
            dur = w.getnframes() / w.getframerate()
        defectuoso = dur < DURACION_MINIMA_S
        filas.append({
            "id": ruta.stem, "modalidad": "audio",
            "ruta": ruta.relative_to(DESCARGAS).as_posix(), "sha256": sha256(ruta),
            "duracion_s": round(dur, 3),
            "motivo": ("clip vacío (3–13 ms): corte original falló por el offset de timestamps "
                       "(~18–22 h) de los WebM grabados con VLC; duplicado exacto de otros clips")
            if defectuoso else "clip válido de la segmentación anterior, sustituido por la nueva segmentación",
            "decision": "descartado; reemplazado por clips regenerados desde audio normalizado; "
                        "se conserva fuera del repositorio, no se versiona",
            "fecha": date.today().isoformat(),
        })
    df = pd.DataFrame(filas)
    salida = REPORTES / "descartes_audio.csv"
    if salida.exists():  # conservar la fecha de la decisión original
        previas = pd.read_csv(salida)
        if "fecha" in previas:
            fechas = previas.set_index("id")["fecha"]
            df["fecha"] = [fechas.get(i, f) if pd.notna(fechas.get(i)) else f for i, f in zip(df["id"], df["fecha"])]
    df.to_csv(salida, index=False, encoding="utf-8")
    return df


def clips_por_fuente(lote: dict, duraciones: dict[str, float]) -> dict[str, int]:
    if lote["n_clips"]:
        return asignar_clips(duraciones, lote["n_clips"])
    return {f: max(1, round(d / DURACION_OBJETIVO_S)) for f, d in duraciones.items()}


def main() -> None:
    CLIPS.mkdir(parents=True, exist_ok=True)
    fuentes = pd.read_csv(REPORTES / "fuentes_audio_commons.csv")
    fuentes = fuentes.set_index(fuentes["archivo_local"].map(lambda a: Path(a).stem))

    filas, n = [], 0
    for lote in LOTES:
        audios = {f: decodificar_16k_mono(NORMALIZADOS / f"{f}.flac") for f in lote["fuentes"]}
        asignacion = clips_por_fuente(lote, {f: len(x) / SR for f, x in audios.items()})
        print(f"Lote {lote['lote']} – clips por fuente: {asignacion}")
        for fuente, x in audios.items():
            cortes = cortes_en_pausas(x, asignacion[fuente])
            for j in range(asignacion[fuente]):
                n += 1
                id_clip = f"aud_{n:03d}"
                ruta = CLIPS / f"{id_clip}.wav"
                segmento = x[cortes[j]: cortes[j + 1]]
                accion = escribir_wav(ruta, segmento)
                fila = {
                    "id": id_clip, "lote": lote["lote"], "archivo": ruta.name,
                    "fuente": fuentes.loc[fuente, "archivo_local"],
                    "titulo_fuente": fuentes.loc[fuente, "titulo_commons"],
                    "licencia": fuentes.loc[fuente, "licencia"],
                    "segmento_en_fuente": f"{j + 1}/{asignacion[fuente]}",
                    "inicio_s": round(cortes[j] / SR, 3), "fin_s": round(cortes[j + 1] / SR, 3),
                    "accion": accion,
                }
                fila |= validar_wav(ruta, len(segmento) / SR)
                filas.append(fila)

    df = pd.DataFrame(filas)
    primeros = df.drop_duplicates("sha256").set_index("sha256")["id"]
    df["duplicado_de"] = [primeros[h] if primeros[h] != i else "" for h, i in zip(df["sha256"], df["id"])]
    df["duplicado"] = df["duplicado_de"] != ""
    df.loc[df["duplicado"], "valido"] = False
    df.to_csv(REPORTES / "clips_audio.csv", index=False, encoding="utf-8")

    pd.set_option("display.width", 250)
    print(df[["id", "lote", "fuente", "inicio_s", "duracion_real_s", "duracion_real_min", "tamano_mb", "rms_dbfs",
              "pct_tramos_con_energia", "decodifica_sin_error", "valido", "duplicado", "silencio", "licencia",
              "accion"]].to_string(index=False))
    print("\nDuración real por fuente (min):")
    print(df.groupby("fuente")["duracion_real_s"].agg(clips="count", minutos=lambda s: round(s.sum() / 60, 2))
          .to_string())
    validos = df[df["valido"]]
    total = validos["duracion_real_s"].sum()
    print(f"\nTOTAL CLIPS: {len(df)} (válidos: {len(validos)}) | TOTAL MINUTOS REALES: {total / 60:.2f} | "
          f"≥20 clips: {'CUMPLE' if len(validos) >= 20 else 'NO CUMPLE'} | "
          f"≥30 min: {'CUMPLE' if total >= 1800 else 'NO CUMPLE'}")

    if df["valido"].all():
        antiguos = registrar_clips_antiguos()
        print(f"Clips antiguos registrados como descartados: {len(antiguos)} (datos/reportes/descartes_audio.csv)")


if __name__ == "__main__":
    main()
