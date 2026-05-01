# main.py
# Punto de entrada de NEXIOS — Núcleo de Extracción Forense en dispositivos iOS
# Ministerio Público Fiscal de la Nación Córdoba
# Autor: Maximiliano Telmo  |  GPLv3

import logging
import os
import sys
import tkinter
from datetime import datetime

# ── Silenciar errores tardíos de Tcl/Tk ────────────────────────────────────────
_orig_excepthook = sys.excepthook

def _silent_excepthook(exc_type, exc_val, exc_tb):
    if issubclass(exc_type, (tkinter.TclError,)):
        return
    _orig_excepthook(exc_type, exc_val, exc_tb)

sys.excepthook = _silent_excepthook

# ── Importaciones de la aplicación ─────────────────────────────────────────────
from version_nexios import __version__
from nexios.ui.main_window import MainWindow
from nexios.utils.file_system import FileSystemManager

# ── Configuración de logging base ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)

_log = logging.getLogger("nexios")


def main() -> None:
    _log.info("NEXIOS v%s iniciando", __version__)
    fs = FileSystemManager()
    app = MainWindow(version=__version__, file_system=fs)
    app.mainloop()


if __name__ == "__main__":
    main()
