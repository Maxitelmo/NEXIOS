# uso_apps.py — Parser: Uso de apps por fecha/hora
# Fuente: HomeDomain/Library/application usage/DataUsage.sqlite  (SQLite)

import logging
import sqlite3
from pathlib import Path

_log = logging.getLogger(__name__)

ARTIFACT_ID = "uso_apps"
NOMBRE      = "Uso de apps"


def parsear(ruta_db: str) -> list[dict]:
    """
    Parsea DataUsage.sqlite. Devuelve uso de datos (WiFi/celular) por app.

    Campos: bundle_id, wifi_in, wifi_out, celular_in, celular_out, timestamp_raw.
    """
    ruta = Path(ruta_db)
    if not ruta.is_file():
        _log.warning("DataUsage.sqlite no encontrado: %s", ruta_db)
        return []
    resultados = []
    try:
        con = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("""
            SELECT
                p.ZBUNDLENAME AS bundle_id,
                SUM(l.ZWIFIIN)      AS wifi_in,
                SUM(l.ZWIFIOUT)     AS wifi_out,
                SUM(l.ZWWANIN)      AS celular_in,
                SUM(l.ZWWANOUT)     AS celular_out,
                MAX(l.ZTIMESTAMP)   AS ultimo_uso
            FROM ZPROCESS p
            LEFT JOIN ZLIVEUSAGE l ON l.ZPROCESS = p.Z_PK
            GROUP BY p.ZBUNDLENAME
            ORDER BY wifi_in + wifi_out + celular_in + celular_out DESC
        """)
        for row in cur.fetchall():
            resultados.append(dict(row))
        con.close()
    except Exception as e:
        _log.error("Error parseando DataUsage.sqlite: %s", e)
    _log.info("Uso de apps: %d registros", len(resultados))
    return resultados
