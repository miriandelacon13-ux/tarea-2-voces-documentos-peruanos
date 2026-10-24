"""Normaliza los audios originales y valida sus duraciones reales.

Incidencia documentada: los WebM A–D (grabados con VLC) tienen timestamps que
empiezan en ~65 000–78 000 s (offset constante de 18–22 h) y el contenedor no
declara duración (Duration ausente). Wikimedia Commons estima la duración como
tamaño_archivo × 8 / 128 kbps, ignorando que ~78 % de los bytes son video VP8,
por lo que sobrestima la duración del audio.

Procedimiento (sin modificar originales):
1. ffprobe: start_time, duración del contenedor y streams.
2. Duración real = muestras decodificadas / frecuencia de muestreo.
3. Copia normalizada: solo pista de audio, timestamps reiniciados a 0
   (asetpts=PTS-STARTPTS), FLAC 16 bit, frecuencia y canales originales.
4. Validación: la copia normalizada debe tener start_time 0 y la misma
   duración decodificada que el original (tolerancia 50 ms).
"""
from __future__ import annotations

import subprocess

import pandas as pd

from utilidades import RAW, REPORTES, a_float, binario, ffprobe

CARPETAS_ORIGEN = [RAW / "audio" / "originales", RAW / "audio" / "adicionales"]  # adicionales: F y G (OGG)
NORMALIZADOS = RAW / "audio" / "normalizados"
TOLERANCIA_S = 0.05


def duracion_decodificada(ruta) -> tuple[float, int]:
    """Decodifica la primera pista de audio a PCM y cuenta muestras (sin remuestrear)."""
    sr = int(next(s for s in ffprobe(ruta)["streams"] if s["codec_type"] == "audio")["sample_rate"])
    proc = subprocess.Popen(
        [binario("ffmpeg"), "-nostdin", "-v", "error", "-i", str(ruta), "-map", "0:a:0",
         "-ac", "1", "-f", "s16le", "-"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    total = 0
    while bloque := proc.stdout.read(1 << 20):
        total += len(bloque)
    errores = proc.stderr.read().decode("utf-8", "replace").strip()
    if proc.wait() != 0 or errores:
        raise RuntimeError(f"Error al decodificar {ruta.name}: {errores}")
    muestras = total // 2
    return muestras / sr, sr


def normalizar(origen, destino) -> str:
    if destino.exists():
        return "ya_existia"
    subprocess.run(
        [binario("ffmpeg"), "-nostdin", "-hide_banner", "-v", "error", "-n", "-i", str(origen),
         "-map", "0:a:0", "-vn", "-sn", "-dn", "-map_metadata", "-1",
         "-af", "asetpts=PTS-STARTPTS", "-c:a", "flac", "-sample_fmt", "s16",
         "-metadata", f"comment=Normalizado desde {origen.name}: solo audio, timestamps desde 0",
         str(destino)],
        check=True,
    )
    return "creado"


def info_audio(ruta) -> dict:
    datos = ffprobe(ruta)
    audio = next(s for s in datos["streams"] if s["codec_type"] == "audio")
    return {
        "start_time": a_float(datos["format"].get("start_time")),
        "duracion_ffprobe": a_float(datos["format"].get("duration")),
        "codec": audio["codec_name"],
        "sample_rate": int(audio["sample_rate"]),
        "canales": audio["channels"],
        "streams": "; ".join(f"{s['codec_type']}:{s['codec_name']}" for s in datos["streams"]),
    }


def main() -> None:
    NORMALIZADOS.mkdir(parents=True, exist_ok=True)
    commons = pd.read_csv(REPORTES / "fuentes_audio_commons.csv").set_index("archivo_local")
    filas = []
    origenes = sorted((p for c in CARPETAS_ORIGEN if c.exists() for p in c.iterdir() if p.is_file()),
                      key=lambda p: p.name)
    for origen in origenes:
        destino = NORMALIZADOS / f"{origen.stem}.flac"
        o = info_audio(origen)
        dur_o, _ = duracion_decodificada(origen)
        accion = normalizar(origen, destino)
        n = info_audio(destino)
        dur_n, _ = duracion_decodificada(destino)
        diferencia = dur_n - dur_o
        ok = abs(diferencia) <= TOLERANCIA_S and (n["start_time"] or 0) == 0
        filas.append({
            "archivo_original": origen.name,
            "carpeta_origen": origen.parent.name,
            "titulo_commons": commons.loc[origen.name, "titulo_commons"],
            "streams_original": o["streams"],
            "start_time_original_s": o["start_time"],
            "duracion_ffprobe_contenedor_s": o["duracion_ffprobe"],
            "duracion_decodificada_original_s": round(dur_o, 3),
            "duracion_commons_declarada_s": round(float(commons.loc[origen.name, "duracion_commons_declarada_s"]), 3),
            "archivo_normalizado": destino.name,
            "formato_normalizado": f"{n['codec']} {n['sample_rate']} Hz {n['canales']} ch",
            "start_time_normalizado_s": n["start_time"],
            "duracion_ffprobe_normalizada_s": round(n["duracion_ffprobe"], 3),
            "duracion_decodificada_normalizada_s": round(dur_n, 3),
            "diferencia_norm_vs_original_s": round(diferencia, 3),
            "accion": accion,
            "estado": "OK" if ok else "REVISAR",
        })
    df = pd.DataFrame(filas)
    df.to_csv(REPORTES / "validacion_audio_originales.csv", index=False, encoding="utf-8")
    pd.set_option("display.width", 250)
    print(df.drop(columns=["titulo_commons", "carpeta_origen", "streams_original", "formato_normalizado", "accion"])
          .to_string(index=False))
    total = df["duracion_decodificada_normalizada_s"].sum()
    print(f"\nDuración real total: {total:.1f} s = {total / 60:.2f} min | "
          f"según Commons: {df['duracion_commons_declarada_s'].sum() / 60:.2f} min")


if __name__ == "__main__":
    main()
