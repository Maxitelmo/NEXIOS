# fotos_operativo.py
# Módulo de fotografías manuales del operador.
# El operador importa fotos tomadas con su propio dispositivo (cámara, celular)
# para incorporarlas al expediente con trazabilidad completa.

import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from nexios.utils.file_system import safe_join_and_validate
from nexios.utils.hash_utils import calcular_hash
from nexios.utils.forensic_log_chain import append_evento_forense

_log = logging.getLogger(__name__)

try:
    from PIL import Image
    from PIL.ExifTags import TAGS, GPSTAGS
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False


def importar_foto(
    ruta_origen: str,
    carpeta_fotos: str,
    carpeta_relevamiento: str,
    operador: str,
    descripcion: str = "",
    numero: int = 1,
) -> dict:
    """
    Importa una foto al expediente forense con trazabilidad completa.

    Args:
        ruta_origen: Ruta de la foto original.
        carpeta_fotos: Carpeta destino dentro del relevamiento.
        carpeta_relevamiento: Carpeta raíz del relevamiento (para log).
        operador: Nombre del operador que tomó la foto.
        descripcion: Descripción libre del contenido.
        numero: Número correlativo en el expediente.

    Returns:
        dict con: ok, ruta_local, sha256, timestamp_importacion,
                  exif (dict), operador, descripcion, numero.
    """
    resultado: dict = {
        "ok": False,
        "ruta_local": "",
        "sha256": "",
        "timestamp_importacion": "",
        "exif": {},
        "operador": operador,
        "descripcion": descripcion,
        "numero": numero,
        "mensaje": "",
    }
    ruta = Path(ruta_origen)
    if not ruta.is_file():
        resultado["mensaje"] = f"Archivo no encontrado: {ruta_origen}"
        return resultado
    try:
        os.makedirs(carpeta_fotos, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = ruta.suffix.lower()
        nombre_destino = f"foto_operativo_{numero:03d}_{timestamp}{ext}"
        ruta_local = safe_join_and_validate(carpeta_fotos, nombre_destino)
        shutil.copy2(str(ruta), ruta_local)
        sha = calcular_hash(ruta_local)
        exif = _extraer_exif(ruta_local) if _PIL_AVAILABLE else {}
        resultado.update({
            "ok": True,
            "ruta_local": ruta_local,
            "sha256": sha,
            "timestamp_importacion": timestamp,
            "exif": exif,
        })
        append_evento_forense(
            carpeta_relevamiento,
            f"FOTO OPERATIVO: {nombre_destino} | sha256={sha} | operador={operador}"
            + (f" | desc={descripcion}" if descripcion else "")
            + (f" | fecha_exif={exif.get('fecha')}" if exif.get("fecha") else "")
        )
        _log.info("Foto importada: %s", ruta_local)
    except Exception as e:
        resultado["mensaje"] = str(e)
        _log.error("Error importando foto %s: %s", ruta_origen, e)
    return resultado


def importar_lote(
    rutas_origen: list[str],
    carpeta_fotos: str,
    carpeta_relevamiento: str,
    operador: str,
    descripciones: Optional[list[str]] = None,
    numero_inicio: int = 1,
) -> list[dict]:
    """Importa múltiples fotos en secuencia. Devuelve lista de resultados."""
    resultados = []
    for i, ruta in enumerate(rutas_origen):
        desc = (descripciones[i] if descripciones and i < len(descripciones) else "")
        r = importar_foto(
            ruta_origen=ruta,
            carpeta_fotos=carpeta_fotos,
            carpeta_relevamiento=carpeta_relevamiento,
            operador=operador,
            descripcion=desc,
            numero=numero_inicio + i,
        )
        resultados.append(r)
    return resultados


def _extraer_exif(ruta: str) -> dict:
    exif: dict = {}
    try:
        img = Image.open(ruta)
        raw = img._getexif()
        if not raw:
            return exif
        for tag_id, valor in raw.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag == "DateTimeOriginal":
                exif["fecha"] = str(valor)
            elif tag == "Model":
                exif["modelo_camara"] = str(valor)
            elif tag == "Make":
                exif["fabricante"] = str(valor)
            elif tag == "GPSInfo":
                lat, lon = _gps_coords(valor)
                if lat is not None:
                    exif["gps_lat"] = lat
                    exif["gps_lon"] = lon
    except Exception:
        pass
    return exif


def _gps_coords(gps_info: dict) -> tuple[Optional[float], Optional[float]]:
    try:
        def _to_deg(v):
            d, m, s = v
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
