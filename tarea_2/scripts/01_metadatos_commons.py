"""Recupera fuente, licencia y autor de los audios desde la API pública de Wikimedia Commons.

La correspondencia archivo local <-> página de Commons NO se asume: se confirma
comparando el SHA-1 del archivo local con el SHA-1 que publica Commons.
Solo se consultan metadatos; no se descarga ningún audio.
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from datetime import date
from html import unescape

import pandas as pd

from utilidades import RAW, REPORTES, sha1

# Páginas de Commons por pageid (no por título): cuatro títulos contienen el nombre de la persona
# entrevistada. Cada pageid devuelve el mismo archivo (título y SHA-1 verificados el 2026-10-25).
PAGEIDS_COMMONS = {
    121326996: "A · entrevista en Jr. de la Unión",
    121320724: "B · entrevista en Plaza San Martín (1)",
    121321680: "C · entrevista en Plaza San Martín (2)",
    121328389: "D · entrevista a un excombatiente del Cenepa",
    149426476: "E · entrevistas en una ceremonia patronal",
    # Lote adicional (ver 00b_descargar_audio_adicional.py)
    121219891: "F · conferencia de prensa en Plaza San Martín",
    119251160: "G · entrevista en El Agustino",
}
CARPETAS_AUDIO = [RAW / "audio" / "originales", RAW / "audio" / "adicionales"]
API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "Tarea2-OCR-ASR-academico/1.0 (uso educativo; consulta de metadatos)"


def sin_html(texto) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", str(texto or "")))).strip()


def buscar_clave(metadatos, clave: str):
    """Busca una clave en la metadata anidada de getID3 (lista de pares name/value)."""
    for m in metadatos or []:
        if m.get("name") == clave and not isinstance(m.get("value"), list):
            return m["value"]
        if isinstance(m.get("value"), list):
            encontrado = buscar_clave(m["value"], clave)
            if encontrado is not None:
                return encontrado
    return None


def consultar() -> dict:
    parametros = {
        "action": "query", "format": "json", "formatversion": "2", "prop": "imageinfo",
        "iiprop": "size|sha1|url|mime|extmetadata|metadata|timestamp|user",
        "pageids": "|".join(str(p) for p in PAGEIDS_COMMONS),
    }
    req = urllib.request.Request(f"{API}?{urllib.parse.urlencode(parametros)}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def main() -> None:
    datos = consultar()
    REPORTES.mkdir(parents=True, exist_ok=True)
    # Respuesta cruda: incluye descripciones con nombres de particulares -> no se versiona (datos/raw/)
    (RAW / "metadatos").mkdir(parents=True, exist_ok=True)
    (RAW / "metadatos" / "commons_audio_metadata.json").write_text(
        json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")

    locales = {sha1(p): p.name for carpeta in CARPETAS_AUDIO if carpeta.exists()
               for p in sorted(carpeta.iterdir()) if p.is_file()}
    filas = []
    for pagina in datos["query"]["pages"]:
        info = pagina["imageinfo"][0]
        meta = {k: sin_html(v.get("value", "")) for k, v in info.get("extmetadata", {}).items()}
        tecnica = {m["name"]: m["value"] for m in info.get("metadata") or [] if not isinstance(m.get("value"), list)}
        filas.append({
            "archivo_local": locales.get(info["sha1"], "SIN_COINCIDENCIA"),
            "titulo_commons": pagina["title"].removeprefix("File:"),
            "fuente_url": info["descriptionurl"],
            "licencia": meta.get("LicenseShortName", ""),
            "licencia_url": meta.get("LicenseUrl", ""),
            "autor": meta.get("Artist", ""),
            "credito": meta.get("Credit", ""),
            "fecha_subida": info["timestamp"],
            "fecha_consulta": date.today().isoformat(),
            "tamano_bytes_commons": info["size"],
            "sha1_commons": info["sha1"],
            "sha1_coincide": info["sha1"] in locales,
            # Commons calcula la duración con getID3; para WebM sin Duration la estima por bitrate
            "duracion_commons_declarada_s": tecnica.get("playtime_seconds")
            or buscar_clave(info.get("metadata"), "length"),  # OGG: streams -> length
            "bitrate_getid3_bps": tecnica.get("bitrate"),
            "duracion_estimada_tamano_x8_div_bitrate_s": round(info["size"] * 8 / tecnica["bitrate"], 4)
            if tecnica.get("bitrate") else None,
        })
    df = pd.DataFrame(filas).sort_values("archivo_local")
    df.to_csv(REPORTES / "fuentes_audio_commons.csv", index=False, encoding="utf-8")
    print(df[["archivo_local", "titulo_commons", "licencia", "autor", "sha1_coincide", "duracion_commons_declarada_s",
              "bitrate_getid3_bps", "duracion_estimada_tamano_x8_div_bitrate_s"]].to_string(index=False))


if __name__ == "__main__":
    main()
