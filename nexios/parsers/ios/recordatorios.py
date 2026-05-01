# recordatorios.py — Parser: Recordatorios
# Fuente: HomeDomain/Library/Reminders/RemindersDB  (SQLite)

import logging
import sqlite3
from pathlib import Path

_log = logging.getLogger(__name__)

ARTIFACT_ID = "recordatorios"
NOMBRE      = "Recordatorios"


def parsear(ruta_db: str) -> list[dict]:
    """
    Parsea RemindersDB. Devuelve lista de recordatorios.

    Campos: rowid, titulo, fecha_vencimiento, completado, notas, lista.
    """
    ruta = Path(ruta_db)
    if not ruta.is_file():
        _log.warning("RemindersDB no encontrado: %s", ruta_db)
        return []
    resultados = []
    try:
        con = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        # TODO: verificar nombres de tabla en distintas versiones de iOS
        cur.execute("""
            SELECT
                r.ROWID,
                r.SUMMARY        AS titulo,
                r.DUEDATE        AS fecha_vencimiento,
                r.COMPLETEDDATE  AS fecha_completado,
                r.NOTES          AS notas,
                l.TITLE          AS lista
            FROM RMReminder r
            LEFT JOIN RMList l ON r.LIST_ID = l.ROWID
            ORDER BY r.DUEDATE DESC
        """)
        for row in cur.fetchall():
            resultados.append(dict(row))
        con.close()
    except Exception as e:
        _log.error("Error parseando RemindersDB: %s", e)
    _log.info("Recordatorios: %d registros", len(resultados))
    return resultados
