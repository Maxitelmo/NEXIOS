# device_service.py
# Detección, pairing e información del dispositivo iOS vía pymobiledevice3.

import logging
from typing import Optional

_log = logging.getLogger(__name__)

# ── pymobiledevice3 imports ────────────────────────────────────────────────────
try:
    from pymobiledevice3.usbmux import create_mux
    from pymobiledevice3.lockdown import create_using_usbmux, LockdownClient
    _PMD3_AVAILABLE = True
except ImportError:
    _PMD3_AVAILABLE = False
    _log.warning("pymobiledevice3 no disponible — modo simulación activo")


def pmd3_disponible() -> bool:
    return _PMD3_AVAILABLE


def listar_dispositivos() -> list[dict]:
    """
    Devuelve lista de dispositivos iOS conectados por USB.
    Cada elemento: { "udid": str, "nombre": str }
    """
    if not _PMD3_AVAILABLE:
        return []
    try:
        with create_mux() as mux:
            devices = mux.devices
        return [{"udid": d.serial, "nombre": getattr(d, "name", d.serial)} for d in devices]
    except Exception as e:
        _log.error("Error listando dispositivos: %s", e)
        return []


def conectar(udid: Optional[str] = None) -> Optional["LockdownClient"]:
    """
    Conecta al dispositivo (primero si udid es None) y devuelve el LockdownClient.
    El cliente queda disponible para obtener servicios. Cierra la conexión al salir del with.
    El pairing record se guarda automáticamente por pymobiledevice3.
    """
    if not _PMD3_AVAILABLE:
        _log.error("pymobiledevice3 no disponible")
        return None
    try:
        lockdown = create_using_usbmux(serial=udid)
        _log.info(
            "Dispositivo conectado: %s (%s) iOS %s",
            lockdown.get_value("DeviceName"),
            lockdown.get_value("UniqueDeviceID"),
            lockdown.get_value("ProductVersion"),
        )
        return lockdown
    except Exception as e:
        _log.error("Error conectando al dispositivo: %s", e)
        return None


def obtener_info_dispositivo(lockdown: "LockdownClient") -> dict:
    """
    Extrae información técnica completa del dispositivo.

    Returns:
        Dict con: nombre, modelo, ios_version, serial, imei, capacidad_gb,
                  bateria_pct, udid, nombre_hw, build_version.
    """
    def _get(key: str, default: str = "") -> str:
        try:
            val = lockdown.get_value(key)
            return str(val) if val is not None else default
        except Exception:
            return default

    def _get_domain(domain: str, key: str, default: str = "") -> str:
        try:
            val = lockdown.get_value(key, domain=domain)
            return str(val) if val is not None else default
        except Exception:
            return default

    # Capacidad total en GB
    total_bytes = lockdown.get_value("TotalDiskCapacity") or 0
    try:
        capacidad_gb = f"{int(total_bytes) / 1_000_000_000:.1f} GB"
    except Exception:
        capacidad_gb = ""

    # Nivel de batería
    bateria_raw = _get_domain("com.apple.mobile.battery", "BatteryCurrentCapacity")
    bateria_pct = f"{bateria_raw}%" if bateria_raw else ""

    return {
        "nombre":        _get("DeviceName"),
        "modelo":        _get("ProductType"),
        "modelo_str":    _get("MarketingName") or _get("ProductType"),
        "ios_version":   _get("ProductVersion"),
        "build_version": _get("BuildVersion"),
        "serial":        _get("SerialNumber"),
        "imei":          _get("InternationalMobileEquipmentIdentity"),
        "udid":          _get("UniqueDeviceID"),
        "nombre_hw":     _get("HardwareModel"),
        "capacidad_gb":  capacidad_gb,
        "bateria_pct":   bateria_pct,
        "color":         _get("DeviceColor"),
        "cpu_arch":      _get("CPUArchitecture"),
    }


def hacer_pairing(lockdown: "LockdownClient") -> bool:
    """
    Inicia el proceso de pairing. El iPhone mostrará 'Confiar en esta computadora'.
    El pairing record se persiste automáticamente por pymobiledevice3.

    Returns True si el pairing fue exitoso.
    """
    if not _PMD3_AVAILABLE:
        return False
    try:
        lockdown.pair()
        _log.info("Pairing exitoso con %s", lockdown.get_value("UniqueDeviceID"))
        return True
    except Exception as e:
        _log.error("Error en pairing: %s", e)
        return False
