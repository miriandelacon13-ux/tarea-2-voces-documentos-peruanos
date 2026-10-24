"""Ejecuta el ASR principal (faster-whisper small) sobre todos los clips y la diarización por fuente.

Uso: python scripts/07_ejecutar_asr.py [--forzar]
Usa las cachés de asr.py y diarizacion.py (las mismas que lee 01_extraccion.ipynb).
Debe ejecutarse sin otros procesos pesados en paralelo para que tiempos y RTF sean válidos.
"""
from __future__ import annotations

import json
import sys
import time
import traceback

import asr  # importa faster_whisper/ctranslate2 (debe ir antes que cualquier import de paddle)
import diarizacion
from utilidades import RAW


def main() -> None:
    forzar = "--forzar" in sys.argv
    clips = sorted((RAW / "audio" / "clips").glob("aud_*.wav"))
    modelo, t_carga = asr.cargar_modelo()
    print(f"faster-whisper cargado en {t_carga:.1f} s", flush=True)
    (asr.CACHE / "_carga_modelo.json").parent.mkdir(parents=True, exist_ok=True)
    (asr.CACHE / "_carga_modelo.json").write_text(json.dumps({"tiempo_carga_s": round(t_carga, 3)}), encoding="utf-8")
    t_total = time.perf_counter()
    for i, ruta in enumerate(clips, 1):
        try:
            r = asr.transcribir(modelo, ruta, forzar=forzar)
            print(f"[{i:02d}/{len(clips)}] {ruta.name}: {r['duracion_seg']} s, idioma libre "
                  f"{r['idioma_detectado_libre']} ({r['idioma_detectado_prob']}), RTF {r['rtf']}", flush=True)
        except Exception as e:
            (asr.CACHE / f"{ruta.stem}.error.json").write_text(json.dumps(
                {"id": ruta.stem, "error": f"{type(e).__name__}: {e}", "traza": traceback.format_exc()},
                ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"[{i:02d}/{len(clips)}] {ruta.name}: ERROR {type(e).__name__}: {e}", flush=True)
    print(f"FIN ASR: {time.perf_counter() - t_total:.1f} s", flush=True)

    diarizador = diarizacion.crear_diarizador()
    for ruta in sorted((RAW / "audio" / "normalizados").glob("*.flac")):
        try:
            d = diarizacion.diarizar_fuente(diarizador, ruta, forzar=forzar)
            print(f"DIAR {ruta.stem}: {d['n_hablantes_estimado']} hablantes estimados, "
                  f"{len(d['segmentos'])} segmentos, RTF {d['rtf']}", flush=True)
        except Exception as e:
            print(f"DIAR {ruta.stem}: ERROR {type(e).__name__}: {e}", flush=True)
    print("FIN DIARIZACION", flush=True)


if __name__ == "__main__":
    main()
