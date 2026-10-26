"""Completa la fuente de los documentos que 04_metadatos_documentos_commons.py no pudo verificar por SHA-1.

Seis documentos no coinciden byte a byte con ningún archivo de Wikimedia Commons porque no son el archivo
publicado, sino:
- una página exportada de un PDF de Commons (doc_005, doc_006, doc_007, doc_009 y doc_010), o
- una fotografía propia de la pantalla que muestra la página de un archivo de Commons (doc_021).
Su correspondencia se verifica por contenido y queda registrada en la columna `coincidencia`:
- PDF: se renderizan todas las páginas y se calcula la correlación visual con la imagen local. La página
  candidata debe ser la mejor, con correlación >= 0,85 y >= 0,2 por encima de la segunda.
- Fotografía de pantalla: el texto y el diseño se compararon a la vista; además, las resoluciones que se
  leen en la foto deben ser exactamente las que Commons genera para ese archivo.
Los candidatos se identificaron buscando en Commons por título y contenido y se fijan aquí por pageid.
Licencia, autor y crédito se leen de la API de Commons (no se infieren). La respuesta cruda se guarda en
datos/raw/metadatos/ (puede contener nombres) y después se ejecuta 17_preparar_publicacion.py.

Uso: python scripts/04b_fuentes_por_contenido.py   (los PDF se guardan en datos/raw/cache/fuentes_commons/)
"""
from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from datetime import date, datetime
from html import unescape

import numpy as np
import pandas as pd
import pypdfium2 as pdfium
from PIL import Image

from utilidades import RAW, REPORTES

API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "Tarea2-OCR-ASR-academico/1.0 (uso educativo; verificación de fuentes)"
CACHE = RAW / "cache" / "fuentes_commons"
PENDIENTE = "PENDIENTE_REVISION_HUMANA"
ANCHO = 256

# archivo local -> página de Commons (pageid) y forma de correspondencia esperada
CANDIDATOS = {
    "doc_005.png": {"pageid": 125143989, "pagina_pdf": 11, "nota": "portada del Tomo I"},
    "doc_006.png": {"pageid": 125143033, "pagina_pdf": 14, "nota": "página impresa 8 del Tomo II"},
    "doc_007.png": {"pageid": 95006799, "pagina_pdf": 5, "nota": "Año I, núm. 3, 28 de mayo de 1887"},
    "doc_009.png": {"pageid": 196947131, "pagina_pdf": 1, "nota": "primera página de la carta"},
    "doc_010.png": {"pageid": 196947176, "pagina_pdf": 2, "nota": "segunda página de la carta"},
    "doc_021.jpg": {"pageid": 7279749, "foto_de_pantalla": [(500, 762), (250, 381), (330, 503)]},
}


def consultar(parametros: dict) -> dict:
    parametros = parametros | {"action": "query", "format": "json", "formatversion": "2"}
    req = urllib.request.Request(f"{API}?{urllib.parse.urlencode(parametros)}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def sin_html(t) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", str(t or "")))).strip()


def pdf_local(pageid: int, info: dict):
    ruta = CACHE / f"{pageid}.pdf"
    if not ruta.exists() or ruta.stat().st_size != info["size"]:
        CACHE.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(info["url"], headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=600) as r, open(ruta, "wb") as f:
            while bloque := r.read(1 << 20):
                f.write(bloque)
    return ruta


def gris(img: Image.Image, alto: int) -> np.ndarray:
    g = np.asarray(img.convert("L").resize((ANCHO, alto), Image.BILINEAR), dtype=np.float32)
    g -= g.mean()
    return g / (np.linalg.norm(g) + 1e-6)


def verificar_pagina(local: Image.Image, ruta_pdf, esperada: int) -> tuple[float, float, int]:
    if local.mode == "RGBA":   # las páginas exportadas traen transparencia: fondo blanco
        fondo = Image.new("RGB", local.size, "white")
        fondo.paste(local, mask=local.split()[3])
        local = fondo
    alto = round(ANCHO * local.height / local.width)
    ref = gris(local, alto)
    doc = pdfium.PdfDocument(str(ruta_pdf))
    puntajes = []
    for i in range(len(doc)):
        pg = doc[i]
        img = pg.render(scale=ANCHO / pg.get_width(), grayscale=True).to_pil()
        puntajes.append(float((ref * gris(img, alto)).sum()))
    orden = np.argsort(puntajes)[::-1]
    mejor, segunda = int(orden[0]) + 1, float(puntajes[orden[1]])
    if mejor != esperada or puntajes[orden[0]] < 0.85 or puntajes[orden[0]] - segunda < 0.2:
        raise RuntimeError(f"{ruta_pdf.name}: la mejor página es {mejor} ({puntajes[orden[0]]:.3f}), no {esperada}")
    return puntajes[orden[0]], segunda, len(doc)


def main() -> None:
    ruta_csv = REPORTES / "fuentes_documentos_commons.csv"
    tabla = pd.read_csv(ruta_csv, dtype=str, keep_default_na=False)
    if "fecha_consulta" not in tabla.columns:   # fecha real de la consulta de 04 (= fecha del archivo)
        tabla["fecha_consulta"] = datetime.fromtimestamp(ruta_csv.stat().st_mtime).date().isoformat()
    ids = [c["pageid"] for c in CANDIDATOS.values()]
    datos = consultar({"pageids": "|".join(map(str, ids)), "prop": "imageinfo",
                       "iiprop": "url|size|sha1|extmetadata"})
    (RAW / "metadatos").mkdir(parents=True, exist_ok=True)   # respuesta cruda: no se versiona
    (RAW / "metadatos" / "commons_documentos_por_contenido.json").write_text(
        json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    paginas = {p["pageid"]: p for p in datos["query"]["pages"]}

    for archivo, cand in CANDIDATOS.items():
        fila = tabla.index[tabla["archivo"] == archivo]
        assert len(fila) == 1 and tabla.loc[fila[0], "licencia"] in (PENDIENTE, ""), f"{archivo}: fila inesperada"
        pagina = paginas[cand["pageid"]]
        ii = pagina["imageinfo"][0]
        meta = {k: sin_html(v.get("value")) for k, v in ii.get("extmetadata", {}).items()}
        local = Image.open(RAW / "documentos" / archivo)
        if "pagina_pdf" in cand:
            corr, segunda, n = verificar_pagina(local, pdf_local(cand["pageid"], ii), cand["pagina_pdf"])
            coincidencia = (f"contenido: página {cand['pagina_pdf']} de {n} del PDF ({cand['nota']}); correlación "
                            f"visual {corr:.3f} frente a {segunda:.3f} de la siguiente; el archivo local es una "
                            "exportación de esa página, por eso su SHA-1 no coincide")
        else:
            esperado = [(a, round(a * ii["height"] / ii["width"])) for a, _ in cand["foto_de_pantalla"]]
            assert esperado == cand["foto_de_pantalla"], f"{archivo}: resoluciones no coinciden"
            coincidencia = (f"contenido: fotografía propia de la pantalla que muestra la página del archivo en Commons; "
                            f"mismo texto y diseño (comparación visual) y resoluciones visibles en la foto "
                            f"({', '.join(f'{a}×{b}' for a, b in cand['foto_de_pantalla'])}) idénticas a las de este "
                            f"archivo de {ii['width']}×{ii['height']}")
        tabla.loc[fila[0], ["titulo_commons", "fuente_url", "licencia", "licencia_url", "autor", "credito",
                            "descripcion", "fecha_original", "coincidencia", "fecha_consulta"]] = [
            pagina["title"].removeprefix("File:"), ii["descriptionurl"], meta.get("LicenseShortName", ""),
            meta.get("LicenseUrl", ""), meta.get("Artist", ""), meta.get("Credit", ""),
            meta.get("ImageDescription", "")[:300], meta.get("DateTimeOriginal", ""), coincidencia,
            date.today().isoformat()]
        print(f"{archivo}: {pagina['title']} | {meta.get('LicenseShortName', '')} | {coincidencia[:90]}…")

    fechas = ruta_csv.stat()
    tabla.to_csv(ruta_csv, index=False, encoding="utf-8")
    os.utime(ruta_csv, (fechas.st_atime, fechas.st_mtime))
    pend = (tabla["licencia"] == PENDIENTE).sum()
    print(f"\nFuentes verificadas: {len(tabla) - pend}/{len(tabla)} · pendientes: {pend}")


if __name__ == "__main__":
    main()
