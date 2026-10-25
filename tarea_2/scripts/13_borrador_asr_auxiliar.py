"""Borrador de referencias de AUDIO con un ASR AUXILIAR que NO se evalúa (opción B elegida por la autora).

- Modelo: jonatasgrosman/wav2vec2-large-xlsr-53-spanish (Apache-2.0), CTC sin modelo de lenguaje,
  revisión fijada en REVISION. Arquitectura y entrenamiento distintos de Whisper y Parakeet.
- NO se usa el texto de faster-whisper ni de Parakeet (son los modelos evaluados: usarlos haría
  circular el WER). Su desacuerdo solo se usa en el reporte para señalar audios inseguros.
- Se procesa cada fragmento (<= 15 s, cortado en pausas) de datos/raw/referencias/apoyo/<id>/; cada
  línea del borrador lleva su marca [mm:ss–mm:ss] (los corchetes se eliminan al normalizar el WER).
- Una palabra se acepta solo si (a) su confianza (media de la probabilidad máxima CTC en sus tramas)
  es >= UMBRAL y (b) existe en el léxico español de spaCy es_core_news_md (342 369 formas, exportado a
  datos/raw/referencias/apoyo/lexico_es_core_news_md.txt). Si no, se escribe [inaudible] (consecutivos
  se agrupan). El filtro (b) se añadió porque CTC es sobreconfiado: en la primera pasada producía
  no-palabras con confianza alta (p. ej., en aud_019, con música). Efecto: nombres propios o topónimos
  ausentes del léxico también quedan [inaudible] y deben resolverse al escuchar.
- Estado: GENERADO_ASISTIDO_POR_ASR_PENDIENTE_REVISION. NO es una referencia humana: debe escucharse
  y corregirse por completo antes de marcar REVISADO_HUMANAMENTE.
- Nunca sobrescribe un archivo que ya tenga texto (protege ediciones humanas), salvo --forzar.

Entorno: Python global con torch 2.14.1+cpu y transformers 5.20.1 (no el .venv del proyecto, para no
mezclar torch con paddle). Uso: python scripts/13_borrador_asr_auxiliar.py [--forzar]
"""
from __future__ import annotations

import sys
import time
import wave
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import transformers
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

RAIZ = Path(__file__).resolve().parents[1]
RAW, REPORTES = RAIZ / "datos" / "raw", RAIZ / "datos" / "reportes"
MODELO = "jonatasgrosman/wav2vec2-large-xlsr-53-spanish"
REVISION = "96d7e9b4e4a7"  # prefijo del commit del repositorio en Hugging Face (se resuelve al completo)
UMBRAL = 0.5
PENDIENTE = "PENDIENTE_REVISION_HUMANA"
ESTADO = "GENERADO_ASISTIDO_POR_ASR_PENDIENTE_REVISION"
METODO = (f"borrador ASR auxiliar: {MODELO} (Apache-2.0, CTC greedy) + filtro de confianza >= {UMBRAL} "
          "y léxico es_core_news_md; sin usar Whisper ni Parakeet")
LEXICO = RAW / "referencias" / "apoyo" / "lexico_es_core_news_md.txt"


def leer_wav(ruta: Path) -> np.ndarray:
    with wave.open(str(ruta)) as w:
        assert w.getframerate() == 16_000 and w.getnchannels() == 1
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768


def transcribir_fragmento(modelo, procesador, x: np.ndarray) -> tuple[list[str], list[float]]:
    entrada = procesador(x, sampling_rate=16_000, return_tensors="pt")
    with torch.inference_mode():
        logits = modelo(entrada.input_values).logits[0]
    probs = torch.softmax(logits, dim=-1)
    ids = torch.argmax(logits, dim=-1)
    salida = procesador.tokenizer.decode(ids.tolist(), output_word_offsets=True)
    palabras, confianzas = [], []
    pmax = probs.max(dim=-1).values.numpy()
    for w in salida.word_offsets:
        conf = float(pmax[w["start_offset"]: max(w["end_offset"], w["start_offset"] + 1)].mean())
        palabras.append(w["word"])
        confianzas.append(conf)
    return palabras, confianzas


def main() -> None:
    forzar = "--forzar" in sys.argv
    muestra = pd.read_csv(RAIZ / "datos" / "muestra_evaluacion.csv")
    ids = muestra.loc[muestra["modalidad"] == "audio", "id"].tolist()
    cache = RAIZ / "modelos" / "hf_aux"
    t0 = time.perf_counter()
    procesador = Wav2Vec2Processor.from_pretrained(MODELO, revision=REVISION, cache_dir=cache)
    modelo = Wav2Vec2ForCTC.from_pretrained(MODELO, revision=REVISION, cache_dir=cache).eval()
    print(f"Modelo cargado en {time.perf_counter() - t0:.1f} s (torch {torch.__version__}, "
          f"transformers {transformers.__version__})", flush=True)

    desacuerdo = pd.read_csv(REPORTES / "desacuerdo_asr_muestra.csv").set_index("id")["desacuerdo_relativo"]
    lexico = set(LEXICO.read_text(encoding="utf-8").split())
    filas = []
    for i in ids:
        ref = RAW / "referencias" / "audio" / f"{i}.txt"
        actual = ref.read_text(encoding="utf-8").strip() if ref.exists() else ""
        if actual and actual != PENDIENTE and not forzar:
            print(f"{i}: ya tiene texto; NO se sobrescribe", flush=True)
            continue
        carpeta = RAW / "referencias" / "apoyo" / i
        tiempos = (carpeta / "plantilla_con_tiempos.txt").read_text(encoding="utf-8").split("\n")
        tiempos = [t.strip() for t in tiempos if t.strip()]
        fragmentos = sorted(carpeta.glob("fragmento_*.wav"))
        assert len(tiempos) == len(fragmentos), f"{i}: plantilla y fragmentos no coinciden"
        lineas, todas_conf, n_inaudible, n_palabras, n_fuera_lexico = [], [], 0, 0, 0
        t1 = time.perf_counter()
        for marca, frag in zip(tiempos, fragmentos):
            palabras, conf = transcribir_fragmento(modelo, procesador, leer_wav(frag))
            texto = []
            for w, c in zip(palabras, conf):
                n_fuera_lexico += w.lower() not in lexico
                if c < UMBRAL or w.lower() not in lexico:
                    if not texto or texto[-1] != "[inaudible]":
                        texto.append("[inaudible]")
                        n_inaudible += 1
                else:
                    texto.append(w)
                    n_palabras += 1
            todas_conf += conf
            lineas.append(f"{marca} {' '.join(texto) if texto else '[inaudible]'}")
            if not texto:
                n_inaudible += 1
        ref.write_text("\n".join(lineas) + "\n", encoding="utf-8")
        filas.append({
            "id_audio": i, "archivo_txt": ref.relative_to(RAIZ).as_posix(), "metodo_usado": METODO,
            "estado": ESTADO, "n_fragmentos": len(fragmentos), "n_palabras": n_palabras,
            "n_inaudible": n_inaudible, "palabras_fuera_de_lexico": n_fuera_lexico,
            "pct_palabras_aceptadas": round(100 * n_palabras / max(1, len(todas_conf)), 1),
            "confianza_media": round(float(np.mean(todas_conf)), 3) if todas_conf else None,
            "pct_palabras_baja_confianza": round(100 * float(np.mean(np.array(todas_conf) < UMBRAL)), 1) if todas_conf else None,
            "desacuerdo_whisper_parakeet": desacuerdo.get(i), "tiempo_s": round(time.perf_counter() - t1, 1),
            "fecha": date.today().isoformat(),
        })
        print(f"{i}: {n_palabras} palabras, {n_inaudible} [inaudible], conf. media {filas[-1]['confianza_media']}", flush=True)

    if filas:
        df = pd.DataFrame(filas)
        df.to_csv(REPORTES / "borradores_audio_aux.csv", index=False, encoding="utf-8")
        control = pd.read_csv(REPORTES / "control_referencias.csv")
        hechos = set(df["id_audio"])
        control.loc[control["id"].isin(hechos), "estado"] = ESTADO
        control.loc[control["id"].isin(hechos), "origen_referencia"] = (
            METODO + "; requiere escucha y corrección humana completa antes de REVISADO_HUMANAMENTE")
        control.to_csv(REPORTES / "control_referencias.csv", index=False, encoding="utf-8")
    print(f"FIN: {len(filas)} borradores generados", flush=True)


if __name__ == "__main__":
    main()
