# notas.py — Parser: Notas
# Fuente: HomeDomain/Library/Notes/NotesStore.sqlite  (SQLite)

import logging
import sqlite3
from pathlib import Path

_log = logging.getLogger(__name__)

ARTIFACT_ID = "notas"
NOMBRE      = "Notas"


def parsear(ruta_db: str) -> list[dict]:
    """
    Parsea NotesStore.sqlite. Devuelve lista de notas.

    Campos: rowid, titulo, snippet, fecha_creacion, fecha_modificacion, cuenta.
    """
    ruta = Path(ruta_db)
    if not ruta.is_file():
        _log.warning("NotesStore.sqlite no encontrado: %s", ruta_db)
        return []
    resultados = []
    try:
        con = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("""
            SELECT
                n.Z_PK,
                n.ZTITLE        AS titulo,
                n.ZSNIPPET      AS snippet,
                n.ZCREATIONDATE AS fecha_creacion,
                n.ZMODIFICATIONDATE AS fecha_modificacion
            FROM ZICNOTEDATA nd
            JOIN ZICCLOUDSYNCINGOBJECT n ON n.Z_PK = nd.ZNOTE
            ORDER BY n.ZMODIFICATIONDATE DESC
        """)
        for row in cur.fetchall():
            resultados.append(dict(row))
        con.close()
    except Exception as e:
        _log.error("Error parseando NotesStore.sqlite: %s", e)
    _log.info("Notas: %d registros", len(resultados))
    return resultados
