# llamadas.py — Parser: Historial de llamadas
# Fuente: HomeDomain/Library/CallHistory/call_history.db  (SQLite)

import logging
import sqlite3
from pathlib import Path

_log = logging.getLogger(__name__)

ARTIFACT_ID = "llamadas"
NOMBRE      = "Historial de llamadas"


def parsear(ruta_db: str) -> list[dict]:
    """
    Parsea call_history.db. Devuelve lista de llamadas ordenadas por fecha DESC.

    Campos: rowid, fecha_raw, duracion, numero, tipo (entrante/saliente/perdida), servicio.
    """
    ruta = Path(ruta_db)
    if not ruta.is_file():
        _log.warning("call_history.db no encontrado: %s", ruta_db)
        return []
    resultados = []
    try:
        con = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("""
            SELECT
                ROWID,
                ZDATE        AS fecha_raw,
                ZDURATION    AS duracion,
                ZADDRESS     AS numero,
                ZANSWERED    AS contestada,
                ZORIGINATED  AS originada,
                ZSERVICE_PROVIDER AS servicio
            FROM ZCALLRECORD
            ORDER BY ZDATE DESC
        """)
        for row in cur.fetchall():
            d = dict(row)
            d["tipo"] = (
                "saliente"  if d.get("originada") else
                "entrante"  if d.get("contestada") else
                "perdida"
            )
            resultados.append(d)
        con.close()
    except Exception as e:
        _log.error("Error parseando call_history.db: %s", e)
    _log.info("Llamadas: %d registros", len(resultados))
    return resultados
