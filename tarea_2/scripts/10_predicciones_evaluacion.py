"""Genera las predicciones de los modelos ALTERNATIVOS sobre la muestra congelada (sin métricas).

- Tesseract 5.4 (spa) sobre los 10 documentos de datos/muestra_evaluacion.csv.
- Parakeet TDT 0.6B v3 sobre los 10 clips de la misma muestra.
Los modelos principales (PaddleOCR, faster-whisper) ya tienen sus salidas en la caché de la Parte 1.
NO calcula CER/WER: eso ocurre en 02_evaluacion.ipynb y solo con referencias humanas completas.
Uso: python scripts/10_predicciones_evaluacion.py [--ocr] [--asr] [--forzar]
"""
from __future__ import annotations

import sys

import pandas as pd

from utilidades import DATOS, RAW


def main() -> None:
    args = set(sys.argv[1:])
    forzar = "--forzar" in args
    muestra = pd.read_csv(DATOS / "muestra_evaluacion.csv")
    if "--ocr" in args or not args - {"--forzar"}:
        import ocr
        for a in muestra.loc[muestra["modalidad"] == "documento", "archivo"]:
            r = ocr.ocr_tesseract(RAW / "documentos" / a, forzar=forzar)
            print(f"Tesseract {r['id']}: {r['n_palabras']} palabras, conf {r['confianza_media']}, {r['tiempo_ocr_seg']} s",
                  flush=True)
    if "--asr" in args or not args - {"--forzar"}:
        import asr_alternativo
        modelo, t = asr_alternativo.cargar_modelo()
        print(f"Parakeet cargado en {t:.1f} s", flush=True)
        for a in muestra.loc[muestra["modalidad"] == "audio", "archivo"]:
            r = asr_alternativo.transcribir(modelo, RAW / "audio" / "clips" / a, forzar=forzar)
            print(f"Parakeet {r['id']}: {r['duracion_seg']} s, {len(r['texto_asr'].split())} palabras, "
                  f"RTF {r['rtf']}", flush=True)


if __name__ == "__main__":
    main()
