# calendario.py — Parser: Calendario
# Fuente: HomeDomain/Library/Calendar/Calendar.sqlitedb  (SQLite)

import logging
import sqlite3
from pathlib import Path

_log = logging.getLogger(__name__)

ARTIFACT_ID = "calendario"
NOMBRE      = "Calendario"


def parsear(ruta_db: str) -> list[dict]:
    """
    Parsea Calendar.sqlitedb. Devuelve lista de eventos.

    Campos: rowid, titulo, fecha_inicio, fecha_fin, notas, calendario, todo.
    """
    ruta = Path(ruta_db)
    if not ruta.is_file():
        _log.warning("Calendar.sqlitedb no encontrado: %s", ruta_db)
        return []
    resultados = []
    try:
        con = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("""
            SELECT
                ci.ROWID,
                ci.SUMMARY      AS titulo,
                ci.DTSTART      AS fecha_inicio,
                ci.DTEND        AS fecha_fin,
                ci.NOTES        AS notas,
                c.TITLE         AS calendario
            FROM CalendarItem ci
            LEFT JOIN Calendar c ON ci.CALENDAR_ID = c.ROWID
            ORDER BY ci.DTSTART DESC
        """)
        for row in cur.fetchall():
            resultados.append(dict(row))
        con.close()
    except Exception as e:
        _log.error("Error parseando Calendar.sqlitedb: %s", e)
    _log.info("Calendario: %d eventos", len(resultados))
    return resultados
