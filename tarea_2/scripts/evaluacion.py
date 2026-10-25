"""Normalización y métricas de evaluación (CER, WER, RTF) para 02_evaluacion.ipynb.

Fórmulas:
- CER = (S + D + I) / N, sobre caracteres (incluido el espacio) del texto normalizado; N = longitud
  de la referencia normalizada. S/D/I = sustituciones, eliminaciones e inserciones de la alineación
  de distancia de edición mínima (Levenshtein), calculada con jiwer.
- WER = (S + D + I) / N, sobre palabras del texto normalizado; N = palabras de la referencia.
- RTF = tiempo_procesamiento / duración_audio  (< 1: más rápido que el tiempo real).
Agregados: promedio simple por elemento (macro, métrica principal pedida) y ponderado por longitud
(micro = errores totales / longitud total de las referencias), como complemento.

La MISMA función de normalización se aplica a la referencia y a todas las hipótesis (sin ajustes por
modelo). Ver la tabla de normalización en datos/GUIA_REFERENCIAS.md.
Nunca se calcula una métrica si la referencia está vacía o es PENDIENTE_REVISION_HUMANA.
"""
from __future__ import annotations

import re
import unicodedata

import jiwer
from num2words import num2words

PENDIENTE = "PENDIENTE_REVISION_HUMANA"
ETIQUETAS = re.compile(r"\[[^\]]*\]")          # [HABLANTE_1], [ilegible], [inaudible], [NOMBRE_3]...
CORTE_CON_GUION = re.compile(r"(\w)-[ \t]*\r?\n[ \t]*(\w)")
NO_ALFANUMERICO = re.compile(r"[^\w\s]|_")
MULETILLAS = {"eh", "ehh", "em", "emm", "mm", "mmm", "ah", "aah"}


def referencia_disponible(texto) -> bool:
    return isinstance(texto, str) and bool(texto.strip()) and PENDIENTE not in texto


def _quitar_tildes(texto: str) -> str:
    """Elimina tildes/diéresis pero conserva la ñ (es una letra distinta en español)."""
    salida = []
    for c in unicodedata.normalize("NFD", texto):
        if unicodedata.category(c) == "Mn" and not (c == "̃" and salida and salida[-1] in "nN"):
            continue
        salida.append(c)
    return unicodedata.normalize("NFC", "".join(salida))


def normalizar_cer(texto: str, quitar_tildes: bool = False) -> str:
    t = unicodedata.normalize("NFC", texto)
    t = ETIQUETAS.sub(" ", t)
    t = CORTE_CON_GUION.sub(r"\1\2", t)            # «autori-\nsado» -> «autorisado»
    t = t.lower()
    t = NO_ALFANUMERICO.sub(" ", t)                # puntuación y símbolos -> espacio
    if quitar_tildes:
        t = _quitar_tildes(t)
    return re.sub(r"\s+", " ", t).strip()          # saltos de línea y espacios -> un espacio


def _cifras_a_palabras(texto: str) -> str:
    return re.sub(r"\d+", lambda m: f" {num2words(int(m.group()), lang='es')} ", texto)


def normalizar_wer(texto: str) -> str:
    t = unicodedata.normalize("NFC", texto)
    t = ETIQUETAS.sub(" ", t)                      # quita [HABLANTE_k] y otras etiquetas
    t = t.lower()
    t = _cifras_a_palabras(t)
    t = NO_ALFANUMERICO.sub(" ", t)
    palabras = [p for p in t.split() if p not in MULETILLAS]
    return " ".join(palabras)


def cer(referencia: str, hipotesis: str, quitar_tildes: bool = False) -> dict:
    if not referencia_disponible(referencia):
        raise ValueError("Referencia no disponible (PENDIENTE_REVISION_HUMANA): no se calcula CER")
    r, h = normalizar_cer(referencia, quitar_tildes), normalizar_cer(hipotesis or "", quitar_tildes)
    if not h:
        return {"cer": 1.0, "S": 0, "D": len(r), "I": 0, "N": len(r)}
    o = jiwer.process_characters(r, h)
    return {"cer": o.cer, "S": o.substitutions, "D": o.deletions, "I": o.insertions, "N": len(r)}


def wer(referencia: str, hipotesis: str) -> dict:
    if not referencia_disponible(referencia):
        raise ValueError("Referencia no disponible (PENDIENTE_REVISION_HUMANA): no se calcula WER")
    r, h = normalizar_wer(referencia), normalizar_wer(hipotesis or "")
    n = len(r.split())
    if not h:
        return {"wer": 1.0, "S": 0, "D": n, "I": 0, "N": n}
    o = jiwer.process_words(r, h)
    return {"wer": o.wer, "S": o.substitutions, "D": o.deletions, "I": o.insertions, "N": n}


def rtf(tiempo_procesamiento_s: float, duracion_audio_s: float) -> float:
    return tiempo_procesamiento_s / duracion_audio_s


def agregar(filas: list[dict], clave: str) -> dict:
    """Promedio simple por elemento (macro) y ponderado por longitud (micro)."""
    if not filas:
        return {"macro": None, "micro": None, "n": 0}
    errores = sum(f["S"] + f["D"] + f["I"] for f in filas)
    total = sum(f["N"] for f in filas)
    return {"macro": sum(f[clave] for f in filas) / len(filas), "micro": errores / total if total else None,
            "n": len(filas)}


def autoverificar() -> list[tuple[str, bool]]:
    """Pruebas con ejemplos sintéticos (no son datos del corpus) para validar normalización y fórmulas."""
    casos = [
        ("CER: 1 sustitución en 3 caracteres = 1/3", abs(cer("abc", "abd")["cer"] - 1 / 3) < 1e-9),
        ("CER: puntuación, mayúsculas y saltos de línea no penalizan",
         cer("Lima,\n12 de Enero.", "lima 12 de enero")["cer"] == 0),
        ("CER: guion de corte de línea se une", cer("autori-\nsado", "autorisado")["cer"] == 0),
        ("CER: la tilde cuenta en la métrica principal (1/4)", abs(cer("Perú", "Peru")["cer"] - 0.25) < 1e-9),
        ("CER sin tildes: Perú = Peru, pero ñ ≠ n",
         cer("Perú", "Peru", quitar_tildes=True)["cer"] == 0 and cer("año", "ano", quitar_tildes=True)["cer"] > 0),
        ("CER: inserciones pueden superar 1", cer("a", "abcd")["cer"] == 3.0),
        ("WER: 1 sustitución en 4 palabras = 0,25", abs(wer("el perú es grande", "el peru es grande")["wer"] - 0.25) < 1e-9),
        ("WER: etiquetas [HABLANTE_k] se eliminan", wer("[HABLANTE_1] Hola mundo", "hola, mundo.")["wer"] == 0),
        ("WER: cifras = palabras", wer("en mil novecientos doce", "En 1912")["wer"] == 0),
        # Limitación conocida: «dos a cero» (dicho) frente a «2-0» (escrito) cuenta 1 error, porque el
        # guion no se lee como «a». Se documenta en lugar de añadir reglas a medida.
        ("WER: limitación documentada «dos a cero» vs «2-0» = 1 eliminación",
         wer("dos a cero", "2-0")["D"] == 1),
        ("WER: muletillas no léxicas se eliminan", wer("eh bueno sí", "bueno sí")["wer"] == 0),
        ("WER: hipótesis vacía = 1", wer("hola mundo", "")["wer"] == 1.0),
        ("RTF = tiempo / duración", rtf(10, 100) == 0.1),
    ]
    try:
        cer(PENDIENTE, "x")
        casos.append(("Referencia pendiente bloquea el cálculo", False))
    except ValueError:
        casos.append(("Referencia pendiente bloquea el cálculo", True))
    return casos


if __name__ == "__main__":
    for nombre, ok in autoverificar():
        print("✅" if ok else "❌", nombre)
