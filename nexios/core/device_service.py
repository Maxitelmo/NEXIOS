# device_service.py
# Detección, pairing e información del dispositivo iOS vía pymobiledevice3 v9 (async).
# Toda la API de pymobiledevice3 v9 es async — los wrappers sync usan asyncio.run().

import asyncio
import logging
from typing import Optional

_log = logging.getLogger(__name__)

try:
    from pymobiledevice3.usbmux import list_devices, MuxDevice
    from pymobiledevice3.lockdown import create_using_usbmux, UsbmuxLockdownClient
    _PMD3_AVAILABLE = True
except ImportError:
    _PMD3_AVAILABLE = False
    _log.warning("pymobiledevice3 no disponible — modo simulación activo")


def pmd3_disponible() -> bool:
    return _PMD3_AVAILABLE


# ── Wrappers sync (para uso desde UI/threads) ──────────────────────────────────

def listar_dispositivos() -> list[dict]:
    """
    Devuelve lista de dispositivos iOS conectados por USB.
    Cada elemento: { "udid": str }
    """
    if not _PMD3_AVAILABLE:
        return []
    try:
        return asyncio.run(_listar_dispositivos_async())
    except Exception as e:
        _log.error("Error listando dispositivos: %s", e)
        return []


def conectar(udid: Optional[str] = None) -> Optional["UsbmuxLockdownClient"]:
    """
    Conecta al dispositivo (primero si udid es None) y devuelve el LockdownClient.
    El pairing record se guarda automáticamente por pymobiledevice3.
    """
    if not _PMD3_AVAILABLE:
        _log.error("pymobiledevice3 no disponible")
        return None
    try:
        return asyncio.run(_conectar_async(udid))
    except Exception as e:
        _log.error("Error conectando al dispositivo: %s", e)
        return None


def obtener_info_dispositivo(lockdown: "UsbmuxLockdownClient") -> dict:
    """
    Extrae información técnica completa del dispositivo.

    Returns:
        Dict con: nombre, modelo, modelo_str, ios_version, build_version,
                  serial, imei, udid, nombre_hw, capacidad_gb, bateria_pct, color, cpu_arch.
    """
    try:
        return asyncio.run(_obtener_info_async(lockdown))
    except Exception as e:
        _log.error("Error obteniendo info del dispositivo: %s", e)
        return {}


def hacer_pairing(lockdown: "UsbmuxLockdownClient") -> bool:
    """
    Inicia el proceso de pairing. El iPhone mostrará 'Confiar en esta computadora'.
    El pairing record se persiste automáticamente.
    Returns True si exitoso.
    """
    if not _PMD3_AVAILABLE:
        return False
    try:
        asyncio.run(lockdown.pair())
        _log.info("Pairing exitoso")
        return True
    except Exception as e:
        _log.error("Error en pairing: %s", e)
        return False


# ── Implementaciones async ─────────────────────────────────────────────────────

async def _listar_dispositivos_async() -> list[dict]:
    devices: list[MuxDevice] = await list_devices()
    return [{"udid": d.serial, "connection_type": d.connection_type} for d in devices]


async def _conectar_async(udid: Optional[str]) -> "UsbmuxLockdownClient":
    lockdown = await create_using_usbmux(serial=udid)
    nombre  = await lockdown.get_value(key="DeviceName")
    ios     = await lockdown.get_value(key="ProductVersion")
    udid_   = await lockdown.get_value(key="UniqueDeviceID")
    _log.info("Dispositivo conectado: %s iOS %s (%s)", nombre, ios, udid_)
    return lockdown


async def _obtener_info_async(lockdown: "UsbmuxLockdownClient") -> dict:
    async def get(key: str, domain: str = None) -> str:
        try:
            val = await lockdown.get_value(domain=domain, key=key)
            return str(val) if val is not None else ""
        except Exception:
            return ""

    total_bytes_raw = await lockdown.get_value(key="TotalDiskCapacity")
    try:
        capacidad_gb = f"{int(total_bytes_raw) / 1_000_000_000:.1f} GB"
    except Exception:
        capacidad_gb = ""

    bateria_raw = await lockdown.get_value(domain="com.apple.mobile.battery", key="BatteryCurrentCapacity")
    bateria_pct = f"{bateria_raw}%" if bateria_raw is not None else ""

    return {
        "nombre":        await get("DeviceName"),
        "modelo":        await get("ProductType"),
        "modelo_str":    await get("MarketingName") or await get("ProductType"),
        "ios_version":   await get("ProductVersion"),
        "build_version": await get("BuildVersion"),
        "serial":        await get("SerialNumber"),
        "imei":          await get("InternationalMobileEquipmentIdentity"),
        "udid":          await get("UniqueDeviceID"),
        "nombre_hw":     await get("HardwareModel"),
        "capacidad_gb":  capacidad_gb,
        "bateria_pct":   bateria_pct,
        "color":         await get("DeviceColor"),
        "cpu_arch":      await get("CPUArchitecture"),
    }
