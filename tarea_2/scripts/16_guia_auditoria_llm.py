"""Prepara la auditoría humana de las 20 extracciones LLM (no decide nada por la autora).

- datos/GUIA_AUDITORIA_LLM.md: por caso, texto fuente resumido (seudonimizado), campos extraídos y
  problemas detectados automáticamente (solo como alertas; la decisión es humana).
- datos/respuestas_auditoria_llm.txt: plantilla "id: SI|NO | observación" (no se sobrescribe si existe).
Aplicar las respuestas: python scripts/16_guia_auditoria_llm.py --aplicar
  -> actualiza correcto/observacion en datos/auditoria_llm.csv solo para líneas con SI o NO y, cuando los
     20 están decididos, escribe datos/reportes/acuerdo_llm_humano.csv (documentos, audios y total).
"""
from __future__ import annotations

import json
import re
import sys

import pandas as pd

from utilidades import DATOS, REPORTES

PENDIENTE = "PENDIENTE_REVISION_HUMANA"
GUIA = DATOS / "GUIA_AUDITORIA_LLM.md"
RESPUESTAS = DATOS / "respuestas_auditoria_llm.txt"


AUSENCIA_COMO_TEXTO = {"n/a", "na", "null", "none", "no disponible", "desconocido", "no aplica", "-"}


def alertas(fila, campos, fuente, conf_ocr, tipo) -> list[str]:
    al = [f"«{k}» = «{v}» indica ausencia como texto: debería ser null" for k, v in campos.items()
          if isinstance(v, str) and v.strip().lower() in AUSENCIA_COMO_TEXTO]
    if fila["modalidad"] == "documento":
        if conf_ocr is not None and conf_ocr < 0.8:
            al.append(f"OCR de baja confianza ({conf_ocr:.2f}, {tipo}): riesgo de que tema/resumen se basen en texto erróneo")
        if campos.get("emisor") and campos["emisor"].lower() not in fuente.lower():
            al.append("el emisor no aparece literalmente en el texto fuente")
        if fila["verif_fecha_monto"] != "ok":
            al.append(f"fecha/monto: {fila['verif_fecha_monto']}")
        if campos.get("monto"):
            al.append("verifica que el monto sea realmente una cantidad de dinero del documento")
    else:
        if fila["verif_citas"] and not re.match(r"(\d+)/\1 ", fila["verif_citas"] + " "):
            al.append(f"citas literales: {fila['verif_citas']} (alguna puede estar parafraseada o inventada)")
        if fila["verif_hablantes"] != "ok":
            al.append(f"numero_hablantes no coincide con las etiquetas: {fila['verif_hablantes']}")
    if fila.get("texto_truncado"):
        al.append("el texto fuente se truncó a 8000 caracteres para el LLM")
    return al or ["sin alertas automáticas (igual verifica tema y resumen)"]


def generar() -> None:
    aud = pd.read_csv(DATOS / "auditoria_llm.csv")
    ext = pd.read_csv(DATOS / "extraccion_llm.csv").set_index("id")
    docs = pd.read_csv(DATOS / "documentos.csv").set_index("id")
    L = ["# Guía de auditoría humana de la extracción LLM (20 casos)", "",
         "**Qué se evalúa:** si la extracción es **fiel al texto fuente que recibió el LLM** (OCR/ASR seudonimizado), no si "
         "el OCR/ASR era correcto.", "",
         "**Marca SI** cuando se cumplen todas estas condiciones:",
         "- `tema` y `resumen` describen lo que realmente dice el texto, sin agregar hechos;",
         "- `emisor`, `fecha` y `monto` son correctos, o `null` cuando el texto no los contiene;",
         "- las `citas_clave` aparecen en el texto, salvo diferencias mínimas de puntuación;",
         "- `numero_hablantes` coincide con las etiquetas `[HABLANTE_k]` del texto, o es `null` si no hay etiquetas.", "",
         "**Marca NO** si algún campo está inventado o es claramente incorrecto, aunque el resto esté bien. Si es parcial, "
         "pon NO y explica en la observación.", "",
         "**Cómo responder:** completa `datos/respuestas_auditoria_llm.txt`, una línea por caso:",
         "`doc_003: SI` o `aud_017: NO | la cita 2 no está en el texto`.", "",
         "Las alertas automáticas son pistas, **no decisiones**: un caso con alertas puede ser SI y uno sin alertas puede ser NO.", "",
         "---", ""]
    for _, r in aud.iterrows():
        e = ext.loc[r["id"]]
        campos = json.loads(r["campos_json"])
        fuente = str(r["texto_fuente"])
        conf = float(docs.loc[r["id"], "confianza_media"]) if r["modalidad"] == "documento" else None
        tipo = docs.loc[r["id"], "tipo"] if r["modalidad"] == "documento" else "audio"
        extracto = re.sub(r"\s+", " ", fuente)[:420] + ("…" if len(fuente) > 420 else "")
        L += [f"### {r['id']} · {r['modalidad']} ({tipo}) · {len(fuente)} caracteres de texto fuente", "",
              f"**Texto fuente (inicio):** {extracto}", "",
              "**Campos extraídos:**", "", "```json", json.dumps(campos, ensure_ascii=False, indent=1), "```", "",
              "**Alertas automáticas:** " + "; ".join(alertas(e, campos, fuente, conf, tipo)), "",
              f"**Tu decisión:** `{r['id']}: SI` o `{r['id']}: NO | observación`", "", "---", ""]
    GUIA.write_text("\n".join(L), encoding="utf-8")
    if not RESPUESTAS.exists():
        RESPUESTAS.write_text("# Escribe SI o NO después de cada id; observación opcional después de '|'\n"
                              + "\n".join(f"{i}: " for i in aud["id"]) + "\n", encoding="utf-8")
    print(f"Guía: {GUIA.name} ({len(aud)} casos) · plantilla: {RESPUESTAS.name}")


def aplicar() -> None:
    aud = pd.read_csv(DATOS / "auditoria_llm.csv")
    respuestas = {}
    for linea in RESPUESTAS.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*(\w+)\s*:\s*(SI|SÍ|NO)\s*(?:\|\s*(.*))?$", linea, re.I)
        if m:
            respuestas[m.group(1)] = ("SI" if m.group(2).upper() in ("SI", "SÍ") else "NO", (m.group(3) or "").strip())
    aud["observacion"] = aud["observacion"].astype("object").fillna("")
    for i, (decision, obs) in respuestas.items():
        aud.loc[aud["id"] == i, ["correcto", "observacion"]] = [decision, obs]
    aud.to_csv(DATOS / "auditoria_llm.csv", index=False, encoding="utf-8")
    decididos = aud["correcto"].isin(["SI", "NO"])
    print(f"Respuestas aplicadas: {len(respuestas)} · decididos {decididos.sum()}/{len(aud)} · pendientes {(~decididos).sum()}")
    if decididos.all():
        acuerdo = acuerdo_por_modalidad(aud)
        acuerdo.to_csv(REPORTES / "acuerdo_llm_humano.csv", index=False, encoding="utf-8")
        for _, f in acuerdo.iterrows():
            print(f"Acuerdo LLM-humano ({f['modalidad']}): {f['correctos']}/{f['n']} = {100 * f['acuerdo']:.0f} %")
    elif REPORTES.joinpath("acuerdo_llm_humano.csv").exists():
        REPORTES.joinpath("acuerdo_llm_humano.csv").unlink()  # un acuerdo parcial no se reporta


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Intervalo de Wilson al 95 % para una proporción (adecuado con n pequeño)."""
    p = k / n
    centro = (p + z * z / (2 * n)) / (1 + z * z / n)
    margen = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / (1 + z * z / n)
    return centro - margen, centro + margen


def acuerdo_por_modalidad(aud: pd.DataFrame) -> pd.DataFrame:
    """Proporción de extracciones que la autora juzgó correctas (SI), por modalidad y total."""
    filas = []
    for nombre, d in [("documento", aud[aud["modalidad"] == "documento"]),
                      ("audio", aud[aud["modalidad"] == "audio"]), ("total", aud)]:
        n_si = int((d["correcto"] == "SI").sum())
        bajo, alto = wilson(n_si, len(d))
        filas.append({"modalidad": nombre, "n": len(d), "correctos": n_si, "incorrectos": len(d) - n_si,
                      "acuerdo": n_si / len(d), "ic95_inf": bajo, "ic95_sup": alto})
    return pd.DataFrame(filas)


if __name__ == "__main__":
    aplicar() if "--aplicar" in sys.argv else generar()
