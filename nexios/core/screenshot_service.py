# screenshot_service.py
# Captura de pantalla del iPhone vía ScreenshotService (pymobiledevice3 v9).
# iOS 15-: directo. iOS 16+: requiere Developer Mode activo.
# Toda activación de Developer Mode queda registrada en la cadena de custodia.
#
# NOTA: En v9 no existe un método para consultar el estado de Developer Mode
# sin activarlo. La detección se hace por versión de iOS + intento de captura:
# si falla con error específico, se informa al operador.

import asyncio
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
    from pymobiledevice3.services.screenshot import ScreenshotService
    _PMD3_AVAILABLE = True
except ImportError:
    _PMD3_AVAILABLE = False

try:
    from PIL import Image
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False


def _parse_ios_version(version_str: str) -> tuple[int, int]:
    try:
        partes = str(version_str).split(".")
        return int(partes[0]), int(partes[1]) if len(partes) > 1 else 0
    except Exception:
        return 0, 0


def verificar_developer_mode(lockdown) -> dict:
    """
    Determina si la captura de pantalla estará disponible según la versión de iOS.
    En v9 no hay un getter de estado de Developer Mode sin activarlo; se informa
    al operador según la versión y se confirma al intentar la captura real.

    Returns:
        dict con: ios_version, ios_major, requiere_dev_mode, mensaje.
    """
    try:
        ios_version = asyncio.run(_get_ios_version(lockdown))
    except Exception:
        ios_version = ""
    ios_major, _ = _parse_ios_version(ios_version)
    requiere = ios_major >= 16
    return {
        "ios_version":     ios_version,
        "ios_major":       ios_major,
        "requiere_dev_mode": requiere,
        "mensaje": (
            f"iOS {ios_version}: captura disponible sin restricciones."
            if not requiere else
            f"iOS {ios_version}: requiere Developer Mode activo "
            f"(Ajustes → Privacidad y seguridad → Developer Mode). "
            f"Se confirmará al intentar la primera captura."
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
    Si falla por Developer Mode inactivo, lo indica claramente en el mensaje.

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
    try:
        os.makedirs(carpeta_capturas, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = f"captura_{numero:03d}_{timestamp}.png"
        ruta_local = safe_join_and_validate(carpeta_capturas, nombre_archivo)
        png_data = asyncio.run(_take_screenshot_async(lockdown))
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
        msg = str(e)
        # Detectar error de Developer Mode por mensaje de la excepción
        if "developer" in msg.lower() or "DeveloperModeError" in type(e).__name__:
            msg = (
                "Captura bloqueada: Developer Mode no activo. "
                "Activarlo desde Ajustes → Privacidad y seguridad → Developer Mode "
                "y reiniciar el dispositivo."
            )
        resultado["mensaje"] = msg
        _log.error("Error capturando pantalla: %s", e)
        append_evento_forense(
            carpeta_relevamiento,
            f"ERROR CAPTURA: {msg} | operador={operador}"
        )
    return resultado


def registrar_activacion_developer_mode(
    carpeta_relevamiento: str, operador: str, ios_version: str
) -> None:
    """
    Registra en la cadena de custodia que el operador activó Developer Mode.
    Llamar ANTES de la activación para que quede el timestamp de la decisión.
    """
    append_evento_forense(
        carpeta_relevamiento,
        f"DEVELOPER MODE ACTIVADO POR OPERADOR: iOS {ios_version} | operador={operador} "
        f"| NOTA: activación implica reinicio del dispositivo y modifica su estado"
    )


def activar_developer_mode(lockdown) -> bool:
    """
    Activa Developer Mode vía AmfiService (iOS 16+).
    Nota: requiere reinicio del dispositivo — el proceso es asistido por pymobiledevice3.
    Returns True si se inició el proceso exitosamente.
    """
    if not _PMD3_AVAILABLE:
        return False
    try:
        asyncio.run(_activar_developer_mode_async(lockdown))
        return True
    except Exception as e:
        _log.error("Error activando Developer Mode: %s", e)
        return False


# ── Implementaciones async ─────────────────────────────────────────────────────

async def _get_ios_version(lockdown) -> str:
    return str(await lockdown.get_value(key="ProductVersion") or "")


async def _take_screenshot_async(lockdown) -> bytes:
    # ScreenshotService(lockdown) llama internamente a start_lockdown_developer_service
    async with ScreenshotService(lockdown) as ss:
        return await ss.take_screenshot()


async def _activar_developer_mode_async(lockdown) -> None:
    from pymobiledevice3.services.amfi import AmfiService
    # AmfiService no es LockdownService — no es context manager, toma lockdown directamente
    amfi = AmfiService(lockdown)
    await amfi.enable_developer_mode()
