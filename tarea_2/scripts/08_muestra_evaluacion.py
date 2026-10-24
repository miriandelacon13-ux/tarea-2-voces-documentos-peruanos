"""Fija y CONGELA la muestra de evaluación: 10 documentos y 10 clips (semilla reproducible).

Diseño (decidido antes de mirar cualquier métrica; usa solo metadatos, nunca resultados OCR/ASR):
- Documentos: muestreo aleatorio estratificado por tipo: 3 impresos, 3 fotos, 4 manuscritos
  (proporcional a 8/8/9). Marco muestral: los 25 documentos excepto doc_025, excluido A PRIORI
  por factibilidad: es un mapa con ~1 400 rótulos cuya transcripción manual completa no es viable.
- Clips: asignación proporcional al número de clips por fuente (resto mayor) con mínimo 1 por
  fuente, para que las 7 fuentes estén representadas; empates resueltos con la misma semilla.
- Semilla: numpy.random.default_rng(20261024).

Congelamiento: si datos/muestra_evaluacion.csv ya existe, el script NO lo sobrescribe; solo
verifica que la selección reproducida sea idéntica y muestra la huella SHA-256 de la muestra.
"""
from __future__ import annotations

import hashlib
import sys
from datetime import date

import numpy as np
import pandas as pd

from utilidades import DATOS, RAW, REPORTES, sha256

SEMILLA = 20261024
CUOTA_TIPO = {"impreso": 3, "foto": 3, "manuscrito": 4}
EXCLUIDOS_A_PRIORI = {"doc_025": "mapa con ~1 400 rótulos: referencia manual completa no factible"}
N_CLIPS = 10
SALIDA = DATOS / "muestra_evaluacion.csv"


def seleccionar() -> pd.DataFrame:
    rng = np.random.default_rng(SEMILLA)
    clasif = pd.read_csv(REPORTES / "clasificacion_documentos.csv")
    marco = clasif[~clasif["id"].isin(EXCLUIDOS_A_PRIORI)].sort_values("id")
    filas = []
    for tipo, k in CUOTA_TIPO.items():
        candidatos = marco.loc[marco["tipo"] == tipo, "id"].tolist()
        for orden, i in enumerate(sorted(rng.choice(candidatos, size=k, replace=False)), 1):
            filas.append({"id": i, "modalidad": "documento", "estrato": tipo, "tamano_estrato": len(candidatos),
                          "archivo": marco.set_index("id").loc[i, "archivo"]})

    clips = pd.read_csv(REPORTES / "clips_audio.csv")
    clips["fuente_id"] = clips["fuente"].str.replace(r"\.\w+$", "", regex=True)
    por_fuente = clips.groupby("fuente_id")["id"].apply(sorted).to_dict()
    cuota = {f: N_CLIPS * len(v) / len(clips) for f, v in por_fuente.items()}
    asignacion = {f: max(1, int(c)) for f, c in cuota.items()}
    faltan = N_CLIPS - sum(asignacion.values())
    desempate = dict(zip(sorted(cuota), rng.random(len(cuota))))
    # Resto = cuota - asignación ya hecha (tras aplicar el mínimo de 1). Corrección del 2026-10-24,
    # hecha antes de calcular cualquier métrica: la primera versión usaba cuota - int(cuota) y daba
    # un clip extra a la fuente C, que ya superaba su cuota (0,67) por el mínimo de 1.
    for f in sorted(cuota, key=lambda f: (cuota[f] - asignacion[f], desempate[f]), reverse=True)[:faltan]:
        asignacion[f] += 1
    for f in sorted(asignacion):
        for i in sorted(rng.choice(por_fuente[f], size=asignacion[f], replace=False)):
            filas.append({"id": i, "modalidad": "audio", "estrato": f, "tamano_estrato": len(por_fuente[f]),
                          "archivo": f"{i}.wav"})
    df = pd.DataFrame(filas)
    carpeta = {"documento": RAW / "documentos", "audio": RAW / "audio" / "clips"}
    df["sha256_archivo"] = [sha256(carpeta[m] / a) for m, a in zip(df["modalidad"], df["archivo"])]
    df["semilla"] = SEMILLA
    return df


def huella(df: pd.DataFrame) -> str:
    return hashlib.sha256(",".join(sorted(df["id"])).encode()).hexdigest()


def main() -> None:
    nueva = seleccionar()
    if SALIDA.exists():
        congelada = pd.read_csv(SALIDA)
        if sorted(congelada["id"]) != sorted(nueva["id"]):
            sys.exit("ERROR: la selección reproducida difiere de la muestra congelada; no se modifica nada.")
        print(f"Muestra congelada verificada (sin cambios). Huella: {huella(congelada)}")
        return
    nueva["fecha_congelacion"] = date.today().isoformat()
    nueva["excluidos_a_priori"] = "; ".join(f"{k}: {v}" for k, v in EXCLUIDOS_A_PRIORI.items())
    nueva.to_csv(SALIDA, index=False, encoding="utf-8")
    print(nueva[["id", "modalidad", "estrato", "tamano_estrato"]].to_string(index=False))
    print(f"\nMuestra CONGELADA en {SALIDA.name} · huella SHA-256: {huella(nueva)}")


if __name__ == "__main__":
    main()
