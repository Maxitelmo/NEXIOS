# nexios/parsers/ios/__init__.py
# Dispatcher: dado un artifact_id y ruta_local, llama al parser correspondiente
# y devuelve (datos: list[dict], columnas_pdf: list[str]).
# Las columnas_pdf definen qué campos mostrar en el informe.

import logging
import os
from typing import Optional

_log = logging.getLogger(__name__)

# (artifact_id) → (función_parser, [columnas_para_PDF])
# Las columnas deben existir como keys en los dicts devueltos por el parser.
_DISPATCH: dict[str, tuple] = {}


def _reg(artifact_id, fn, cols):
    _DISPATCH[artifact_id] = (fn, cols)


def _load_dispatch():
    from nexios.parsers.ios import (
        sms, contactos, llamadas, whatsapp, safari, notas,
        ubicaciones, calendario, recordatorios, telegram, grabaciones,
        voicemail, apps_instaladas, wifi, cuentas, fotos_eliminadas,
        uso_apps, bluetooth, fotos,
    )
    _reg("sms",               lambda r: sms.parsear(r),
         ["fecha_raw", "numero", "es_enviado", "texto"])
    _reg("contactos",         lambda r: contactos.parsear(r),
         ["nombre", "apellido", "organizacion", "telefonos"])
    _reg("llamadas",          lambda r: llamadas.parsear(r),
         ["fecha_raw", "numero", "tipo", "duracion"])
    _reg("whatsapp_mensajes", lambda r: whatsapp.parsear_mensajes(r),
         ["fecha_raw", "jid_chat", "es_enviado", "texto"])
    _reg("whatsapp_llamadas", lambda r: whatsapp.parsear_llamadas(r),
         ["fecha_raw", "jid", "tipo", "duracion"])
    _reg("safari",            lambda r: safari.parsear(r),
         ["fecha_raw", "titulo", "url"])
    _reg("notas",             lambda r: notas.parsear(r),
         ["titulo", "fecha_creacion", "snippet"])
    _reg("ubicaciones",       lambda r: ubicaciones.parsear(r),
         ["nombre", "latitud", "longitud", "fecha_raw"])
    _reg("calendario",        lambda r: calendario.parsear(r),
         ["titulo", "fecha_inicio", "fecha_fin", "calendario"])
    _reg("recordatorios",     lambda r: recordatorios.parsear(r),
         ["titulo", "fecha_vencimiento", "lista", "notas"])
    _reg("telegram",          lambda r: telegram.parsear(r),
         ["fecha_raw", "cid", "es_enviado", "texto"])
    _reg("grabaciones",       lambda r: grabaciones.parsear(r),
         ["nombre", "extension", "tamaño_bytes"])
    _reg("voicemail",         lambda r: voicemail.parsear(r),
         ["remitente", "fecha_raw", "duracion", "archivo_audio"])
    _reg("apps_instaladas",   lambda r: apps_instaladas.parsear(r),
         ["nombre", "bundle_id", "version", "tipo"])
    _reg("wifi",              lambda r: wifi.parsear(r),
         ["ssid", "security_mode", "last_connected", "bssid"])
    _reg("cuentas",           lambda r: cuentas.parsear(r),
         ["tipo", "username", "fecha_creacion", "activa"])
    _reg("fotos_eliminadas",  lambda r: fotos_eliminadas.parsear(r),
         ["nombre", "extension", "tamaño_bytes"])
    _reg("uso_apps",          lambda r: uso_apps.parsear(r),
         ["bundle_id", "wifi_in", "wifi_out", "ultimo_uso"])
    _reg("bluetooth",         lambda r: bluetooth.parsear(r),
         ["nombre", "mac_address", "tipo", "ultima_conexion"])
    _reg("fotos",             lambda r: fotos.parsear(r),
         ["nombre", "fecha_exif", "gps_lat", "gps_lon"])
    # info_dispositivo ya figura en la sección de dispositivo — no se parsea aquí


_loaded = False


def parsear_artifact(artifact_id: str, ruta_local: str) -> tuple[list[dict], list[str]]:
    """
    Parsea el artifact indicado y devuelve (datos, columnas_pdf).

    Args:
        artifact_id: ID del artifact (ej. "sms", "wifi").
        ruta_local:  Ruta local al archivo o carpeta extraída.

    Returns:
        Tupla (datos: list[dict], columnas_pdf: list[str]).
        Si no hay parser registrado o falla, devuelve ([], []).
    """
    global _loaded
    if not _loaded:
        _load_dispatch()
        _loaded = True

    if not ruta_local or not os.path.exists(ruta_local):
        return [], []

    entry = _DISPATCH.get(artifact_id)
    if not entry:
        return [], []

    fn, cols = entry
    try:
        datos = fn(ruta_local)
        return datos, cols
    except Exception as e:
        _log.error("Error parseando artifact %s: %s", artifact_id, e)
        return [], []
