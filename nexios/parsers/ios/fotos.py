# fotos.py — Parser: Fotos + EXIF
# Fuente: AFC /DCIM/  (archivos + metadata EXIF)

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

_log = logging.getLogger(__name__)

ARTIFACT_ID = "fotos"
NOMBRE      = "Fotos + EXIF"

try:
    from PIL import Image
    from PIL.ExifTags import TAGS, GPSTAGS
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False


def parsear(carpeta_dcim: str) -> list[dict]:
    """
    Recorre la carpeta DCIM descargada y extrae metadata EXIF de cada imagen.

    Returns:
        Lista de dicts con: ruta_relativa, nombre, tamaño_bytes, fecha_exif,
        gps_lat, gps_lon, modelo_camara, sha256.
    """
    if not _PIL_AVAILABLE:
        _log.warning("Pillow no disponible — EXIF no extraíble")
        return []
    resultados = []
    extensiones = {".jpg", ".jpeg", ".heic", ".png", ".tiff", ".mov", ".mp4"}
    for root, _, files in os.walk(carpeta_dcim):
        for name in files:
            if Path(name).suffix.lower() not in extensiones:
                continue
            ruta_abs = os.path.join(root, name)
            ruta_rel = os.path.relpath(ruta_abs, carpeta_dcim)
            info: dict = {
                "ruta_relativa": ruta_rel.replace("\\", "/"),
                "nombre": name,
                "tamaño_bytes": os.path.getsize(ruta_abs),
                "fecha_exif": "",
                "gps_lat": None,
                "gps_lon": None,
                "modelo_camara": "",
            }
            _extraer_exif(ruta_abs, info)
            resultados.append(info)
    _log.info("Fotos: %d archivos en DCIM", len(resultados))
    return resultados


def _extraer_exif(ruta: str, info: dict) -> None:
    try:
        img = Image.open(ruta)
        exif_data = img._getexif()
        if not exif_data:
            return
        for tag_id, valor in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag == "DateTimeOriginal":
                info["fecha_exif"] = str(valor)
            elif tag == "Model":
                info["modelo_camara"] = str(valor)
            elif tag == "GPSInfo":
                info["gps_lat"], info["gps_lon"] = _gps_coords(valor)
    except Exception:
        pass


def _gps_coords(gps_info: dict) -> tuple[Optional[float], Optional[float]]:
    try:
        def _to_deg(value):
            d, m, s = value
            return float(d) + float(m) / 60 + float(s) / 3600

        lat = _to_deg(gps_info[2])
        if gps_info[1] == "S":
            lat = -lat
        lon = _to_deg(gps_info[4])
        if gps_info[3] == "W":
            lon = -lon
        return round(lat, 6), round(lon, 6)
    except Exception:
        return None, None
