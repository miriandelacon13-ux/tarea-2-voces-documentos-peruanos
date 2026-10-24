"""Utilidades compartidas por los scripts del corpus (rutas, hashes y FFmpeg)."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]  # .../tarea_2
DESCARGAS = RAIZ.parent  # .../Tarea2_Python (carpetas originales de descarga)
DATOS = RAIZ / "datos"
RAW = DATOS / "raw"
REPORTES = DATOS / "reportes"

# Ubicación de FFmpeg instalado con: winget install --id Gyan.FFmpeg -e --version 9.0.2
_FFMPEG_WINGET = (
    Path(os.environ.get("LOCALAPPDATA", ""))
    / "Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0.2-full_build/bin"
)


def binario(nombre: str) -> str:
    """Devuelve la ruta a ffmpeg/ffprobe: variable FFMPEG_DIR, PATH o instalación winget."""
    if os.environ.get("FFMPEG_DIR"):
        candidato = Path(os.environ["FFMPEG_DIR"]) / f"{nombre}.exe"
        if candidato.exists():
            return str(candidato)
    encontrado = shutil.which(nombre)
    if encontrado:
        return encontrado
    candidato = _FFMPEG_WINGET / f"{nombre}.exe"
    if candidato.exists():
        return str(candidato)
    raise FileNotFoundError(f"No se encontró {nombre}. Instale FFmpeg o defina FFMPEG_DIR.")


def sha256(ruta: Path, bloque: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        while datos := f.read(bloque):
            h.update(datos)
    return h.hexdigest()


def sha1(ruta: Path, bloque: int = 1 << 20) -> str:
    h = hashlib.sha1()
    with open(ruta, "rb") as f:
        while datos := f.read(bloque):
            h.update(datos)
    return h.hexdigest()


def ffprobe(ruta: Path) -> dict:
    """Formato y streams de un archivo multimedia según ffprobe (JSON)."""
    salida = subprocess.run(
        [binario("ffprobe"), "-v", "error", "-show_format", "-show_streams", "-of", "json", str(ruta)],
        capture_output=True, text=True, check=True,
    )
    return json.loads(salida.stdout)


def a_float(valor) -> float | None:
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None
