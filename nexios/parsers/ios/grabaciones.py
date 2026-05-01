# grabaciones.py — Parser: Grabaciones de voz
# Fuente: AFC /Recordings/  (archivos .m4a)

import logging
import os
from pathlib import Path

_log = logging.getLogger(__name__)

ARTIFACT_ID = "grabaciones"
NOMBRE      = "Grabaciones de voz"


def parsear(carpeta_recordings: str) -> list[dict]:
    """
    Lista los archivos de grabación descargados desde /Recordings/.

    Campos por archivo: nombre, ruta_relativa, tamaño_bytes, extension.
    """
    carpeta = Path(carpeta_recordings)
    if not carpeta.is_dir():
        _log.warning("Carpeta Recordings no encontrada: %s", carpeta_recordings)
        return []
    resultados = []
    for ruta_abs in sorted(carpeta.rglob("*")):
        if not ruta_abs.is_file():
            continue
        resultados.append({
            "nombre": ruta_abs.name,
            "ruta_relativa": str(ruta_abs.relative_to(carpeta)).replace("\\", "/"),
            "tamaño_bytes": ruta_abs.stat().st_size,
            "extension": ruta_abs.suffix.lower(),
        })
    _log.info("Grabaciones: %d archivos", len(resultados))
    return resultados
