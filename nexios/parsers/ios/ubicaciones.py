# ubicaciones.py — Parser: Ubicaciones Maps
# Fuente: HomeDomain/Library/Maps/GeoHistory.mapsdata  (plist binario / SQLite)

import logging
import plistlib
from pathlib import Path

_log = logging.getLogger(__name__)

ARTIFACT_ID = "ubicaciones"
NOMBRE      = "Ubicaciones Maps"


def parsear(ruta_archivo: str) -> list[dict]:
    """
    Parsea GeoHistory.mapsdata. Devuelve lista de ubicaciones buscadas/visitadas.

    Campos: latitud, longitud, nombre, fecha_raw.
    # GeoHistory.mapsdata es un plist binario que encapsula un SQLite — ver TODO.
    """
    ruta = Path(ruta_archivo)
    if not ruta.is_file():
        _log.warning("GeoHistory.mapsdata no encontrado: %s", ruta_archivo)
        return []
    resultados = []
    try:
        # GeoHistory.mapsdata es en realidad un contenedor; intentar como plist primero
        with open(ruta, "rb") as f:
            data = plistlib.load(f)
        # TODO: parsear estructura interna del plist según versión de iOS
        _log.debug("GeoHistory.mapsdata cargado (plist), estructura: %s", type(data).__name__)
    except Exception as e:
        _log.error("Error parseando GeoHistory.mapsdata: %s", e)
    _log.info("Ubicaciones: %d registros", len(resultados))
    return resultados
