# contactos.py — Parser: Contactos
# Fuente: HomeDomain/Library/AddressBook/AddressBook.sqlitedb  (SQLite)

import logging
import sqlite3
from pathlib import Path

_log = logging.getLogger(__name__)

ARTIFACT_ID = "contactos"
NOMBRE      = "Contactos"


def parsear(ruta_db: str) -> list[dict]:
    """
    Parsea AddressBook.sqlitedb. Devuelve lista de contactos con nombre, apellido y teléfonos.
    """
    ruta = Path(ruta_db)
    if not ruta.is_file():
        _log.warning("AddressBook.sqlitedb no encontrado: %s", ruta_db)
        return []
    resultados = []
    try:
        con = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        # TODO: unir con ABMultiValue para teléfonos/emails
        cur.execute("""
            SELECT
                r.ROWID,
                r.First   AS nombre,
                r.Last    AS apellido,
                r.Organization AS organizacion,
                r.CreationDate AS fecha_creacion
            FROM ABPerson r
            ORDER BY r.Last, r.First
        """)
        personas = {row["ROWID"]: dict(row) for row in cur.fetchall()}
        cur.execute("""
            SELECT record_id, value, label
            FROM ABMultiValue
            WHERE property = 3   -- teléfonos
        """)
        for row in cur.fetchall():
            rid = row["record_id"]
            if rid in personas:
                personas[rid].setdefault("telefonos", []).append(row["value"])
        resultados = list(personas.values())
        con.close()
    except Exception as e:
        _log.error("Error parseando AddressBook: %s", e)
    _log.info("Contactos: %d registros", len(resultados))
    return resultados
