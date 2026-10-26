"""Retira de los archivos publicables los nombres de personas que llegan desde los metadatos de Commons.

Contexto: privacidad.py seudonimiza los textos OCR/ASR, pero los títulos de cuatro entrevistas (fuentes
A, B, C y F) y los metadatos del documento contemporáneo doc_013 contienen el nombre de la persona
entrevistada o autora; además, el crédito de autor de doc_022/doc_023 corresponde a una persona que
figura (seudonimizada) en el texto del acta. Esos metadatos se copian a los reportes (01, 00b, 02, 03,
04, 05) y de ahí a datos/fuentes.csv y datos/documentos.csv (notebook 01).
Cuando no hay URL que reemplazar (pageid vacío), la atribución CC BY se cumple con el enlace a la página
de origen, que contiene el crédito completo (CC BY 4.0 §3(a)(2)).

Qué hace (en los CSV de datos/ y datos/reportes/, nunca en datos/raw/):
- reemplaza cada nombre por un marcador ([PERSONA_ENTREVISTADA_A], [AUTOR_SEUDONIMIZADO], ...);
- reemplaza las URL de Commons que contienen el nombre por la URL estable ?curid=<pageid>, que lleva a la
  misma página con la atribución completa (autor, licencia), como permite CC BY-SA 4.0 §3(a)(2);
- guarda antes una copia del archivo original en datos/raw/privacidad/pre_publicacion/ (no versionada).
La lista de nombres está en datos/raw/privacidad/redaccion_fuentes_PRIVADO.csv (no versionada): este
script no contiene ningún nombre. Se reemplaza texto a nivel de archivo para no reformatear los CSV.

Orden: después de los scripts 00–16 y ANTES de ejecutar el notebook 01 (que regenera fuentes.csv y
documentos.csv a partir de los reportes). Es idempotente.
Uso: python scripts/17_preparar_publicacion.py [--verificar]
  --verificar: busca en todos los archivos publicables (git ls-files + no ignorados) los nombres de la
  tabla de redacción y del mapa privado de seudonimización; termina con error si encuentra alguno.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import unicodedata
import urllib.parse

import pandas as pd

from utilidades import DATOS, RAIZ, RAW, REPORTES

PRIVADO = RAW / "privacidad"
REDACCION = PRIVADO / "redaccion_fuentes_PRIVADO.csv"
RESPALDO = PRIVADO / "pre_publicacion"
CURID = "https://commons.wikimedia.org/w/index.php?curid={}"
URL = re.compile(r"https?://[^\s,\"'<>|)\]]+")
# Entradas del mapa de seudonimización que son palabras comunes (falsos positivos del NER revisados:
# sustantivos, una palabra awajún, un término legal y un error de ASR); no indican fuga si aparecen.
FALSOS_POSITIVOS_REVISADOS = {"mayor", "papa", "inciso", "trasguiendo", "luz"}
VARIANTES = {"a": "aá", "e": "eé", "i": "ií", "o": "oó", "u": "uúü", "n": "nñ"}
VACIAS = {"de", "del", "la", "las", "los", "y", "e"}


def sin_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if not unicodedata.combining(c)).lower()


def patron(nombre: str) -> re.Pattern:
    """Nombre sin distinguir mayúsculas ni tildes, con espacio, guion bajo o guion entre palabras."""
    partes = []
    for c in sin_tildes(nombre):
        if c.isspace():
            partes.append(r"[\s_\-]+")
        elif c in VARIANTES:
            partes.append(f"[{VARIANTES[c]}]")
        else:
            partes.append(re.escape(c))
    return re.compile(r"(?<![^\W_])" + "".join(partes) + r"(?![^\W_])", re.IGNORECASE)


def cargar_redaccion() -> pd.DataFrame:
    if not REDACCION.exists():
        sys.exit(f"Falta {REDACCION.relative_to(RAIZ)} (privado): no se puede redactar ni verificar.")
    tabla = pd.read_csv(REDACCION)
    tabla["patron"] = tabla["nombre"].map(patron)
    return tabla


def redactar_texto(texto: str, tabla: pd.DataFrame) -> str:
    def url(m: re.Match) -> str:
        decodificada = urllib.parse.unquote(m.group(0))
        for _, r in tabla.iterrows():
            if pd.notna(r["pageid"]) and r["patron"].search(decodificada):
                return CURID.format(int(r["pageid"]))
        return m.group(0)
    texto = URL.sub(url, texto)
    for _, r in tabla.iterrows():
        texto = r["patron"].sub(r["reemplazo"], texto)
    return texto


def redactar() -> None:
    tabla = cargar_redaccion()
    RESPALDO.mkdir(parents=True, exist_ok=True)
    cambios = []
    for ruta in sorted(list(DATOS.glob("*.csv")) + list(REPORTES.glob("*.csv"))):
        with open(ruta, encoding="utf-8", newline="") as f:   # conserva los saltos de línea originales
            original = f.read()
        nuevo = redactar_texto(original, tabla)
        if nuevo != original:
            copia = RESPALDO / ruta.relative_to(DATOS)
            copia.parent.mkdir(parents=True, exist_ok=True)
            if not copia.exists():
                shutil.copy2(ruta, copia)
            fechas = ruta.stat()
            ruta.write_text(nuevo, encoding="utf-8", newline="")
            # Redactar no es una nueva consulta a Commons: se conserva la fecha de modificación, que el
            # notebook 01 usa como fecha de consulta de los metadatos de documentos.
            os.utime(ruta, (fechas.st_atime, fechas.st_mtime))
            cambios.append(ruta.relative_to(RAIZ).as_posix())
    print(f"Archivos redactados: {len(cambios)}", *cambios, sep="\n  ")
    print(f"Originales respaldados en {RESPALDO.relative_to(RAIZ).as_posix()}/ (no versionado)")


def archivos_publicables() -> list:
    raiz_git = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=RAIZ, capture_output=True,
                              text=True).stdout.strip()
    lista = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=raiz_git,
                           capture_output=True, text=True, encoding="utf-8").stdout.splitlines()
    from pathlib import Path
    return [Path(raiz_git) / a for a in lista if (Path(raiz_git) / a).is_file()]


def verificar() -> bool:
    tabla = cargar_redaccion()
    mapa = pd.read_csv(PRIVADO / "mapa_nombres_PRIVADO.csv")
    nombres = {sin_tildes(n).strip() for n in mapa["original"]} - FALSOS_POSITIVOS_REVISADOS
    patrones = [(r["reemplazo"], r["patron"]) for _, r in tabla.iterrows()]
    patrones += [(m, patron(n)) for n, m in zip(mapa["original"], mapa["marcador"])
                 if sin_tildes(n).strip() in nombres]
    # También pares de palabras consecutivas de cada nombre (p. ej., los dos apellidos): un crédito puede
    # citar a la misma persona con menos palabras que el texto.
    for n, m in zip(mapa["original"], mapa["marcador"]):
        palabras = [p for p in sin_tildes(n).split() if p not in VACIAS]
        patrones += [(f"{m} (2 palabras)", patron(f"{a} {b}")) for a, b in zip(palabras, palabras[1:])
                     if len(a) >= 3 and len(b) >= 3 and len(palabras) > 2]
    hallazgos = []
    for ruta in archivos_publicables():
        if ruta.suffix.lower() in {".jpg", ".jpeg", ".png"}:
            continue
        texto = ruta.read_text(encoding="utf-8", errors="replace")
        texto = texto + "\n" + urllib.parse.unquote(texto)   # también nombres codificados en URL
        for marcador, p in patrones:
            n = len(p.findall(texto))
            if n:
                hallazgos.append((ruta.name, marcador, n))
    if hallazgos:
        print("NOMBRES ENCONTRADOS (se muestra el marcador, no el nombre):")
        for archivo, marcador, n in hallazgos:
            print(f"  {archivo}: {marcador} × {n}")
        return False
    print(f"Verificación OK: 0 nombres de personas protegidas en {len(archivos_publicables())} archivos publicables "
          f"({len(patrones)} nombres buscados, sin distinguir mayúsculas, tildes ni codificación URL).")
    return True


if __name__ == "__main__":
    if "--verificar" in sys.argv:
        sys.exit(0 if verificar() else 1)
    redactar()
