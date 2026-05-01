# file_system.py
# Gestión de rutas y sistema de archivos portable — portado de CAPTA.

import ctypes
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from version_nexios import __version__ as NEXIOS_VERSION
except ImportError:
    NEXIOS_VERSION = "1.0.0"

# ── Tipos de unidad Windows (GetDriveType) ─────────────────────────────────────
DRIVE_UNKNOWN   = 0
DRIVE_NO_ROOT   = 1
DRIVE_REMOVABLE = 2
DRIVE_FIXED     = 3
DRIVE_REMOTE    = 4
DRIVE_CDROM     = 5
DRIVE_RAMDISK   = 6

ALLOWED_EVIDENCE_DRIVE_TYPES = (DRIVE_REMOVABLE, DRIVE_FIXED)
EVIDENCIAS_ROOT_FOLDER = "Relevamientos_NEXIOS"

_evidence_root: Optional[str] = None
_riesgo_evidencias_en_sistema: bool = False


def is_path_under(base: str, path: str) -> bool:
    if not base or not path:
        return False
    base_abs = os.path.abspath(os.path.normpath(base))
    path_abs = os.path.abspath(os.path.normpath(path))
    return path_abs == base_abs or path_abs.startswith(base_abs + os.sep)


def safe_join_and_validate(base: str, *parts: str) -> str:
    """Une base con parts y verifica que el resultado esté bajo base (anti path-traversal)."""
    full = os.path.join(base, *parts)
    if not is_path_under(base, full):
        raise ValueError(f"Ruta fuera del directorio permitido: {full}")
    return full


def obtener_unidad_nexios() -> str:
    ruta = sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__)
    drive = (os.path.splitdrive(ruta)[0] or "").upper()
    if not drive:
        return ""
    return drive if drive.endswith(":") else drive + ":"


def _get_drive_type_windows(letra: str) -> int:
    if not letra or sys.platform != "win32":
        return DRIVE_UNKNOWN
    root = letra.rstrip(":") + ":\\"
    try:
        return ctypes.windll.kernel32.GetDriveTypeW(root)
    except Exception:
        return DRIVE_UNKNOWN


def set_evidence_root(ruta: Optional[str], riesgo_en_sistema: bool = False) -> None:
    global _evidence_root, _riesgo_evidencias_en_sistema
    _evidence_root = (ruta or "").strip() or None
    _riesgo_evidencias_en_sistema = bool(riesgo_en_sistema)


def get_evidence_root() -> Optional[str]:
    return _evidence_root


def build_case_paths(evidence_root: str, metadatos_caso: Dict[str, Any]) -> Dict[str, str]:
    """Construye todas las rutas de un caso bajo la raíz de evidencias."""
    expediente = (metadatos_caso.get("expediente") or "").strip()
    caso       = (metadatos_caso.get("caso") or "").strip()
    timestamp  = (metadatos_caso.get("timestamp") or "").strip()
    if not expediente or not caso:
        raise ValueError("metadatos_caso debe incluir expediente y caso")
    for c in '<>:"/\\|?*':
        expediente = expediente.replace(c, "_")
        caso = caso.replace(c, "_")
    expediente = "_".join(expediente.split())
    caso = "_".join(caso.replace(" ", "_").split())
    if not timestamp:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre = f"{expediente}_{caso}_{timestamp}"
    carpeta = os.path.join(evidence_root, nombre)
    return {
        "carpeta_relevamiento": carpeta,
        "reporte_folder": os.path.join(carpeta, "Reporte_Forense"),
        "artifacts_folder": os.path.join(carpeta, "Artifacts"),
        "capturas_folder": os.path.join(carpeta, "Capturas"),
        "fotos_folder": os.path.join(carpeta, "Fotos_Operativo"),
        "logs_folder": os.path.join(carpeta, "Logs"),
    }


class FileSystemManager:
    """Gestiona rutas y estructura de archivos del sistema forense NEXIOS."""

    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.base_path = self._detect_base_path()
        self.save_path = self._detect_save_path()

    @staticmethod
    def _detect_base_path() -> str:
        if getattr(sys, "frozen", False):
            return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.abspath(__file__))

    def _detect_save_path(self) -> str:
        try:
            root = get_evidence_root()
            if root:
                os.makedirs(root, exist_ok=True)
                return root
            ruta_ejecucion = sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__)
            unidad = os.path.splitdrive(ruta_ejecucion)[0].upper()
            if unidad != "C:":
                ruta_base = os.path.join(unidad + os.sep, EVIDENCIAS_ROOT_FOLDER)
                self.logger.info("Modo PORTABLE detectado: %s", unidad)
            else:
                ruta_base = os.path.join("C:\\NEXIOS_Relevamientos")
                self.logger.info("Modo LOCAL detectado: C:")
            os.makedirs(ruta_base, exist_ok=True)
            return ruta_base
        except Exception as e:
            self.logger.error("Error determinando ruta de guardado: %s", e)
            return os.getcwd()

    def get_base_path(self) -> str:
        return self.base_path

    def get_save_path(self) -> str:
        root = get_evidence_root()
        return root if root else self.save_path

    def create_relevamiento_structure(
        self, expediente: str, caso: str, operador: str
    ) -> tuple[str, str]:
        """Crea la estructura de carpetas para un nuevo relevamiento. Devuelve (carpeta, timestamp)."""
        if not expediente or not caso:
            raise ValueError("Expediente y caso son obligatorios")
        evidence_root = self.get_save_path()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        metadatos = {"expediente": expediente, "caso": caso, "timestamp": timestamp}
        paths = build_case_paths(evidence_root, metadatos)
        carpeta = paths["carpeta_relevamiento"]
        os.makedirs(carpeta, exist_ok=True)
        for key in ("reporte_folder", "artifacts_folder", "capturas_folder",
                    "fotos_folder", "logs_folder"):
            os.makedirs(paths[key], exist_ok=True)
        self._write_metadata(carpeta, expediente, caso, operador, timestamp)
        self.logger.info("Estructura de relevamiento creada: %s", carpeta)
        return carpeta, timestamp

    def _write_metadata(self, carpeta, expediente, caso, operador, timestamp):
        try:
            ruta = safe_join_and_validate(carpeta, "metadata.txt")
            with open(ruta, "w", encoding="utf-8") as f:
                f.write("RELEVAMIENTO FORENSE — NEXIOS\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Expediente : {expediente}\n")
                f.write(f"Caso       : {caso}\n")
                f.write(f"Operador   : {operador}\n")
                f.write(f"Inicio     : {timestamp}\n")
                f.write(f"Sistema    : NEXIOS v{NEXIOS_VERSION}\n")
                f.write("\n" + "=" * 50 + "\n")
        except Exception as e:
            self.logger.warning("No se pudo escribir metadata.txt: %s", e)
