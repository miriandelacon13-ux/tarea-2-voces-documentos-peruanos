"""Busca cada documento en Wikimedia Commons por su SHA-1 y recupera fuente, licencia y autor.

Una coincidencia de SHA-1 prueba que el archivo local es idéntico byte a byte al publicado.
Los documentos sin coincidencia quedan como PENDIENTE_REVISION_HUMANA: su fuente debe
aportarla una persona (no se infiere ni se inventa).
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request

import pandas as pd

from utilidades import RAW, REPORTES, sha1

API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "Tarea2-OCR-ASR-academico/1.0 (uso educativo; consulta de metadatos)"
PAUSA_S = 1.5
PENDIENTE = "PENDIENTE_REVISION_HUMANA"


def consultar(parametros: dict, intentos: int = 5) -> dict:
    parametros = parametros | {"action": "query", "format": "json", "formatversion": "2"}
    url = f"{API}?{urllib.parse.urlencode(parametros)}"
    for intento in range(intentos):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code != 429 or intento == intentos - 1:
                raise
            time.sleep(float(e.headers.get("Retry-After") or 10 * (intento + 1)))
        except (urllib.error.URLError, TimeoutError):
            if intento == intentos - 1:
                raise
            time.sleep(10 * (intento + 1))
    raise RuntimeError("sin respuesta")


def main() -> None:
    from html import unescape
    import re

    sin_html = lambda t: re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", str(t or "")))).strip()

    filas = []
    for ruta in sorted((RAW / "documentos").iterdir()):
        h = sha1(ruta)
        coincidencias = consultar({"list": "allimages", "aisha1": h, "aiprop": "url"})["query"]["allimages"]
        time.sleep(PAUSA_S)
        fila = {"archivo": ruta.name, "sha1_local": h, "titulo_commons": PENDIENTE, "fuente_url": PENDIENTE,
                "licencia": PENDIENTE, "licencia_url": "", "autor": "", "credito": "", "descripcion": "",
                "fecha_original": "", "coincidencia": "sin coincidencia exacta de SHA-1"}
        if coincidencias:
            titulo = coincidencias[0]["name"]
            info = consultar({"titles": f"File:{titulo}", "prop": "imageinfo", "iiprop": "url|extmetadata"})
            time.sleep(PAUSA_S)
            ii = info["query"]["pages"][0]["imageinfo"][0]
            meta = {k: sin_html(v.get("value")) for k, v in ii.get("extmetadata", {}).items()}
            fila |= {
                "titulo_commons": titulo, "fuente_url": ii["descriptionurl"],
                "licencia": meta.get("LicenseShortName", ""), "licencia_url": meta.get("LicenseUrl", ""),
                "autor": meta.get("Artist", ""), "credito": meta.get("Credit", ""),
                "descripcion": meta.get("ImageDescription", "")[:300],
                "fecha_original": meta.get("DateTimeOriginal", ""),
                "coincidencia": "SHA-1 idéntico" + (f" (+{len(coincidencias) - 1} copias)" if len(coincidencias) > 1 else ""),
            }
        filas.append(fila)
        print(f"{ruta.name}: {fila['titulo_commons']} | {fila['licencia']}")

    df = pd.DataFrame(filas)
    df.to_csv(REPORTES / "fuentes_documentos_commons.csv", index=False, encoding="utf-8")
    print(f"\nCon fuente verificada por SHA-1: {(df['titulo_commons'] != PENDIENTE).sum()}/{len(df)}")


if __name__ == "__main__":
    main()
