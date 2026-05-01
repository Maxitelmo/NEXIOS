# bluetooth.py — Parser: Bluetooth dispositivos
# Fuente: SystemPreferencesDomain/com.apple.bluetooth.plist  (plist)

import logging
import plistlib
from pathlib import Path

_log = logging.getLogger(__name__)

ARTIFACT_ID = "bluetooth"
NOMBRE      = "Bluetooth dispositivos"


def parsear(ruta_plist: str) -> list[dict]:
    """
    Parsea com.apple.bluetooth.plist. Devuelve lista de dispositivos BT conocidos.

    Campos: nombre, mac_address, tipo, ultima_conexion, conectado.
    """
    ruta = Path(ruta_plist)
    if not ruta.is_file():
        _log.warning("com.apple.bluetooth.plist no encontrado: %s", ruta_plist)
        return []
    resultados = []
    try:
        with open(ruta, "rb") as f:
            data = plistlib.load(f)
        dispositivos = data.get("DeviceCache", {})
        for mac, info in dispositivos.items():
            resultados.append({
                "mac_address":     mac,
                "nombre":          info.get("Name") or info.get("BatteryPercentCase") or mac,
                "tipo":            info.get("MinorType") or "",
                "ultima_conexion": str(info.get("LastSeenTime") or ""),
                "conectado":       bool(info.get("Connected", False)),
                "fabricante":      info.get("Manufacturer") or "",
            })
    except Exception as e:
        _log.error("Error parseando com.apple.bluetooth.plist: %s", e)
    _log.info("Bluetooth: %d dispositivos", len(resultados))
    return resultados
