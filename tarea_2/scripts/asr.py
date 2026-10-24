"""ASR principal con faster-whisper (Whisper small, español, VAD Silero) con caché por clip.

Configuración (registrada en cada resultado):
- modelo "small" (Systran/faster-whisper-small), CPU, compute_type="int8";
- language="es", task="transcribe", beam_size=5, vad_filter=True (Silero VAD, parámetros por defecto),
  word_timestamps=True (para alinear con la diarización); resto de parámetros por defecto.
- Detección de idioma independiente (language=None) solo como evidencia del idioma hablado.

Tiempos: tiempo_proc_s = transcripción completa del clip (sin carga del modelo);
RTF = tiempo_proc_s / duración del audio. La carga del modelo se mide aparte.

Incidencia: faster_whisper.decode_audio() (1.2.1) llama a PyAV con `metadata_errors`, parámetro
eliminado en PyAV 19 -> TypeError. Como los clips ya son WAV PCM 16 kHz mono, se leen con
soundfile y se pasa el arreglo float32 al modelo (mismo contenido, sin remuestreo).
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import faster_whisper
import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel

from utilidades import RAIZ, RAW

MODELO = "small"
DISPOSITIVO = "cpu"
TIPO_COMPUTO = "int8"
OPCIONES = {"language": "es", "task": "transcribe", "beam_size": 5, "vad_filter": True, "word_timestamps": True}
CACHE = RAW / "cache" / "asr_faster_whisper_small"
DIR_MODELOS = RAIZ / "modelos" / "faster-whisper"


def cargar_modelo() -> tuple[WhisperModel, float]:
    t0 = time.perf_counter()
    modelo = WhisperModel(MODELO, device=DISPOSITIVO, compute_type=TIPO_COMPUTO, download_root=str(DIR_MODELOS))
    return modelo, time.perf_counter() - t0


def transcribir(modelo: WhisperModel, ruta: Path, forzar: bool = False) -> dict:
    CACHE.mkdir(parents=True, exist_ok=True)
    cache = CACHE / f"{ruta.stem}.json"
    if cache.exists() and not forzar:
        return json.loads(cache.read_text(encoding="utf-8"))

    audio, sr = sf.read(str(ruta), dtype="float32")
    if sr != 16_000 or audio.ndim != 1:
        raise ValueError(f"{ruta.name}: se esperaba WAV mono 16 kHz (sr={sr}, ndim={audio.ndim})")
    audio = np.ascontiguousarray(audio)
    duracion = len(audio) / 16_000

    t0 = time.perf_counter()
    idioma_det, prob_det, _ = modelo.detect_language(audio)
    t_idioma = time.perf_counter() - t0

    t0 = time.perf_counter()
    segmentos_gen, info = modelo.transcribe(audio, **OPCIONES)
    primero = None
    segmentos = []
    for s in segmentos_gen:  # el generador ejecuta la decodificación
        if primero is None:
            primero = time.perf_counter() - t0
        segmentos.append({
            "inicio": round(s.start, 3), "fin": round(s.end, 3), "texto": s.text.strip(),
            "avg_logprob": round(s.avg_logprob, 4), "no_speech_prob": round(s.no_speech_prob, 4),
            "compression_ratio": round(s.compression_ratio, 3),
            "palabras": [{"inicio": round(w.start, 3), "fin": round(w.end, 3), "palabra": w.word,
                          "prob": round(w.probability, 4)} for w in (s.words or [])],
        })
    tiempo = time.perf_counter() - t0

    resultado = {
        "id": ruta.stem, "archivo_audio": ruta.name, "duracion_seg": round(duracion, 3),
        "modelo_asr": f"faster-whisper {faster_whisper.__version__} / whisper-{MODELO} ({TIPO_COMPUTO}, {DISPOSITIVO})",
        "configuracion": OPCIONES,
        "idioma": info.language, "idioma_prob_forzado": round(info.language_probability, 4),
        "idioma_detectado_libre": idioma_det, "idioma_detectado_prob": round(prob_det, 4),
        "tiempo_deteccion_idioma_s": round(t_idioma, 3),
        "duracion_tras_vad_seg": round(info.duration_after_vad, 3),
        "texto_asr": " ".join(s["texto"] for s in segmentos).strip(),
        "n_segmentos": len(segmentos),
        "tiempo_proc_s": round(tiempo, 3),
        "latencia_primer_segmento_s": round(primero, 3) if primero is not None else None,
        "rtf": round(tiempo / duracion, 4),
        "segmentos": segmentos,
        "error": "",
    }
    cache.write_text(json.dumps(resultado, ensure_ascii=False, indent=1), encoding="utf-8")
    return resultado
