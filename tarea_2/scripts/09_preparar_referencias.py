"""Crea las plantillas de referencia manual para la muestra congelada y reporta su estado.

- Plantillas en datos/raw/referencias/{documentos,audio}/<id>.txt (no versionadas: contendrán
  nombres reales). Contenido inicial: PENDIENTE_REVISION_HUMANA.
- NUNCA sobrescribe una plantilla existente (protege lo que la autora ya escribió).
- NO rellena con salidas de modelos (evita sesgar la verdad de referencia).
- Escribe datos/referencias_estado.csv (sin texto): id, modalidad, archivo a revisar,
  archivo de referencia, estado y longitud.
Uso: python scripts/09_preparar_referencias.py   (se puede re-ejecutar para actualizar el estado)
"""
from __future__ import annotations

import pandas as pd

from utilidades import DATOS, RAIZ, RAW

PENDIENTE = "PENDIENTE_REVISION_HUMANA"
DIR_REF = RAW / "referencias"


def estado(ruta) -> tuple[str, int]:
    texto = ruta.read_text(encoding="utf-8").strip()
    if not texto or texto == PENDIENTE:
        return PENDIENTE, 0
    if PENDIENTE in texto:
        return "INCOMPLETA (aún contiene PENDIENTE_REVISION_HUMANA)", len(texto)
    return "COMPLETA", len(texto)


def main() -> None:
    muestra = pd.read_csv(DATOS / "muestra_evaluacion.csv")
    filas = []
    for _, m in muestra.iterrows():
        sub = "documentos" if m["modalidad"] == "documento" else "audio"
        ref = DIR_REF / sub / f"{m['id']}.txt"
        ref.parent.mkdir(parents=True, exist_ok=True)
        creada = not ref.exists()
        if creada:
            ref.write_text(PENDIENTE + "\n", encoding="utf-8")
        est, n = estado(ref)
        origen = (RAW / "documentos" / m["archivo"]) if sub == "documentos" else (RAW / "audio" / "clips" / m["archivo"])
        filas.append({"id": m["id"], "modalidad": m["modalidad"], "estrato": m["estrato"],
                      "revisar": origen.relative_to(RAIZ).as_posix(),
                      "archivo_referencia": ref.relative_to(RAIZ).as_posix(),
                      "estado": est, "n_caracteres": n, "plantilla_creada_ahora": creada})
    df = pd.DataFrame(filas)
    df.to_csv(DATOS / "referencias_estado.csv", index=False, encoding="utf-8")
    print(df[["id", "modalidad", "estrato", "revisar", "estado"]].to_string(index=False))
    print(f"\nCompletas: {(df['estado'] == 'COMPLETA').sum()}/{len(df)}")


if __name__ == "__main__":
    main()
