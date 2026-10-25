"""Extracción estructurada con LLM local (Ollama qwen2.5:3b) sobre los textos OCR/ASR seudonimizados.

- Entrada: datos/documentos.csv (texto_ocr) y datos/transcripciones.csv (texto_asr_diarizado), ambos
  seudonimizados: el LLM no ve datos personales y su salida es publicable.
- Salida estructurada con esquema JSON (parámetro `format` de Ollama), temperature=0, seed=42.
- Campos: modalidad, tema, resumen; documentos: emisor, fecha, monto (null si no aparecen);
  audios: citas_clave (literales), numero_hablantes (etiquetas [HABLANTE_k] distintas; null si no hay).
- Validación: JSON parseable + claves/tipos del esquema; verificaciones anti-invención:
  · cada cita clave debe aparecer literalmente en el texto fuente (sin distinguir mayúsculas/espacios);
  · las cifras de fecha y monto deben aparecer en el texto fuente;
  · numero_hablantes debe coincidir con las etiquetas presentes.
- Auditoría: 20 extracciones al azar (10 documentos + 10 audios, semilla 20261025) en
  datos/auditoria_llm.csv con correcto = PENDIENTE_REVISION_HUMANA (lo decide la autora).
Uso: python scripts/14_extraccion_llm.py [--forzar]
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
from datetime import date

import numpy as np
import pandas as pd

from utilidades import DATOS, RAW

OLLAMA = "http://localhost:11434"
MODELO = "qwen2.5:3b"
OPCIONES = {"temperature": 0, "seed": 42, "num_ctx": 8192}
MAX_CHARS = 8000
CACHE = RAW / "cache" / "llm_qwen25_3b"
PENDIENTE = "PENDIENTE_REVISION_HUMANA"
SEMILLA_AUDITORIA = 20261025

SISTEMA = ("Eres un asistente de extracción de información para un archivo histórico peruano. "
           "Responde SOLO con JSON válido según el esquema. No inventes: si un dato no aparece explícitamente "
           "en el texto, usa null. El texto proviene de OCR o de reconocimiento de voz y puede tener errores: "
           "no los corrijas en las citas. Los marcadores como [NOMBRE_3] son seudónimos: consérvalos tal cual.")

ESQUEMA = {
    "documento": {"type": "object", "required": ["modalidad", "tema", "resumen", "emisor", "fecha", "monto"],
                  "properties": {"modalidad": {"type": "string", "enum": ["documento"]},
                                 "tema": {"type": "string"}, "resumen": {"type": "string"},
                                 "emisor": {"type": ["string", "null"]}, "fecha": {"type": ["string", "null"]},
                                 "monto": {"type": ["string", "null"]}}},
    "audio": {"type": "object", "required": ["modalidad", "tema", "resumen", "citas_clave", "numero_hablantes"],
              "properties": {"modalidad": {"type": "string", "enum": ["audio"]},
                             "tema": {"type": "string"}, "resumen": {"type": "string"},
                             "citas_clave": {"type": "array", "items": {"type": "string"}, "maxItems": 3},
                             "numero_hablantes": {"type": ["integer", "null"]}}},
}
INSTRUCCION = {
    "documento": ("Del siguiente texto de un DOCUMENTO (obtenido por OCR) extrae: tema (máximo 8 palabras), "
                  "resumen (1 o 2 oraciones), emisor (quién emite o firma el documento, solo si aparece), "
                  "fecha (tal como aparece en el texto, solo si aparece) y monto (cantidad de dinero, solo si "
                  "aparece). Si un campo no aparece explícitamente, null."),
    "audio": ("De la siguiente TRANSCRIPCIÓN de una entrevista (reconocimiento de voz) extrae: tema (máximo 8 "
              "palabras), resumen (1 o 2 oraciones), citas_clave (hasta 3 frases copiadas LITERALMENTE del texto) "
              "y numero_hablantes (cantidad de etiquetas [HABLANTE_k] distintas que aparecen; null si no hay "
              "etiquetas)."),
}


def llamar(modalidad: str, texto: str) -> tuple[str, float]:
    cuerpo = {"model": MODELO, "stream": False, "format": ESQUEMA[modalidad], "options": OPCIONES,
              "messages": [{"role": "system", "content": SISTEMA},
                           {"role": "user", "content": f"{INSTRUCCION[modalidad]}\n\nTEXTO:\n<<<\n{texto}\n>>>"}]}
    req = urllib.request.Request(f"{OLLAMA}/api/chat", data=json.dumps(cuerpo).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=600) as r:
        respuesta = json.load(r)
    return respuesta["message"]["content"], time.perf_counter() - t0


def plano(t: str) -> str:
    """Minúsculas, sin etiquetas [..] ni puntuación, espacios unificados (para comparar citas)."""
    t = re.sub(r"\[[^\]]*\]", " ", str(t).lower())
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", t)).strip()


def validar(modalidad: str, crudo: str, fuente: str) -> dict:
    try:
        datos = json.loads(crudo)
    except json.JSONDecodeError as e:
        return {"json_valido": False, "error_parsing": f"JSONDecodeError: {e}", "campos": None}
    esquema = ESQUEMA[modalidad]
    faltan = [k for k in esquema["required"] if k not in datos]
    if faltan:
        return {"json_valido": False, "error_parsing": f"faltan claves: {faltan}", "campos": datos}
    v = {"json_valido": True, "error_parsing": "", "campos": datos}
    f = plano(fuente)
    if modalidad == "documento":
        cifras = [c for campo in ("fecha", "monto") if datos.get(campo) for c in re.findall(r"\d+", str(datos[campo]))]
        no_halladas = [c for c in cifras if c not in f]
        v["verif_fecha_monto"] = "ok" if not no_halladas else f"cifras no halladas en el texto: {no_halladas}"
        v["verif_citas"] = v["verif_hablantes"] = "no_aplica"
    else:
        citas = datos.get("citas_clave") or []
        literales = sum(plano(c) in f for c in citas)
        v["verif_citas"] = f"{literales}/{len(citas)} literales"
        etiquetas = len(set(re.findall(r"\[HABLANTE_\d+\]", fuente)))
        nh = datos.get("numero_hablantes")
        v["verif_hablantes"] = "ok" if nh == (etiquetas or None) else f"LLM={nh} vs etiquetas={etiquetas}"
        v["verif_fecha_monto"] = "no_aplica"
    return v


def main() -> None:
    forzar = "--forzar" in sys.argv
    CACHE.mkdir(parents=True, exist_ok=True)
    info = json.load(urllib.request.urlopen(urllib.request.Request(
        f"{OLLAMA}/api/show", data=json.dumps({"model": MODELO}).encode(), headers={"Content-Type": "application/json"})))
    version = json.load(urllib.request.urlopen(f"{OLLAMA}/api/version"))["version"]
    detalle = info.get("details", {})
    modelo_llm = (f"{MODELO} (Ollama {version}; {detalle.get('parameter_size')}, {detalle.get('quantization_level')}; "
                  f"temperature=0, seed=42)")

    docs = pd.read_csv(DATOS / "documentos.csv")
    trans = pd.read_csv(DATOS / "transcripciones.csv")
    entradas = [("documento", r["id"], str(r["texto_ocr"])) for _, r in docs.iterrows()] + \
               [("audio", r["id"], str(r["texto_asr_diarizado"])) for _, r in trans.iterrows()]
    filas = []
    for modalidad, i, texto in entradas:
        cache = CACHE / f"{i}.json"
        recorte = texto[:MAX_CHARS]
        if cache.exists() and not forzar:
            previo = json.loads(cache.read_text(encoding="utf-8"))
            crudo, t = previo["crudo"], previo["tiempo_s"]
        else:
            try:
                crudo, t = llamar(modalidad, recorte)
            except Exception as e:  # registrar el error, no ocultarlo
                crudo, t = "", 0.0
                print(f"{i}: ERROR {type(e).__name__}: {e}", flush=True)
            cache.write_text(json.dumps({"crudo": crudo, "tiempo_s": t}, ensure_ascii=False), encoding="utf-8")
        v = validar(modalidad, crudo, texto)
        filas.append({"id": i, "modalidad": modalidad,
                      "campos_json": json.dumps(v["campos"], ensure_ascii=False) if v["campos"] is not None else crudo,
                      "modelo_llm": modelo_llm, "fecha": date.today().isoformat(),
                      "json_valido": v["json_valido"], "error_parsing": v["error_parsing"],
                      "verif_citas": v.get("verif_citas", ""), "verif_fecha_monto": v.get("verif_fecha_monto", ""),
                      "verif_hablantes": v.get("verif_hablantes", ""), "texto_truncado": len(texto) > MAX_CHARS,
                      "tiempo_s": round(t, 2)})
        print(f"{i}: json_valido={v['json_valido']} {v.get('verif_citas', '')} {v.get('verif_fecha_monto', '')} "
              f"{v.get('verif_hablantes', '')} ({t:.1f} s)", flush=True)
    df = pd.DataFrame(filas)
    df.to_csv(DATOS / "extraccion_llm.csv", index=False, encoding="utf-8")

    # Auditoría humana: 10 documentos + 10 audios al azar entre las extracciones válidas
    rng = np.random.default_rng(SEMILLA_AUDITORIA)
    fuente = {**dict(zip(docs["id"], docs["texto_ocr"])), **dict(zip(trans["id"], trans["texto_asr_diarizado"]))}
    elegidos = []
    for modalidad in ["documento", "audio"]:
        candidatos = sorted(df.loc[(df["modalidad"] == modalidad) & df["json_valido"], "id"])
        elegidos += sorted(rng.choice(candidatos, size=min(10, len(candidatos)), replace=False))
    auditoria = df.set_index("id").loc[elegidos, ["modalidad", "campos_json"]].reset_index()
    auditoria.insert(2, "texto_fuente", auditoria["id"].map(fuente))
    auditoria["correcto"] = PENDIENTE
    auditoria["observacion"] = ""
    salida = DATOS / "auditoria_llm.csv"
    if salida.exists():  # nunca pisar decisiones humanas ya registradas
        previa = pd.read_csv(salida).set_index("id")
        for col in ["correcto", "observacion"]:
            auditoria[col] = [previa[col].get(i, v) if i in previa.index else v for i, v in zip(auditoria["id"], auditoria[col])]
    auditoria[["id", "modalidad", "texto_fuente", "campos_json", "correcto", "observacion"]].to_csv(
        salida, index=False, encoding="utf-8")
    print(f"FIN: {len(df)} extracciones · JSON válidos {df['json_valido'].sum()}/{len(df)} · auditoría {len(auditoria)} casos")


if __name__ == "__main__":
    main()
