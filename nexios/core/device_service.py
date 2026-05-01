# device_service.py
# Detección, pairing e información del dispositivo iOS vía pymobiledevice3 v9 (async).
#
# Estrategia de conexión:
#   iOS ≤ 16 : create_using_usbmux  → UsbmuxLockdownClient  (clásico, rápido)
#   iOS 17+  : get_rsds + RSD       → RemoteLockdownClient  (mDNS sobre interfaz USB,
#              no requiere admin en Windows)
#
# Para iOS 17+ el iPhone crea una interfaz de red USB (RNDIS/NCM) y anuncia
# el servicio _remoted._tcp.local. vía mDNS. get_rsds() lo descubre directamente.
# rsd.lockdown es un RemoteLockdownClient compatible con todos los servicios clásicos.

import asyncio
import logging
from typing import Optional

_log = logging.getLogger(__name__)

try:
    from pymobiledevice3.usbmux import list_devices, MuxDevice
    from pymobiledevice3.lockdown import create_using_usbmux, UsbmuxLockdownClient
    from pymobiledevice3.remote.tunnel_service import get_rsds
    _PMD3_AVAILABLE = True
except ImportError:
    _PMD3_AVAILABLE = False
    _log.warning("pymobiledevice3 no disponible — modo simulación activo")

_BONJOUR_TIMEOUT_LISTA  = 3.0   # segundos para descubrir RSD al listar dispositivos
_BONJOUR_TIMEOUT_CONNECT = 6.0  # segundos para descubrir RSD al conectar


def pmd3_disponible() -> bool:
    return _PMD3_AVAILABLE


# ── Wrappers sync (para uso desde UI/threads) ──────────────────────────────────

def listar_dispositivos() -> list[dict]:
    """
    Devuelve lista de dispositivos iOS conectados por USB.
    Combina usbmux (iOS ≤ 16) + RSD/mDNS (iOS 17+).
    Cada elemento: { "udid", "connection_type", "ios_version" }
    """
    if not _PMD3_AVAILABLE:
        return []
    try:
        return asyncio.run(_listar_dispositivos_async())
    except Exception as e:
        _log.error("Error listando dispositivos: %s", e)
        return []


def conectar(udid: Optional[str] = None):
    """
    Conecta al dispositivo (primero si udid es None).
    Intenta conexión clásica (usbmux) primero; si falla, intenta RSD (iOS 17+).
    Devuelve un LockdownClient compatible con todos los servicios.
    """
    if not _PMD3_AVAILABLE:
        _log.error("pymobiledevice3 no disponible")
        return None
    try:
        return asyncio.run(_conectar_async(udid))
    except Exception as e:
        _log.error("Error conectando al dispositivo: %s", e)
        return None


def obtener_info_dispositivo(lockdown) -> dict:
    """
    Extrae información técnica del dispositivo.
    Funciona con UsbmuxLockdownClient y RemoteLockdownClient.
    """
    try:
        return asyncio.run(_obtener_info_async(lockdown))
    except Exception as e:
        _log.error("Error obteniendo info del dispositivo: %s", e)
        return {}


def hacer_pairing(lockdown) -> bool:
    """
    Inicia el proceso de pairing.
    Para iOS 17+ el pairing ya ocurre en la fase de conexión RSD.
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
    resultado: list[dict] = []
    udids_vistos: set[str] = set()

    # ── Vía usbmux (iOS ≤ 16 y posiblemente iOS 17+) ──────────────────────────
    try:
        devices: list["MuxDevice"] = await list_devices()
        for d in devices:
            udid = d.serial
            if udid not in udids_vistos:
                resultado.append({"udid": udid, "connection_type": d.connection_type, "ios_version": ""})
                udids_vistos.add(udid)
    except Exception as e:
        _log.debug("usbmux list_devices falló: %s", e)

    # ── Vía RSD / mDNS (iOS 17+) ───────────────────────────────────────────────
    try:
        rsds = await get_rsds(bonjour_timeout=_BONJOUR_TIMEOUT_LISTA)
        for rsd in rsds:
            udid = rsd.udid
            ios  = rsd.product_version
            if udid not in udids_vistos:
                resultado.append({"udid": udid, "connection_type": "USB (RSD)", "ios_version": ios})
                udids_vistos.add(udid)
            else:
                # Actualizar la versión iOS si ya estaba en usbmux
                for entry in resultado:
                    if entry["udid"] == udid and not entry.get("ios_version"):
                        entry["ios_version"] = ios
                        entry["connection_type"] = "USB (RSD)"
            await rsd.close()
    except Exception as e:
        _log.debug("RSD/mDNS discovery falló: %s", e)

    return resultado


async def _conectar_async(udid: Optional[str]):
    """
    Conexión dual: usbmux primero, RSD como fallback para iOS 17+.
    Devuelve un LockdownClient (UsbmuxLockdownClient o RemoteLockdownClient).
    """
    # ── Intento 1: conexión clásica vía usbmux ─────────────────────────────────
    err_clasico = None
    try:
        lockdown = await create_using_usbmux(serial=udid)
        nombre = await lockdown.get_value(key="DeviceName")
        ios    = await lockdown.get_value(key="ProductVersion")
        udid_  = await lockdown.get_value(key="UniqueDeviceID")
        _log.info("Conectado (clásico): %s iOS %s (%s)", nombre, ios, udid_)
        return lockdown
    except Exception as e:
        err_clasico = e
        _log.info("Conexión clásica falló (%s) — intentando RSD (iOS 17+)", e)

    # ── Intento 2: RSD vía mDNS (iOS 17+) ─────────────────────────────────────
    try:
        rsds = await get_rsds(bonjour_timeout=_BONJOUR_TIMEOUT_CONNECT, udid=udid)
        if not rsds:
            raise RuntimeError(
                "Dispositivo no encontrado via RSD. "
                "Verificar: cable USB, iPhone desbloqueado, 'Confiar en esta computadora' aceptado, "
                "drivers Apple instalados (Apple Devices o iTunes)."
            )
        rsd = rsds[0]
        lockdown = rsd.lockdown
        if lockdown is None:
            await rsd.close()
            raise RuntimeError("RSD conectado pero lockdown no disponible en el dispositivo.")

        # Anclar rsd en lockdown para que no se libere mientras se use
        lockdown._nexios_rsd = rsd

        nombre = await lockdown.get_value(key="DeviceName")
        ios    = rsd.product_version
        udid_  = rsd.udid
        _log.info("Conectado (RSD/iOS 17+): %s iOS %s (%s)", nombre, ios, udid_)
        return lockdown

    except Exception as e_rsd:
        _log.error("RSD también falló: %s", e_rsd)
        raise RuntimeError(
            f"No se pudo conectar al dispositivo.\n"
            f"• Error conexión clásica: {err_clasico}\n"
            f"• Error RSD (iOS 17+): {e_rsd}\n\n"
            f"Verificar: cable USB, iPhone desbloqueado, 'Confiar en esta computadora' aceptado "
            f"y drivers Apple instalados."
        ) from e_rsd


async def _obtener_info_async(lockdown) -> dict:
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
