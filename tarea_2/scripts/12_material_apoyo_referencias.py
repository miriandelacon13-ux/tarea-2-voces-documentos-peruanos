"""Material de apoyo para que la autora transcriba MANUALMENTE las 20 referencias de la muestra.

No contiene texto de ningún modelo (ni OCR, ni ASR, ni LLM): solo facilita leer y escuchar.
- Documentos: tiras horizontales con 12 % de solapamiento, a resolución nativa (las imágenes
  pequeñas se amplían x2 para leerlas mejor). Salida: datos/raw/referencias/apoyo/<doc>/tira_XX.jpg
- Audio: cada clip se corta en pausas (mínimo de energía) en fragmentos de <= 15 s, más una
  plantilla con marcas de tiempo [mm:ss–mm:ss] (los corchetes se eliminan en la normalización del
  WER, así que pueden quedarse en la referencia). Salida: datos/raw/referencias/apoyo/<aud>/
Todo queda en datos/raw/ (no versionado). Nunca toca los archivos de referencia.
"""
from __future__ import annotations

import wave

import numpy as np
import pandas as pd
from PIL import Image, ImageOps

from utilidades import DATOS, RAW

Image.MAX_IMAGE_PIXELS = None
APOYO = RAW / "referencias" / "apoyo"
SR = 16_000
MAX_SEG_S = 15.0
SOLAPE = 0.12


def tiras_documento(ruta, destino) -> int:
    destino.mkdir(parents=True, exist_ok=True)
    with Image.open(ruta) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
    if im.width < 1200:  # imágenes pequeñas: ampliar x2 para lectura cómoda
        im = im.resize((im.width * 2, im.height * 2), Image.Resampling.LANCZOS)
    alto_tira = max(400, int(im.width * 0.35))
    paso = int(alto_tira * (1 - SOLAPE))
    n, y = 0, 0
    while y < im.height:
        n += 1
        im.crop((0, y, im.width, min(im.height, y + alto_tira))).save(destino / f"tira_{n:02d}.jpg", quality=92)
        if y + alto_tira >= im.height:
            break
        y += paso
    return n


def fragmentos_audio(ruta, destino) -> list[tuple[float, float]]:
    destino.mkdir(parents=True, exist_ok=True)
    with wave.open(str(ruta)) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    paso = 160  # 10 ms
    n = len(x) // paso
    energia = np.sqrt((x[: n * paso].astype(np.float64).reshape(n, paso) ** 2).mean(axis=1))
    energia = np.convolve(energia, np.ones(20) / 20, mode="same")  # suavizado 200 ms
    cortes, inicio = [0], 0
    while (len(x) - inicio) / SR > MAX_SEG_S:
        a = (inicio + int(8 * SR)) // paso          # buscar pausa entre 8 y 15 s
        b = (inicio + int(MAX_SEG_S * SR)) // paso
        corte = (a + int(np.argmin(energia[a:b]))) * paso
        cortes.append(corte)
        inicio = corte
    cortes.append(len(x))
    tramos = []
    for k, (a, b) in enumerate(zip(cortes[:-1], cortes[1:]), 1):
        with wave.open(str(destino / f"fragmento_{k:02d}.wav"), "wb") as w:
            w.setnchannels(1), w.setsampwidth(2), w.setframerate(SR)
            w.writeframes(x[a:b].tobytes())
        tramos.append((a / SR, b / SR))
    mmss = lambda s: f"{int(s // 60):02d}:{s % 60:04.1f}"
    (destino / "plantilla_con_tiempos.txt").write_text(
        "\n".join(f"[{mmss(a)}–{mmss(b)}] " for a, b in tramos) + "\n", encoding="utf-8")
    return tramos


def main() -> None:
    muestra = pd.read_csv(DATOS / "muestra_evaluacion.csv")
    for _, m in muestra.iterrows():
        if m["modalidad"] == "documento":
            n = tiras_documento(RAW / "documentos" / m["archivo"], APOYO / m["id"])
            print(f"{m['id']}: {n} tiras")
        else:
            tramos = fragmentos_audio(RAW / "audio" / "clips" / m["archivo"], APOYO / m["id"])
            print(f"{m['id']}: {len(tramos)} fragmentos (máx. {max(b - a for a, b in tramos):.1f} s)")


if __name__ == "__main__":
    main()
