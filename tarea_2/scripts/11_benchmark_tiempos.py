"""Medición controlada de tiempos sobre la muestra congelada (misma sesión, mismo equipo, sin
otros procesos pesados). No calcula CER/WER.

- ASR: faster-whisper small (misma configuración que la Parte 1) y Parakeet TDT v3, 1 pasada por clip
  tras un calentamiento con un clip fuera de la muestra. RTF = tiempo / duración del clip.
- OCR: PaddleOCR (configuración de la Parte 1) y Tesseract, 1 pasada por documento tras un
  calentamiento con un documento fuera de la muestra.
- Estabilidad: compara el texto obtenido ahora con el guardado en caché (ejecución anterior).
No sobrescribe las cachés de predicciones. Salida: datos/reportes/benchmark_tiempos.csv
Orden de importación: faster-whisper ANTES que paddle (conflicto de DLL en Windows).
"""
from __future__ import annotations

import json
import os
import platform
import time
from datetime import datetime

import numpy as np
import pandas as pd
import soundfile as sf

import asr
import asr_alternativo
import ocr
from utilidades import DATOS, RAW, REPORTES

CALENTAMIENTO_AUDIO = "aud_001"   # fuera de la muestra
CALENTAMIENTO_DOC = "doc_024"     # fuera de la muestra


def main() -> None:
    muestra = pd.read_csv(DATOS / "muestra_evaluacion.csv")
    clips = [RAW / "audio" / "clips" / a for a in muestra.loc[muestra["modalidad"] == "audio", "archivo"]]
    docs = [RAW / "documentos" / a for a in muestra.loc[muestra["modalidad"] == "documento", "archivo"]]
    filas = []
    entorno = f"{platform.processor()} · {os.cpu_count()} hilos · CPU"

    # ---------- ASR ----------
    whisper, t_carga_w = asr.cargar_modelo()
    parakeet, t_carga_p = asr_alternativo.cargar_modelo()
    filas += [{"modalidad": "audio", "modelo": "faster-whisper small", "id": "_carga_modelo", "tiempo_s": t_carga_w},
              {"modalidad": "audio", "modelo": "Parakeet TDT 0.6B v3", "id": "_carga_modelo", "tiempo_s": t_carga_p}]
    calent, _ = sf.read(str(RAW / "audio" / "clips" / f"{CALENTAMIENTO_AUDIO}.wav"), dtype="float32")
    list(whisper.transcribe(calent, **asr.OPCIONES)[0])
    s = parakeet.create_stream(); s.accept_waveform(16_000, calent); parakeet.decode_stream(s)
    for ruta in clips:
        x, _ = sf.read(str(ruta), dtype="float32")
        dur = len(x) / 16_000
        t0 = time.perf_counter()
        segs = list(whisper.transcribe(x, **asr.OPCIONES)[0])
        tw = time.perf_counter() - t0
        texto_w = " ".join(seg.text.strip() for seg in segs).strip()
        previo_w = json.loads((asr.CACHE / f"{ruta.stem}.json").read_text(encoding="utf-8"))["texto_asr"]
        filas.append({"modalidad": "audio", "modelo": "faster-whisper small", "id": ruta.stem, "tiempo_s": tw,
                      "duracion_audio_s": dur, "rtf": tw / dur, "texto_identico_a_cache": texto_w == previo_w})
        s = parakeet.create_stream(); s.accept_waveform(16_000, x)
        t0 = time.perf_counter(); parakeet.decode_stream(s); tp = time.perf_counter() - t0
        previo_p = json.loads((asr_alternativo.CACHE / f"{ruta.stem}.json").read_text(encoding="utf-8"))["texto_asr"]
        filas.append({"modalidad": "audio", "modelo": "Parakeet TDT 0.6B v3", "id": ruta.stem, "tiempo_s": tp,
                      "duracion_audio_s": dur, "rtf": tp / dur, "texto_identico_a_cache": s.result.text.strip() == previo_p})
        print(f"{ruta.stem}: whisper {tw:.1f} s · parakeet {tp:.1f} s", flush=True)

    # ---------- OCR ----------
    import pytesseract
    from PIL import Image
    pytesseract.pytesseract.tesseract_cmd = str(ocr.TESSERACT_EXE)
    os.environ["TESSDATA_PREFIX"] = str(ocr.TESSDATA)
    cfg_t = f'--psm {ocr.CONFIG_TESSERACT["psm"]} --oem {ocr.CONFIG_TESSERACT["oem"]}'
    motor, t_carga_o = ocr.crear_paddle()
    filas.append({"modalidad": "documento", "modelo": "PaddleOCR", "id": "_carga_modelo", "tiempo_s": t_carga_o})
    rgb_c, _ = ocr.cargar_imagen(RAW / "documentos" / f"{CALENTAMIENTO_DOC}.jpg")
    motor.predict(rgb_c[:, :, ::-1].copy())
    pytesseract.image_to_data(Image.fromarray(rgb_c), lang="spa", config=cfg_t)
    for ruta in docs:
        rgb, _ = ocr.cargar_imagen(ruta)
        t0 = time.perf_counter()
        r = motor.predict(rgb[:, :, ::-1].copy())[0]
        tpad = time.perf_counter() - t0
        previo = json.loads((ocr.CACHE_PADDLE / f"{ruta.stem}.json").read_text(encoding="utf-8"))["texto_ocr"]
        filas.append({"modalidad": "documento", "modelo": "PaddleOCR", "id": ruta.stem, "tiempo_s": tpad,
                      "texto_identico_a_cache": "\n".join(r["rec_texts"]) == previo})
        t0 = time.perf_counter()
        pytesseract.image_to_data(Image.fromarray(rgb), lang="spa", config=cfg_t, output_type=pytesseract.Output.DICT)
        ttes = time.perf_counter() - t0
        filas.append({"modalidad": "documento", "modelo": "Tesseract", "id": ruta.stem, "tiempo_s": ttes})
        print(f"{ruta.stem}: paddle {tpad:.1f} s · tesseract {ttes:.1f} s", flush=True)

    df = pd.DataFrame(filas)
    df["fecha"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    df["entorno"] = entorno
    df.to_csv(REPORTES / "benchmark_tiempos.csv", index=False, encoding="utf-8")
    resumen = df[df["id"] != "_carga_modelo"].groupby(["modalidad", "modelo"]).agg(
        tiempo_mediano_s=("tiempo_s", "median"), tiempo_total_s=("tiempo_s", "sum"), rtf_mediano=("rtf", "median"))
    print(resumen.round(3).to_string())
    print("FIN BENCHMARK", flush=True)


if __name__ == "__main__":
    main()
