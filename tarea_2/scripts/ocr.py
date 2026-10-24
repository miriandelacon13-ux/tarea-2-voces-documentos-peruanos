"""OCR principal con PaddleOCR (con caché por documento) y OCR alternativo con Tesseract.

PaddleOCR — configuración usada:
- paddleocr 3.7.0 / paddlepaddle 3.3.1 (CPU), lang="es" -> modelos PP-OCRv6_medium_det + PP-OCRv6_medium_rec.
- use_doc_orientation_classify=False, use_doc_unwarping=False, use_textline_orientation=False:
  no se aplican transformaciones geométricas (misma imagen de entrada que Tesseract).
- enable_mkldnn=False: con oneDNN, paddlepaddle 3.3.1 falla en CPU
  ("ConvertPirAttribute2RuntimeAttribute not support"); se desactiva en lugar de cambiar versiones.
- Detección con parámetros por defecto (limit_side_len=64/min, max_side_limit=4000: el detector
  reduce internamente imágenes con lado > 4000 px; el reconocimiento usa la imagen original).
- Texto final: líneas en el orden devuelto por PaddleOCR (arriba->abajo, izquierda->derecha), unidas con "\n".

Preprocesamiento (único): imágenes con canal alfa se componen sobre fondo blanco y pasan a RGB.
Los originales nunca se modifican.

IMPORTANTE (Windows): importar faster_whisper/ctranslate2 ANTES que paddle; en el orden inverso
ctranslate2 falla con "WinError 127" por conflicto de DLL.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

from utilidades import RAIZ, RAW

Image.MAX_IMAGE_PIXELS = None  # doc_025 (~93 MP) es un escaneo legítimo

CACHE_PADDLE = RAW / "cache" / "ocr_paddleocr"
CACHE_TESSERACT = RAW / "cache" / "ocr_tesseract"
os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(RAIZ / "modelos" / "paddlex"))
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

CONFIG_PADDLE = {"lang": "es", "use_doc_orientation_classify": False, "use_doc_unwarping": False,
                 "use_textline_orientation": False, "enable_mkldnn": False}
MODELOS_PADDLE = "PP-OCRv6_medium_det + PP-OCRv6_medium_rec"

TESSERACT_EXE = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
TESSDATA = RAIZ / "modelos" / "tessdata"  # spa.traineddata de tessdata_best 4.1.0
CONFIG_TESSERACT = {"lang": "spa", "psm": 3, "oem": 1}  # segmentación automática, motor LSTM


def cargar_imagen(ruta: Path) -> tuple[np.ndarray, str]:
    """Imagen RGB uint8 y descripción del preprocesamiento aplicado."""
    with Image.open(ruta) as im:
        im = ImageOps.exif_transpose(im)
        if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
            im = im.convert("RGBA")
            alfa = np.asarray(im.getchannel("A"))
            if alfa.min() < 255:
                fondo = Image.new("RGBA", im.size, (255, 255, 255, 255))
                return np.asarray(Image.alpha_composite(fondo, im).convert("RGB")), \
                    "RGBA compuesto sobre fondo blanco -> RGB"
            return np.asarray(im.convert("RGB")), "canal alfa opaco descartado -> RGB"
        return np.asarray(im.convert("RGB")), "ninguno"


def crear_paddle():
    from paddleocr import PaddleOCR
    t0 = time.perf_counter()
    motor = PaddleOCR(**CONFIG_PADDLE)
    return motor, time.perf_counter() - t0


def _leer_cache(cache: Path, forzar: bool):
    if cache.exists() and not forzar:
        return json.loads(cache.read_text(encoding="utf-8"))
    return None


def ocr_paddle(motor, ruta: Path, forzar: bool = False) -> dict:
    import paddle
    import paddleocr
    CACHE_PADDLE.mkdir(parents=True, exist_ok=True)
    cache = CACHE_PADDLE / f"{ruta.stem}.json"
    if (previo := _leer_cache(cache, forzar)) is not None:
        return previo
    rgb, prepro = cargar_imagen(ruta)
    t0 = time.perf_counter()
    r = motor.predict(rgb[:, :, ::-1].copy())[0]  # PaddleX espera BGR para arreglos numpy
    tiempo = time.perf_counter() - t0
    textos, scores = list(r["rec_texts"]), [float(s) for s in r["rec_scores"]]
    resultado = {
        "id": ruta.stem, "archivo": ruta.name, "ancho_px": int(rgb.shape[1]), "alto_px": int(rgb.shape[0]),
        "modelo_ocr": f"PaddleOCR {paddleocr.__version__} ({MODELOS_PADDLE}; paddlepaddle {paddle.__version__} CPU)",
        "configuracion": CONFIG_PADDLE | {"det_params": {k: v for k, v in (r.get("text_det_params") or {}).items()}},
        "preprocesamiento": prepro,
        "texto_ocr": "\n".join(textos), "n_lineas": len(textos),
        "confianza_media": round(float(np.mean(scores)), 4) if scores else None,
        "confianza_min": round(float(np.min(scores)), 4) if scores else None,
        "tiempo_ocr_seg": round(tiempo, 3),
        "lineas": [{"texto": t, "score": round(s, 4), "poly": np.asarray(p).round(1).tolist()}
                   for t, s, p in zip(textos, scores, r["rec_polys"])],
        "error": "",
    }
    cache.write_text(json.dumps(resultado, ensure_ascii=False, indent=1), encoding="utf-8")
    return resultado


def ocr_tesseract(ruta: Path, forzar: bool = False) -> dict:
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = str(TESSERACT_EXE)
    CACHE_TESSERACT.mkdir(parents=True, exist_ok=True)
    cache = CACHE_TESSERACT / f"{ruta.stem}.json"
    if (previo := _leer_cache(cache, forzar)) is not None:
        return previo
    rgb, prepro = cargar_imagen(ruta)
    config = f'--tessdata-dir "{TESSDATA}" --psm {CONFIG_TESSERACT["psm"]} --oem {CONFIG_TESSERACT["oem"]}'
    t0 = time.perf_counter()
    datos = pytesseract.image_to_data(Image.fromarray(rgb), lang=CONFIG_TESSERACT["lang"], config=config,
                                      output_type=pytesseract.Output.DICT)
    tiempo = time.perf_counter() - t0
    # Una sola pasada: el texto se reconstruye agrupando palabras por (bloque, párrafo, línea)
    lineas: dict[tuple, list[str]] = {}
    for b, p, l, w in zip(datos["block_num"], datos["par_num"], datos["line_num"], datos["text"]):
        if w.strip():
            lineas.setdefault((b, p, l), []).append(w)
    texto = "\n".join(" ".join(ws) for ws in lineas.values())
    confs = [float(c) for c, w in zip(datos["conf"], datos["text"]) if w.strip() and float(c) >= 0]
    resultado = {
        "id": ruta.stem, "archivo": ruta.name,
        "modelo_ocr": f"Tesseract {pytesseract.get_tesseract_version()} (spa, tessdata_best 4.1.0, LSTM)",
        "configuracion": CONFIG_TESSERACT, "preprocesamiento": prepro,
        "texto_ocr": texto, "n_lineas": len(lineas), "n_palabras": len(confs),
        "confianza_media": round(float(np.mean(confs)) / 100, 4) if confs else None,
        "tiempo_ocr_seg": round(tiempo, 3),
        "error": "",
    }
    cache.write_text(json.dumps(resultado, ensure_ascii=False, indent=1), encoding="utf-8")
    return resultado
