# screenshot_service.py
# Captura de pantalla del iPhone vía ScreenshotService (pymobiledevice3).
# iOS 15-: directo. iOS 16+: requiere Developer Mode activo.
# Toda activación de Developer Mode queda registrada en la cadena de custodia.

import io
import logging
import os
from datetime import datetime
from typing import Optional

from nexios.utils.file_system import safe_join_and_validate
from nexios.utils.hash_utils import calcular_hash
from nexios.utils.forensic_log_chain import append_evento_forense

_log = logging.getLogger(__name__)

try:
    from pymobiledevice3.services.screenshotr import ScreenshotService
    _PMD3_AVAILABLE = True
except ImportError:
    _PMD3_AVAILABLE = False

try:
    from PIL import Image
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False


def _parse_ios_version(version_str: str) -> tuple[int, int]:
    """Devuelve (major, minor) de una cadena '16.4.1'."""
    try:
        partes = str(version_str).split(".")
        return int(partes[0]), int(partes[1]) if len(partes) > 1 else 0
    except Exception:
        return 0, 0


def verificar_developer_mode(lockdown) -> dict:
    """
    Consulta si Developer Mode está activo en el dispositivo.

    Returns:
        dict con: activo (bool), ios_major (int), requiere_dev_mode (bool), mensaje (str).
    """
    ios_version = ""
    try:
        ios_version = lockdown.get_value("ProductVersion") or ""
    except Exception:
        pass
    ios_major, _ = _parse_ios_version(ios_version)
    requiere = ios_major >= 16

    activo = False
    if requiere:
        try:
            resultado = lockdown.get_value("DeveloperModeStatus", domain="com.apple.amfi")
            activo = bool(resultado)
        except Exception:
            # Si el dominio no responde, asumimos no activo
            activo = False
    else:
        # iOS 15 y anteriores: no hay restricción
        activo = True

    return {
        "activo": activo,
        "ios_version": ios_version,
        "ios_major": ios_major,
        "requiere_dev_mode": requiere,
        "mensaje": (
            "Developer Mode activo — captura disponible." if activo
            else f"iOS {ios_version}: Developer Mode inactivo. El operador debe activarlo desde Ajustes → Privacidad y seguridad → Developer Mode."
        ),
    }


def capturar_pantalla(
    lockdown,
    carpeta_capturas: str,
    carpeta_relevamiento: str,
    operador: str = "",
    descripcion: str = "",
    numero: int = 1,
) -> dict:
    """
    Captura la pantalla del dispositivo y guarda el PNG en carpeta_capturas.

    Args:
        lockdown: LockdownClient conectado.
        carpeta_capturas: Carpeta donde se guarda la captura.
        carpeta_relevamiento: Carpeta raíz del relevamiento (para log).
        operador: Nombre del operador (para el log).
        descripcion: Descripción opcional de la captura.
        numero: Número correlativo de la captura en el expediente.

    Returns:
        dict con: ok, ruta_local, sha256, timestamp, mensaje.
    """
    resultado = {"ok": False, "ruta_local": "", "sha256": "", "timestamp": "", "mensaje": ""}

    if not _PMD3_AVAILABLE:
        resultado["mensaje"] = "pymobiledevice3 no disponible"
        return resultado
    if not _PIL_AVAILABLE:
        resultado["mensaje"] = "Pillow no disponible"
        return resultado

    # Verificar Developer Mode antes de intentar la captura
    estado_dm = verificar_developer_mode(lockdown)
    if not estado_dm["activo"]:
        resultado["mensaje"] = estado_dm["mensaje"]
        append_evento_forense(
            carpeta_relevamiento,
            f"CAPTURA BLOQUEADA: Developer Mode inactivo en iOS {estado_dm['ios_version']} | operador={operador}"
        )
        return resultado

    try:
        os.makedirs(carpeta_capturas, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = f"captura_{numero:03d}_{timestamp}.png"
        ruta_local = safe_join_and_validate(carpeta_capturas, nombre_archivo)

        with ScreenshotService(lockdown) as ss:
            png_data: bytes = ss.take_screenshot()

        img = Image.open(io.BytesIO(png_data))
        img.save(ruta_local, "PNG")

        sha = calcular_hash(ruta_local)
        resultado.update({"ok": True, "ruta_local": ruta_local, "sha256": sha, "timestamp": timestamp})

        append_evento_forense(
            carpeta_relevamiento,
            f"CAPTURA DE PANTALLA: {nombre_archivo} | sha256={sha} | operador={operador}"
            + (f" | desc={descripcion}" if descripcion else "")
        )
        _log.info("Captura guardada: %s", ruta_local)

    except Exception as e:
        resultado["mensaje"] = str(e)
        _log.error("Error capturando pantalla: %s", e)
        append_evento_forense(
            carpeta_relevamiento,
            f"ERROR CAPTURA: {e} | operador={operador}"
        )
    return resultado


def registrar_activacion_developer_mode(
    carpeta_relevamiento: str, operador: str, ios_version: str
) -> None:
    """
    Registra en la cadena de custodia que el operador activó Developer Mode.
    Llamar ANTES de la activación real, para que quede el timestamp de la decisión.
    """
    append_evento_forense(
        carpeta_relevamiento,
        f"DEVELOPER MODE ACTIVADO POR OPERADOR: iOS {ios_version} | operador={operador} "
        f"| NOTA: activación implica reinicio del dispositivo y modifica su estado"
    )
