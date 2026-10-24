"""Utilidades de gráficos y tiempos para los notebooks.

La exportación PNG (Kaleido + Chrome headless) resultó lenta e irregular en este equipo
(de 3 s a más de 6 min por figura). Por eso NO forma parte del flujo obligatorio: los gráficos
se muestran interactivos y, solo si se pide, se exportan en un subproceso con límite de tiempo
que nunca bloquea la ejecución del notebook.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import time
from pathlib import Path

_SCRIPT_PNG = (
    "import sys, plotly.io as pio\n"
    "fig = pio.read_json(sys.argv[1])\n"
    "fig.write_image(sys.argv[2], width=int(sys.argv[3]), height=int(sys.argv[4]), scale=1)\n"
)


def exportar_png(fig, destino: Path, ancho: int = 1100, alto: int | None = None, limite_s: int = 60) -> str:
    """Exporta un PNG en un subproceso; si supera limite_s se cancela y se informa (no bloquea)."""
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    alto = alto or int(fig.layout.height or 500)
    with tempfile.TemporaryDirectory() as tmp:
        js = Path(tmp) / "fig.json"
        js.write_text(fig.to_json(), encoding="utf-8")
        t0 = time.perf_counter()
        try:
            subprocess.run([sys.executable, "-c", _SCRIPT_PNG, str(js), str(destino), str(ancho), str(alto)],
                           capture_output=True, timeout=limite_s, check=True)
            return f"PNG exportado en {time.perf_counter() - t0:.1f} s: {destino.name}"
        except subprocess.TimeoutExpired:
            return f"PNG cancelado tras {limite_s} s (Kaleido no respondió); se conserva el gráfico interactivo"
        except subprocess.CalledProcessError as e:
            return f"PNG no exportado: {e.stderr.decode('utf-8', 'replace')[-200:]}"


class Cronometro:
    """Registra la duración de cada sección del notebook: marca(nombre) cierra la sección anterior."""

    def __init__(self):
        self.registros: list[dict] = []
        self._actual, self._t0 = None, None

    def marca(self, nombre: str | None = None) -> None:
        ahora = time.perf_counter()
        if self._actual is not None:
            self.registros.append({"seccion": self._actual, "segundos": round(ahora - self._t0, 2)})
        self._actual, self._t0 = nombre, ahora
