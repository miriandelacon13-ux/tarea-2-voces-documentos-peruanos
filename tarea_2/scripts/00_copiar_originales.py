"""Copia (no mueve) los originales descargados a datos/raw/ y verifica su integridad.

- Nunca sobrescribe: si el destino existe, solo comprueba que el SHA-256 coincida.
- Genera datos/reportes/integridad_archivos.csv con hash, tamaño, formato real,
  legibilidad y duplicados exactos.
"""
from __future__ import annotations

import shutil

import pandas as pd
from PIL import Image

from utilidades import DESCARGAS, RAW, REPORTES, a_float, ffprobe, sha256

Image.MAX_IMAGE_PIXELS = None  # doc_025 tiene ~93 MP; es un escaneo legítimo, no un ataque

ORIGEN_DESTINO = [
    ("documento", DESCARGAS / "documentos", RAW / "documentos"),
    ("audio", DESCARGAS / "audio" / "originales", RAW / "audio" / "originales"),
]


def copiar_verificando(origen, destino) -> str:
    h_origen = sha256(origen)
    if destino.exists():
        if sha256(destino) != h_origen:
            raise RuntimeError(f"El destino {destino} existe con contenido distinto; no se sobrescribe.")
        return "ya_existia_identico"
    shutil.copy2(origen, destino)
    if sha256(destino) != h_origen:
        raise RuntimeError(f"La copia de {origen.name} no coincide con el original.")
    return "copiado_verificado"


def describir_imagen(ruta) -> dict:
    try:
        with Image.open(ruta) as im:
            im.verify()
        with Image.open(ruta) as im:
            return {"formato_real": im.format, "ancho_px": im.width, "alto_px": im.height,
                    "megapixeles": round(im.width * im.height / 1e6, 1), "legible": True, "error": ""}
    except Exception as e:  # registrar, nunca ocultar
        return {"formato_real": None, "legible": False, "error": f"{type(e).__name__}: {e}"}


def describir_audio(ruta) -> dict:
    try:
        info = ffprobe(ruta)
        streams = info["streams"]
        return {
            "formato_real": info["format"]["format_name"],
            "streams": "; ".join(f"{s['codec_type']}:{s['codec_name']}" for s in streams),
            "start_time_s": a_float(info["format"].get("start_time")),
            "duracion_contenedor_s": a_float(info["format"].get("duration")),
            "legible": True, "error": "",
        }
    except Exception as e:
        return {"formato_real": None, "legible": False, "error": f"{type(e).__name__}: {e}"}


def main() -> None:
    filas = []
    for modalidad, carpeta_origen, carpeta_destino in ORIGEN_DESTINO:
        carpeta_destino.mkdir(parents=True, exist_ok=True)
        for origen in sorted(p for p in carpeta_origen.iterdir() if p.is_file()):
            destino = carpeta_destino / origen.name
            estado = copiar_verificando(origen, destino)
            fila = {
                "modalidad": modalidad,
                "archivo": origen.name,
                "ruta_raw": destino.relative_to(RAW.parent.parent).as_posix(),
                "extension": origen.suffix.lower().lstrip("."),
                "tamano_bytes": destino.stat().st_size,
                "sha256": sha256(destino),
                "copia": estado,
            }
            fila |= describir_imagen(destino) if modalidad == "documento" else describir_audio(destino)
            filas.append(fila)

    df = pd.DataFrame(filas)
    ext_esperada = {"jpg": "JPEG", "jpeg": "JPEG", "png": "PNG", "webm": "matroska,webm"}
    df["extension_coincide"] = df.apply(lambda r: ext_esperada.get(r["extension"]) == r["formato_real"], axis=1)
    df["vacio"] = df["tamano_bytes"] == 0
    df["mayor_100MB"] = df["tamano_bytes"] > 100 * 1024**2
    primeros = df.drop_duplicates("sha256").set_index("sha256")["archivo"]
    df["duplicado_de"] = [primeros[h] if primeros[h] != a else "" for h, a in zip(df["sha256"], df["archivo"])]

    REPORTES.mkdir(parents=True, exist_ok=True)
    salida = REPORTES / "integridad_archivos.csv"
    df.to_csv(salida, index=False, encoding="utf-8")
    print(df[["modalidad", "archivo", "tamano_bytes", "formato_real", "extension_coincide",
              "legible", "mayor_100MB", "duplicado_de", "copia"]].to_string(index=False))
    print(f"\nArchivos: {len(df)} | ilegibles: {(~df['legible']).sum()} | vacíos: {df['vacio'].sum()} | "
          f"duplicados exactos: {(df['duplicado_de'] != '').sum()} | >100 MB: {df['mayor_100MB'].sum()}")
    print(f"Reporte: {salida}")


if __name__ == "__main__":
    main()
