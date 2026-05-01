# apps_instaladas.py — Parser: Apps instaladas
# Fuente: installation_proxy service (JSON exportado por acquisition_service)

import json
import logging
from pathlib import Path

_log = logging.getLogger(__name__)

ARTIFACT_ID = "apps_instaladas"
NOMBRE      = "Apps instaladas"


def parsear(ruta_json: str) -> list[dict]:
    """
    Parsea apps_instaladas.json generado por InstallationProxyService.

    Campos por app: bundle_id, nombre, version, tipo (usuario/sistema), tamaño_bytes.
    """
    ruta = Path(ruta_json)
    if not ruta.is_file():
        _log.warning("apps_instaladas.json no encontrado: %s", ruta_json)
        return []
    resultados = []
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            data = json.load(f)
        for bundle_id, info in data.items():
            resultados.append({
                "bundle_id":     bundle_id,
                "nombre":        info.get("CFBundleDisplayName") or info.get("CFBundleName") or bundle_id,
                "version":       info.get("CFBundleShortVersionString") or "",
                "tipo":          info.get("ApplicationType") or "",
                "tamaño_bytes":  info.get("StaticDiskUsage") or 0,
                "min_ios":       info.get("MinimumOSVersion") or "",
            })
        resultados.sort(key=lambda x: x["nombre"].lower())
    except Exception as e:
        _log.error("Error parseando apps_instaladas.json: %s", e)
    _log.info("Apps instaladas: %d", len(resultados))
    return resultados
