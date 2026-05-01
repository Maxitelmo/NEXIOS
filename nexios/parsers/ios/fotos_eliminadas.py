# fotos_eliminadas.py — Parser: Fotos eliminadas
# Fuente: AFC /PhotoData/Trash/  (archivos)

import logging
import os
from pathlib import Path

_log = logging.getLogger(__name__)

ARTIFACT_ID = "fotos_eliminadas"
NOMBRE      = "Fotos eliminadas"


def parsear(carpeta_trash: str) -> list[dict]:
    """
    Lista las fotos eliminadas descargadas desde /PhotoData/Trash/.

    Campos por archivo: nombre, ruta_relativa, tamaño_bytes, extension.
    """
    carpeta = Path(carpeta_trash)
    if not carpeta.is_dir():
        _log.warning("Carpeta Trash no encontrada: %s", carpeta_trash)
        return []
    resultados = []
    extensiones_imagen = {".jpg", ".jpeg", ".heic", ".png", ".tiff", ".gif", ".bmp", ".mov", ".mp4"}
    for ruta_abs in sorted(carpeta.rglob("*")):
        if not ruta_abs.is_file():
            continue
        if ruta_abs.suffix.lower() not in extensiones_imagen:
            continue
        resultados.append({
            "nombre": ruta_abs.name,
            "ruta_relativa": str(ruta_abs.relative_to(carpeta)).replace("\\", "/"),
            "tamaño_bytes": ruta_abs.stat().st_size,
            "extension": ruta_abs.suffix.lower(),
        })
    _log.info("Fotos eliminadas: %d archivos", len(resultados))
    return resultados
