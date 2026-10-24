"""Descarga audio adicional de Wikimedia Commons para alcanzar >= 30 min reales.

Motivo: el corpus inicial (A–E) suma 25,28 min reales (ver 02_normalizar_audio.py).

Criterios de selección (registrados en datos/reportes/audio_adicional_seleccion.csv):
- español con contexto peruano según descripción/categorías de Commons;
- material oral (entrevista / conferencia de prensa);
- licencia reutilizable (CC0, dominio público, CC BY, CC BY-SA);
- audio puro (sin pista de video) para evitar la anomalía de duración de A–D.
Descartado explícitamente: serie "Saberes asociados a las plantas medicinales de Shansha"
(descripción: "Idioma de la entrevista: Quechua Huaylas").

Garantías: carpeta nueva (adicionales/), nunca sobrescribe, verifica tamaño y SHA-1 contra Commons.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import date

import pandas as pd

from utilidades import RAW, REPORTES, sha1, sha256

ADICIONALES = RAW / "audio" / "adicionales"
API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "Tarea2-OCR-ASR-academico/1.0 (uso educativo; consulta de metadatos)"

SELECCION = [
    {"archivo_local": "audio_F.ogg",
     "titulo_commons": "Entrevista a [PERSONA_ENTREVISTADA_F]-Organización de mujeres indígenas-fiestas patrias-protesta.ogg",
     "motivo": "conferencia de prensa al aire libre en Plaza San Martín (Lima), Fiestas Patrias 2022; "
               "aporta ruido ambiente de exteriores y habla pública"},
    {"archivo_local": "audio_G.ogg",
     "titulo_commons": "Entrevista 2 en la Av. Rivagüero - El Agustino.ogg",
     "motivo": "entrevista callejera en El Agustino (Lima) a dos vendedoras; candidata a caso multihablante "
               "(número de hablantes por confirmar con diarización y escucha)"},
]


def info_commons(titulo: str) -> dict:
    parametros = {"action": "query", "format": "json", "formatversion": "2", "prop": "imageinfo",
                  "iiprop": "url|size|sha1|mime", "titles": f"File:{titulo}"}
    req = urllib.request.Request(f"{API}?{urllib.parse.urlencode(parametros)}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)["query"]["pages"][0]["imageinfo"][0]


def descargar(url: str, destino) -> None:
    temporal = destino.with_suffix(destino.suffix + ".parcial")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=300) as r, open(temporal, "wb") as f:
        while bloque := r.read(1 << 20):
            f.write(bloque)
    temporal.rename(destino)


def main() -> None:
    ADICIONALES.mkdir(parents=True, exist_ok=True)
    filas = []
    for item in SELECCION:
        info = info_commons(item["titulo_commons"])
        destino = ADICIONALES / item["archivo_local"]
        accion = "ya_existia"
        if not destino.exists():
            descargar(info["url"], destino)
            accion = "descargado"
        tam_ok = destino.stat().st_size == info["size"]
        sha1_ok = sha1(destino) == info["sha1"]
        if not (tam_ok and sha1_ok):
            raise RuntimeError(f"{destino.name}: no coincide con Commons (tamaño={tam_ok}, sha1={sha1_ok})")
        filas.append(item | {
            "url_archivo": info["url"], "mime_commons": info["mime"],
            "tamano_bytes": destino.stat().st_size, "tamano_coincide": tam_ok,
            "sha1": info["sha1"], "sha1_coincide": sha1_ok, "sha256": sha256(destino),
            "accion": accion, "fecha_descarga": date.today().isoformat(),
        })
    df = pd.DataFrame(filas)
    salida = REPORTES / "audio_adicional_seleccion.csv"
    if salida.exists():  # conservar la fecha de la primera descarga
        previas = pd.read_csv(salida).set_index("archivo_local")["fecha_descarga"]
        df["fecha_descarga"] = [previas.get(a, f) for a, f in zip(df["archivo_local"], df["fecha_descarga"])]
    df.to_csv(salida, index=False, encoding="utf-8")
    print(df[["archivo_local", "mime_commons", "tamano_bytes", "tamano_coincide", "sha1_coincide", "accion"]].to_string(index=False))


if __name__ == "__main__":
    main()
