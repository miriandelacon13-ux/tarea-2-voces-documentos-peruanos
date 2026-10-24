"""Ejecuta el OCR principal (PaddleOCR) sobre los 25 documentos usando la caché de ocr.py.

Uso: python scripts/06_ejecutar_ocr.py [--forzar]
Los errores por documento se registran (no se ocultan) y el proceso continúa.
El notebook 01_extraccion.ipynb lee la misma caché mediante las mismas funciones.
"""
from __future__ import annotations

import json
import sys
import time
import traceback

from ocr import CACHE_PADDLE, crear_paddle, ocr_paddle
from utilidades import RAW


def main() -> None:
    forzar = "--forzar" in sys.argv
    documentos = sorted((RAW / "documentos").iterdir())
    motor, t_carga = crear_paddle()
    print(f"PaddleOCR cargado en {t_carga:.1f} s", flush=True)
    t_total = time.perf_counter()
    for i, ruta in enumerate(documentos, 1):
        try:
            r = ocr_paddle(motor, ruta, forzar=forzar)
            print(f"[{i:02d}/{len(documentos)}] {ruta.name}: {r['n_lineas']} líneas, "
                  f"conf {r['confianza_media']}, {r['tiempo_ocr_seg']} s", flush=True)
        except Exception as e:  # registrar y seguir
            CACHE_PADDLE.mkdir(parents=True, exist_ok=True)
            (CACHE_PADDLE / f"{ruta.stem}.error.json").write_text(json.dumps(
                {"id": ruta.stem, "error": f"{type(e).__name__}: {e}", "traza": traceback.format_exc()},
                ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"[{i:02d}/{len(documentos)}] {ruta.name}: ERROR {type(e).__name__}: {e}", flush=True)
    print(f"FIN OCR: {time.perf_counter() - t_total:.1f} s", flush=True)


if __name__ == "__main__":
    main()
