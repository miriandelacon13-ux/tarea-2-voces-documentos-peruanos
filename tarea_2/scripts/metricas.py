"""Cálculo de CER/WER sobre la muestra congelada usando EXCLUSIVAMENTE scripts/evaluacion.py.

- Hipótesis: salidas en caché (no se re-ejecuta OCR/ASR): PaddleOCR y Tesseract (datos/raw/cache/ocr_*),
  faster-whisper small (Parte 1) y Parakeet TDT v3 (datos/raw/cache/asr_*).
- Referencias: datos/raw/referencias/{documentos,audio}/<id>.txt, solo si 09_preparar_referencias.py las
  declaró aptas (texto válido + estado de revisión consistente con la huella del borrador).
- Métricas: CER (principal, conserva tildes), CER sin tildes (sensibilidad), WER; con S/D/I/N.
Uso: python scripts/metricas.py  -> datos/reportes/metricas_ocr.csv, metricas_asr.csv, resumen_metricas.csv
"""
from __future__ import annotations

import json

import pandas as pd

from evaluacion import agregar, cer, normalizar_cer, normalizar_wer, wer
from utilidades import DATOS, RAW, REPORTES

CACHE = RAW / "cache"
OCR = {"PaddleOCR": CACHE / "ocr_paddleocr", "Tesseract": CACHE / "ocr_tesseract"}
ASR = {"faster-whisper small": CACHE / "asr_faster_whisper_small", "Parakeet TDT 0.6B v3": CACHE / "asr_parakeet_tdt_v3"}


def _texto(carpeta, i, campo):
    return json.loads((carpeta / f"{i}.json").read_text(encoding="utf-8"))[campo]


def referencias_aptas() -> pd.DataFrame:
    estado = pd.read_csv(DATOS / "referencias_estado.csv")
    if not estado["apta_para_metricas"].all():
        faltan = estado.loc[~estado["apta_para_metricas"], "id"].tolist()
        raise RuntimeError(f"Referencias no aptas (ejecute 09_preparar_referencias.py): {faltan}")
    estado["referencia"] = [(RAW / "referencias" / ("documentos" if m == "documento" else "audio") / f"{i}.txt")
                            .read_text(encoding="utf-8") for i, m in zip(estado["id"], estado["modalidad"])]
    return estado


def calcular() -> dict[str, pd.DataFrame]:
    refs = referencias_aptas()
    clasif = pd.read_csv(REPORTES / "clasificacion_documentos.csv").set_index("id")["tipo"]
    clips = pd.read_csv(REPORTES / "clips_audio.csv").set_index("id")
    filas_ocr, filas_asr = [], []
    for _, r in refs[refs["modalidad"] == "documento"].iterrows():
        for modelo, carpeta in OCR.items():
            hip = _texto(carpeta, r["id"], "texto_ocr")
            m, s = cer(r["referencia"], hip), cer(r["referencia"], hip, quitar_tildes=True)
            filas_ocr.append({"id": r["id"], "tipo": clasif[r["id"]], "modelo": modelo, "cer": m["cer"],
                              "cer_sin_tildes": s["cer"], "S": m["S"], "D": m["D"], "I": m["I"], "N": m["N"],
                              "caracteres_hipotesis": len(normalizar_cer(hip)),
                              "ilegible_en_referencia": r["referencia"].count("[ilegible]")})
    for _, r in refs[refs["modalidad"] == "audio"].iterrows():
        for modelo, carpeta in ASR.items():
            hip = _texto(carpeta, r["id"], "texto_asr")
            m = wer(r["referencia"], hip)
            filas_asr.append({"id": r["id"], "fuente": clips.loc[r["id"], "fuente"].rsplit(".", 1)[0],
                              "duracion_s": clips.loc[r["id"], "duracion_real_s"], "modelo": modelo, "wer": m["wer"],
                              "S": m["S"], "D": m["D"], "I": m["I"], "N": m["N"],
                              "palabras_hipotesis": len(normalizar_wer(hip).split()),
                              "inaudible_en_referencia": r["referencia"].count("[inaudible]"),
                              "referencia_revisada": r["estado_control"]})
    ocr, asr_ = pd.DataFrame(filas_ocr), pd.DataFrame(filas_asr)

    resumen = []
    for modelo in OCR:
        d = ocr[ocr["modelo"] == modelo]
        g = agregar(d.to_dict("records"), "cer")
        fila = {"modalidad": "documento", "modelo": modelo, "metrica": "CER", "promedio": g["macro"],
                "ponderado": g["micro"], "cer_sin_tildes_promedio": d["cer_sin_tildes"].mean(), "n": g["n"]}
        for tipo in ["impreso", "foto", "manuscrito"]:
            fila[f"promedio_{tipo}"] = d.loc[d["tipo"] == tipo, "cer"].mean()
        resumen.append(fila)
    for modelo in ASR:
        d = asr_[asr_["modelo"] == modelo]
        g = agregar(d.to_dict("records"), "wer")
        resumen.append({"modalidad": "audio", "modelo": modelo, "metrica": "WER", "promedio": g["macro"],
                        "ponderado": g["micro"], "n": g["n"]})
    resumen = pd.DataFrame(resumen)

    bench = pd.read_csv(REPORTES / "benchmark_tiempos.csv")
    nombre = {"faster-whisper small": "faster-whisper small", "Parakeet TDT 0.6B v3": "Parakeet TDT 0.6B v3",
              "PaddleOCR": "PaddleOCR", "Tesseract": "Tesseract"}
    elem = bench[bench["id"] != "_carga_modelo"]
    efic = elem.groupby("modelo").agg(tiempo_mediano_s=("tiempo_s", "median"), tiempo_total_s=("tiempo_s", "sum"),
                                      rtf_mediano=("rtf", "median"), rtf_max=("rtf", "max"),
                                      identicos=("texto_identico_a_cache", lambda s: int(s.fillna(False).sum())),
                                      con_dato_estabilidad=("texto_identico_a_cache", lambda s: int(s.notna().sum())))
    carga = bench[bench["id"] == "_carga_modelo"].set_index("modelo")["tiempo_s"].rename("carga_modelo_s")
    efic = efic.join(carga).reset_index()
    efic["estabilidad"] = [f"{a}/{b}" if b else "no medida" for a, b in zip(efic["identicos"], efic["con_dato_estabilidad"])]
    resumen = resumen.merge(efic[["modelo", "tiempo_mediano_s", "rtf_mediano", "estabilidad", "carga_modelo_s"]],
                            on="modelo", how="left")
    resumen["menor_es_mejor"] = True

    for df, clave in [(ocr, "cer"), (asr_, "wer")]:
        piv = df.pivot(index="id", columns="modelo", values=clave)
        mejor = piv.idxmin(axis=1).where(piv.nunique(axis=1) > 1, "empate")
        df["mejor_modelo_del_elemento"] = df["id"].map(mejor)
    ocr.to_csv(REPORTES / "metricas_ocr.csv", index=False, encoding="utf-8")
    asr_.to_csv(REPORTES / "metricas_asr.csv", index=False, encoding="utf-8")
    resumen.to_csv(REPORTES / "resumen_metricas.csv", index=False, encoding="utf-8")
    return {"ocr": ocr, "asr": asr_, "resumen": resumen, "eficiencia": efic, "referencias": refs}


if __name__ == "__main__":
    r = calcular()
    pd.set_option("display.width", 220)
    print(r["resumen"].round(4).to_string(index=False))
    print(r["ocr"].pivot(index=["id", "tipo"], columns="modelo", values="cer").round(3).to_string())
    print(r["asr"].pivot(index=["id", "fuente"], columns="modelo", values="wer").round(3).to_string())
