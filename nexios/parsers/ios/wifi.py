# wifi.py — Parser: Redes WiFi conocidas
# Fuente: SystemPreferencesDomain/SystemConfiguration/com.apple.wifi.plist  (plist)

import logging
import plistlib
from pathlib import Path

_log = logging.getLogger(__name__)

ARTIFACT_ID = "wifi"
NOMBRE      = "Redes WiFi conocidas"


def parsear(ruta_plist: str) -> list[dict]:
    """
    Parsea com.apple.wifi.plist. Devuelve lista de redes WiFi memorizadas.

    Campos: ssid, bssid, security_mode, auto_join, last_connected.
    """
    ruta = Path(ruta_plist)
    if not ruta.is_file():
        _log.warning("com.apple.wifi.plist no encontrado: %s", ruta_plist)
        return []
    resultados = []
    try:
        with open(ruta, "rb") as f:
            data = plistlib.load(f)
        redes = data.get("List of known networks", [])
        for red in redes:
            resultados.append({
                "ssid":           red.get("SSID_STR") or red.get("SSID", b"").decode("utf-8", errors="replace"),
                "bssid":          red.get("BSSID") or "",
                "security_mode":  red.get("SecurityMode") or "",
                "auto_join":      bool(red.get("auto_join", False)),
                "last_connected": str(red.get("lastConnected") or ""),
                "hidden":         bool(red.get("HIDDEN_NETWORK", False)),
            })
    except Exception as e:
        _log.error("Error parseando com.apple.wifi.plist: %s", e)
    _log.info("WiFi: %d redes conocidas", len(resultados))
    return resultados
