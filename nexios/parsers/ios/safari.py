# safari.py — Parser: Safari historial
# Fuente: HomeDomain/Library/Safari/History.db  (SQLite)

import logging
import sqlite3
from pathlib import Path

_log = logging.getLogger(__name__)

ARTIFACT_ID = "safari"
NOMBRE      = "Safari historial"


def parsear(ruta_db: str) -> list[dict]:
    """
    Parsea History.db de Safari. Devuelve lista de URLs visitadas.

    Campos: rowid, url, titulo, fecha_raw, visit_count.
    """
    ruta = Path(ruta_db)
    if not ruta.is_file():
        _log.warning("History.db no encontrado: %s", ruta_db)
        return []
    resultados = []
    try:
        con = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("""
            SELECT
                hi.id,
                hi.url,
                hi.title         AS titulo,
                hi.visit_count,
                hv.visit_time    AS fecha_raw
            FROM history_items hi
            LEFT JOIN history_visits hv ON hv.history_item = hi.id
            ORDER BY hv.visit_time DESC
        """)
        for row in cur.fetchall():
            resultados.append(dict(row))
        con.close()
    except Exception as e:
        _log.error("Error parseando Safari History.db: %s", e)
    _log.info("Safari: %d entradas", len(resultados))
    return resultados
