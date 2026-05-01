# cuentas.py — Parser: Cuentas configuradas
# Fuente: HomeDomain/Library/Accounts/accounts3.sqlite  (SQLite)

import logging
import sqlite3
from pathlib import Path

_log = logging.getLogger(__name__)

ARTIFACT_ID = "cuentas"
NOMBRE      = "Cuentas configuradas"


def parsear(ruta_db: str) -> list[dict]:
    """
    Parsea accounts3.sqlite. Devuelve lista de cuentas (iCloud, Google, Exchange, etc.).

    Campos: rowid, tipo, username, fecha_creacion, activa.
    """
    ruta = Path(ruta_db)
    if not ruta.is_file():
        _log.warning("accounts3.sqlite no encontrado: %s", ruta_db)
        return []
    resultados = []
    try:
        con = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("""
            SELECT
                a.ROWID,
                at.TYPE         AS tipo,
                a.USERNAME      AS username,
                a.CREATION_DATE AS fecha_creacion,
                a.ENABLED       AS activa
            FROM ZACCOUNT a
            LEFT JOIN ZACCOUNTTYPE at ON a.ACCOUNTTYPE = at.ROWID
            ORDER BY a.CREATION_DATE DESC
        """)
        for row in cur.fetchall():
            resultados.append(dict(row))
        con.close()
    except Exception as e:
        _log.error("Error parseando accounts3.sqlite: %s", e)
    _log.info("Cuentas: %d registros", len(resultados))
    return resultados
