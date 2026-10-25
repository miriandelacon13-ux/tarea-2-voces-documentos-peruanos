"""ASR alternativo: NVIDIA Parakeet TDT 0.6B v3 (multilingüe, incluye español) vía sherpa-onnx.

Elección y viabilidad (Windows 11, Python 3.13, CPU, 15,5 GB RAM, GPU de 4 GB sin CUDA en el entorno):
- Arquitectura distinta de Whisper (FastConformer + Token-and-Duration Transducer) y de otro fabricante.
- Exportación ONNX int8 de k2-fsa (sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8): corre con
  sherpa-onnx, ya instalado; no requiere torch ni NeMo (problemáticos en Windows y en conflicto de
  DLL con paddle). Qwen3-ASR o MMS requerirían torch/transformers en el mismo entorno.
- El modelo detecta el idioma automáticamente (25 idiomas europeos); no se le puede forzar «es».
Decodificación: greedy_search (por defecto del modelo). Tiempo medido solo en decode_stream.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import sherpa_onnx
import soundfile as sf

from utilidades import RAIZ, RAW

DIR = RAIZ / "modelos" / "asr_parakeet" / "sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8"
CACHE = RAW / "cache" / "asr_parakeet_tdt_v3"
NOMBRE = "Parakeet TDT 0.6B v3 (NVIDIA, int8 ONNX vía sherpa-onnx, CPU, greedy)"


def cargar_modelo(hilos: int = 8):
    t0 = time.perf_counter()
    reconocedor = sherpa_onnx.OfflineRecognizer.from_transducer(
        encoder=str(DIR / "encoder.int8.onnx"), decoder=str(DIR / "decoder.int8.onnx"),
        joiner=str(DIR / "joiner.int8.onnx"), tokens=str(DIR / "tokens.txt"),
        num_threads=hilos, sample_rate=16_000, feature_dim=80,
        decoding_method="greedy_search", model_type="nemo_transducer")
    return reconocedor, time.perf_counter() - t0


def transcribir(reconocedor, ruta: Path, forzar: bool = False) -> dict:
    CACHE.mkdir(parents=True, exist_ok=True)
    cache = CACHE / f"{ruta.stem}.json"
    if cache.exists() and not forzar:
        return json.loads(cache.read_text(encoding="utf-8"))
    audio, sr = sf.read(str(ruta), dtype="float32")
    if sr != 16_000 or audio.ndim != 1:
        raise ValueError(f"{ruta.name}: se esperaba WAV mono 16 kHz")
    flujo = reconocedor.create_stream()
    flujo.accept_waveform(16_000, np.ascontiguousarray(audio))
    t0 = time.perf_counter()
    reconocedor.decode_stream(flujo)
    tiempo = time.perf_counter() - t0
    duracion = len(audio) / 16_000
    resultado = {
        "id": ruta.stem, "archivo_audio": ruta.name, "duracion_seg": round(duracion, 3),
        "modelo_asr": f"{NOMBRE}; sherpa-onnx {sherpa_onnx.__version__}",
        "texto_asr": flujo.result.text.strip(),
        "tiempo_proc_s": round(tiempo, 3), "rtf": round(tiempo / duracion, 4),
        # Modelo offline: la primera palabra solo está disponible al terminar el clip completo
        "latencia_primer_segmento_s": round(tiempo, 3),
        "error": "",
    }
    cache.write_text(json.dumps(resultado, ensure_ascii=False, indent=1), encoding="utf-8")
    return resultado
