"""Diarización de hablantes con sherpa-onnx (sin token, sin torch) y alineación con el ASR.

Pipeline (sherpa-onnx 2.0.0, CPU):
- Segmentación: pyannote segmentation-3.0 exportado a ONNX (MIT), ventana deslizante (shift 0,1).
- Embeddings: WeSpeaker ResNet34-LM entrenado en VoxCeleb (Apache-2.0).
- Clustering: FastClustering con num_clusters=-1 (número de hablantes AUTOMÁTICO) y umbral 0,5
  (valor por defecto de sherpa-onnx; mayor umbral -> menos hablantes). min_duration_on=0,3 s,
  min_duration_off=0,5 s.
Se diariza cada FUENTE completa (audio 16 kHz mono idéntico al usado para cortar los clips), de modo
que las etiquetas son consistentes entre clips de la misma fuente. Etiquetas [HABLANTE_k] numeradas
por orden de primera aparición en la fuente.

El número de hablantes resultante es una ESTIMACIÓN automática: requiere revisión humana.
"""
from __future__ import annotations

import json
import subprocess
import time

import numpy as np
import sherpa_onnx

from utilidades import RAIZ, RAW, binario

DIR = RAIZ / "modelos" / "diarizacion"
MODELO_SEG = DIR / "sherpa-onnx-pyannote-segmentation-3-0" / "model.onnx"
MODELO_EMB = DIR / "wespeaker_en_voxceleb_resnet34_LM.onnx"
UMBRAL = 0.5
CACHE = RAW / "cache" / "diarizacion"
SR = 16_000
DESCRIPCION = ("sherpa-onnx 2.0.0: pyannote segmentation-3.0 (ONNX) + WeSpeaker ResNet34-LM; "
               f"FastClustering automático (umbral {UMBRAL})")


def crear_diarizador(hilos: int = 4) -> sherpa_onnx.OfflineSpeakerDiarization:
    config = sherpa_onnx.OfflineSpeakerDiarizationConfig(
        segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
            pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(model=str(MODELO_SEG)),
            num_threads=hilos),
        embedding=sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=str(MODELO_EMB), num_threads=hilos),
        clustering=sherpa_onnx.FastClusteringConfig(num_clusters=-1, threshold=UMBRAL),
        min_duration_on=0.3, min_duration_off=0.5,
    )
    if not config.validate():
        raise RuntimeError("Configuración de diarización inválida (revise rutas de modelos)")
    return sherpa_onnx.OfflineSpeakerDiarization(config)


def audio_16k(ruta) -> np.ndarray:
    """Mismo remuestreo que 03_generar_clips.py (FFmpeg, mono, 16 kHz, s16) -> float32 [-1, 1]."""
    salida = subprocess.run([binario("ffmpeg"), "-nostdin", "-v", "error", "-i", str(ruta), "-map", "0:a:0",
                             "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"], capture_output=True, check=True)
    return np.frombuffer(salida.stdout, dtype=np.int16).astype(np.float32) / 32768


def diarizar_fuente(diarizador, ruta, forzar: bool = False) -> dict:
    CACHE.mkdir(parents=True, exist_ok=True)
    cache = CACHE / f"{ruta.stem}.json"
    if cache.exists() and not forzar:
        return json.loads(cache.read_text(encoding="utf-8"))
    x = audio_16k(ruta)
    t0 = time.perf_counter()
    resultado = diarizador.process(x).sort_by_start_time()
    tiempo = time.perf_counter() - t0
    crudos = [(float(s.start), float(s.end), int(s.speaker)) for s in resultado]
    orden = {}
    for _, _, h in crudos:  # numerar por orden de primera aparición
        orden.setdefault(h, len(orden) + 1)
    segmentos = [{"inicio": round(a, 3), "fin": round(b, 3), "hablante": f"HABLANTE_{orden[h]}"} for a, b, h in crudos]
    salida = {
        "fuente": ruta.stem, "duracion_seg": round(len(x) / SR, 3), "metodo": DESCRIPCION,
        "n_hablantes_estimado": len(orden), "segmentos": segmentos,
        "segundos_por_hablante": {f"HABLANTE_{k}": round(sum(s["fin"] - s["inicio"] for s in segmentos
                                                          if s["hablante"] == f"HABLANTE_{k}"), 2)
                                  for k in range(1, len(orden) + 1)},
        "tiempo_proc_s": round(tiempo, 3), "rtf": round(tiempo / (len(x) / SR), 4),
    }
    cache.write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    return salida


def hablante_de(inicio: float, fin: float, segmentos: list[dict]) -> str | None:
    """Hablante con mayor solapamiento temporal; si no hay solape, el segmento más cercano (≤ 1 s)."""
    mejor, solape_max = None, 0.0
    for s in segmentos:
        solape = min(fin, s["fin"]) - max(inicio, s["inicio"])
        if solape > solape_max:
            mejor, solape_max = s["hablante"], solape
    if mejor is None and segmentos:
        centro = (inicio + fin) / 2
        s = min(segmentos, key=lambda s: min(abs(centro - s["inicio"]), abs(centro - s["fin"])))
        if min(abs(centro - s["inicio"]), abs(centro - s["fin"])) <= 1.0:
            mejor = s["hablante"]
    return mejor


def transcripcion_diarizada(asr: dict, diar: dict, offset_s: float) -> tuple[str, list[str]]:
    """Etiqueta cada palabra del clip (tiempos relativos al clip + offset en la fuente) y agrupa turnos."""
    turnos: list[list] = []
    for seg in asr["segmentos"]:
        for w in seg["palabras"]:
            h = hablante_de(w["inicio"] + offset_s, w["fin"] + offset_s, diar["segmentos"]) or "HABLANTE_?"
            if turnos and turnos[-1][0] == h:
                turnos[-1][1].append(w["palabra"])
            else:
                turnos.append([h, [w["palabra"]]])
    texto = "\n".join(f"[{h}] {''.join(ws).strip()}" for h, ws in turnos)
    presentes = sorted({h for h, _ in turnos if h != "HABLANTE_?"}, key=lambda h: int(h.split("_")[1]))
    return texto, presentes
