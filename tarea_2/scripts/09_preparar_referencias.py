"""Plantillas, control y validación de las referencias manuales de la muestra congelada.

- Plantillas en datos/raw/referencias/{documentos,audio}/<id>.txt (no versionadas: contendrán
  nombres reales). Contenido inicial: PENDIENTE_REVISION_HUMANA. NUNCA se sobrescriben.
- NO se rellenan con salidas de modelos (OCR, ASR ni LLM): la referencia debe ser humana.
- datos/reportes/control_referencias.csv: estado de revisión que gestiona la autora
  (PENDIENTE_REVISION_HUMANA -> REVISADO_SIN_CAMBIOS / REVISADO_CON_CAMBIOS). Si ya existe, se conserva su estado y
  observación; solo se añaden filas faltantes.
- datos/referencias_estado.csv: validación técnica del contenido (sin texto): existe, UTF-8,
  vacío, contiene PENDIENTE, caracteres y palabras.
Una referencia es APTA para CER/WER solo si tiene texto válido Y la autora la marcó con un estado de
revisión explícito y CONSISTENTE con la huella del borrador (datos/raw/referencias/borradores_snapshot/):
- REVISADO_SIN_CAMBIOS: revisada y el archivo es idéntico al borrador;
- REVISADO_CON_CAMBIOS: revisada y el archivo difiere del borrador.
Si el estado no coincide con lo que muestra el archivo -> INCONSISTENTE (no apta). El estado anterior
REVISADO_HUMANAMENTE ya no basta (0/20 archivos cambiaron al usarlo; ver huellas_borradores_referencias.csv).
Uso: python scripts/09_preparar_referencias.py
"""
from __future__ import annotations

import pandas as pd

from utilidades import DATOS, RAIZ, RAW, REPORTES

PENDIENTE = "PENDIENTE_REVISION_HUMANA"
SIN_CAMBIOS, CON_CAMBIOS = "REVISADO_SIN_CAMBIOS", "REVISADO_CON_CAMBIOS"
DIR_REF = RAW / "referencias"
SNAPSHOT = DIR_REF / "borradores_snapshot"
CONTROL = REPORTES / "control_referencias.csv"


def comparar_con_borrador(ref) -> str:
    previo = SNAPSHOT / ref.name
    if not previo.exists():
        return "sin_borrador"
    return "igual_al_borrador" if previo.read_bytes() == ref.read_bytes() else "modificada"


def consistencia(estado: str, cambio: str) -> str:
    if estado == SIN_CAMBIOS:
        return "ok" if cambio == "igual_al_borrador" else "INCONSISTENTE: marcada sin cambios pero el archivo cambió"
    if estado == CON_CAMBIOS:
        return "ok" if cambio == "modificada" else "INCONSISTENTE: marcada con cambios pero es idéntica al borrador"
    return "pendiente"

# Puntos de atención conocidos ANTES de transcribir (de la imagen, los metadatos y la Parte 1)
OBSERVACIONES = {
    "doc_005": "impreso: portada breve, tipografías de varios tamaños",
    "doc_022": "impreso denso sobre fondo de pergamino; contiene nombres de particulares (archivo privado)",
    "doc_023": "impreso denso sobre fondo de pergamino; contiene nombres de particulares (archivo privado)",
    "doc_008": "foto: documento tabular enmarcado bajo vidrio, letra pequeña y reflejos; transcribir solo lo legible",
    "doc_011": "foto: placa en relieve en mayúsculas; verificar fechas y cifras",
    "doc_019": "foto: panel de exposición con portada de periódico y texto muy pequeño; solo lo legible",
    "doc_001": "manuscrito colonial con muchas firmas: el más difícil; uso esperable de [ilegible]",
    "doc_009": "manuscrito cursivo (1912), página densa",
    "doc_015": "manuscrito cursivo s. XIX con abreviaturas (q., V.)",
    "doc_016": "manuscrito cursivo (1897) con rúbrica y abreviaturas",
    "aud_002": "entrevista en la calle; ritmo de habla rápido",
    "aud_006": "entrevista en la calle; ritmo de habla rápido",
    "aud_010": "entrevista en Plaza San Martín",
    "aud_012": "entrevista; la fuente C tiene el ritmo más rápido del corpus",
    "aud_013": "entrevista a excombatiente; posibles nombres de lugares y fechas",
    "aud_019": "ceremonia con MÚSICA de fondo y varias voces; ASR inestable; esperable [inaudible]",
    "aud_022": "conferencia de prensa al aire libre; ruido de público",
    "aud_023": "conferencia de prensa al aire libre; ruido de público",
    "aud_026": "conferencia de prensa al aire libre; ruido de público; posibles otras voces",
    "aud_028": "MULTIHABLANTE (entrevistador + 2 vendedoras); nombres propios de particulares",
}


def validar(ruta) -> dict:
    if not ruta.exists():
        return {"existe": False, "utf8_valido": False, "vacio": True, "contiene_pendiente": False,
                "n_caracteres": 0, "n_palabras": 0, "contenido": "NO_EXISTE"}
    try:
        texto = ruta.read_bytes().decode("utf-8-sig").strip()
        utf8 = True
    except UnicodeDecodeError:
        texto, utf8 = "", False
    pendiente = PENDIENTE in texto
    vacio = not texto or texto == PENDIENTE
    contenido = ("ERROR_UTF8" if not utf8 else "SIN_TRANSCRIPCION" if vacio
                 else "INCOMPLETA_CONTIENE_PENDIENTE" if pendiente else "CON_TEXTO")
    return {"existe": True, "utf8_valido": utf8, "vacio": vacio, "contiene_pendiente": pendiente,
            "n_caracteres": 0 if vacio else len(texto), "n_palabras": 0 if vacio else len(texto.split()),
            "contenido": contenido}


def main() -> None:
    muestra = pd.read_csv(DATOS / "muestra_evaluacion.csv")
    control_previo = pd.read_csv(CONTROL).set_index("id") if CONTROL.exists() else pd.DataFrame()
    filas, control = [], []
    for _, m in muestra.iterrows():
        sub = "documentos" if m["modalidad"] == "documento" else "audio"
        ref = DIR_REF / sub / f"{m['id']}.txt"
        ref.parent.mkdir(parents=True, exist_ok=True)
        if not ref.exists():
            ref.write_text(PENDIENTE + "\n", encoding="utf-8")
        origen = (RAW / "documentos" / m["archivo"]) if sub == "documentos" else (RAW / "audio" / "clips" / m["archivo"])
        v = validar(ref)
        prev = control_previo.loc[m["id"]] if m["id"] in control_previo.index else None
        estado = prev["estado"] if prev is not None else PENDIENTE
        origen_ref = prev["origen_referencia"] if prev is not None and "origen_referencia" in prev.index else ""
        control.append({"id": m["id"], "modalidad": m["modalidad"],
                        "archivo_referencia": ref.relative_to(RAIZ).as_posix(), "estado": estado,
                        "origen_referencia": "" if pd.isna(origen_ref) else origen_ref,
                        "observacion": prev["observacion"] if prev is not None else OBSERVACIONES.get(m["id"], "")})
        cambio = comparar_con_borrador(ref)
        cons = consistencia(estado, cambio)
        filas.append({"id": m["id"], "modalidad": m["modalidad"], "estrato": m["estrato"],
                      "revisar": origen.relative_to(RAIZ).as_posix(),
                      "archivo_referencia": ref.relative_to(RAIZ).as_posix(), **v, "estado_control": estado,
                      "cambio_vs_borrador": cambio, "consistencia": cons,
                      "apta_para_metricas": v["contenido"] == "CON_TEXTO" and cons == "ok"})
    pd.DataFrame(control).to_csv(CONTROL, index=False, encoding="utf-8")
    df = pd.DataFrame(filas)
    df.to_csv(DATOS / "referencias_estado.csv", index=False, encoding="utf-8")
    print(df[["id", "modalidad", "contenido", "n_palabras", "estado_control", "cambio_vs_borrador",
              "consistencia", "apta_para_metricas"]].to_string(index=False))
    for mod in ["documento", "audio"]:
        d = df[df["modalidad"] == mod]
        print(f"{mod}: con texto {(d['contenido'] == 'CON_TEXTO').sum()}/10 · modificadas vs borrador "
              f"{(d['cambio_vs_borrador'] == 'modificada').sum()}/10 · revisadas (sin/con cambios) "
              f"{d['estado_control'].isin([SIN_CAMBIOS, CON_CAMBIOS]).sum()}/10 · inconsistentes "
              f"{d['consistencia'].str.startswith('INCONSISTENTE').sum()} · aptas para métricas "
              f"{d['apta_para_metricas'].sum()}/10")


if __name__ == "__main__":
    main()
