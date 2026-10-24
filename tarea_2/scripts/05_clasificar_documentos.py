"""Registra la clasificación de los 25 documentos (aprobada provisionalmente por Mirian, 2026-10-23).

Criterio:
1. "foto": captura con cámara en condiciones no controladas (vidrio, vitrina, relieve,
   pantalla, iluminación desigual), sin importar el tipo de escritura.
2. En otro caso, se clasifica por la escritura DOMINANTE del contenido:
   "impreso" (tipográfico o mecanografiado) o "manuscrito".
3. En formularios mixtos (impreso + relleno a mano) decide la escritura del contenido variable
   que transmite la información principal.

La clasificación es una decisión humana: no se cambia según el desempeño del OCR.
"""
from __future__ import annotations

import pandas as pd

from utilidades import RAW, REPORTES

APROBACION = "aprobada provisionalmente por Mirian (2026-10-23)"

# id: (tipo, observacion_tipo)  — observación vacía = caso no mixto sin particularidades
CLASIFICACION = {
    "doc_001": ("manuscrito", "Manuscrito antiguo (Acta de Independencia) con numerosas firmas superpuestas."),
    "doc_002": ("manuscrito", "Mixto: recibo con formulario impreso (Peruvian Telephone Company, 1895) y contenido "
                              "variable manuscrito (fecha, nombre, monto); se clasifica por el contenido variable."),
    "doc_003": ("manuscrito", "Mixto: recibo impreso (Central & South American Telegraph Co.) con campos manuscritos "
                              "y timbre; se clasifica por el contenido variable."),
    "doc_004": ("foto", "Mixto: carta manuscrita (1938) reproducida en página impresa de libro, capturada con "
                        "iluminación desigual y reflejo; se clasifica por la condición de captura."),
    "doc_005": ("impreso", ""),
    "doc_006": ("impreso", ""),
    "doc_007": ("impreso", "Periódico ilustrado antiguo (1887): papel amarillento, columnas y grabados."),
    "doc_008": ("foto", "Documento enmarcado bajo vidrio: reflejos y perspectiva."),
    "doc_009": ("manuscrito", ""),
    "doc_010": ("impreso", "Mecanografiado (máquina de escribir) con firma manuscrita; domina el texto mecánico."),
    "doc_011": ("foto", "Texto en relieve sobre placa de monumento."),
    "doc_012": ("foto", "Texto en relieve sobre placa de monumento; perspectiva."),
    "doc_013": ("manuscrito", "Manuscrito en lengua awajún (no español) con algunas palabras en español."),
    "doc_014": ("manuscrito", ""),
    "doc_015": ("manuscrito", ""),
    "doc_016": ("manuscrito", ""),
    "doc_017": ("manuscrito", "Mixto: tarjeta manuscrita (Ricardo Palma, 1912) con transcripción impresa añadida al "
                              "pie; la parte impresa puede favorecer al OCR."),
    "doc_018": ("foto", "Documento en vitrina: reflejos y perspectiva."),
    "doc_019": ("foto", "Panel de exposición en perspectiva con textos de distintos tamaños."),
    "doc_020": ("foto", "Documento en vitrina: reflejos fuertes."),
    "doc_021": ("foto", "Fotografía de una pantalla que muestra un texto impreso: moiré y perspectiva. "
                        "El archivo es PNG aunque tiene extensión .jpg."),
    "doc_022": ("impreso", ""),
    "doc_023": ("impreso", ""),
    "doc_024": ("impreso", "Mixto: tarjeta impresa (Policía de Lima, 1921) con relleno manuscrito minoritario; "
                           "domina el texto impreso."),
    "doc_025": ("impreso", "Mapa impreso (1871): texto escaso, disperso y de tamaño variable; imagen de ~93 MP."),
}
ESPERADO = {"impreso": 8, "foto": 8, "manuscrito": 9}


def main() -> None:
    archivos = {p.stem: p.name for p in sorted((RAW / "documentos").iterdir())}
    if set(archivos) != set(CLASIFICACION):
        raise RuntimeError(f"IDs no coinciden con datos/raw/documentos: {set(archivos) ^ set(CLASIFICACION)}")
    fuentes = pd.read_csv(REPORTES / "fuentes_documentos_commons.csv").set_index("archivo")
    df = pd.DataFrame([
        {"id": i, "archivo": archivos[i], "tipo": t, "es_mixto": obs.startswith("Mixto"),
         "observacion_tipo": obs, "titulo_commons": fuentes.loc[archivos[i], "titulo_commons"],
         "aprobacion": APROBACION}
        for i, (t, obs) in CLASIFICACION.items()
    ])
    conteo = df["tipo"].value_counts().to_dict()
    if conteo != ESPERADO:
        raise RuntimeError(f"Distribución {conteo} distinta de la aprobada {ESPERADO}")
    df.to_csv(REPORTES / "clasificacion_documentos.csv", index=False, encoding="utf-8")
    print(df[["id", "tipo", "es_mixto", "titulo_commons"]].to_string(index=False))
    print(f"\nDistribución: {conteo} (coincide con la aprobada) | mixtos: {df['es_mixto'].sum()}")


if __name__ == "__main__":
    main()
