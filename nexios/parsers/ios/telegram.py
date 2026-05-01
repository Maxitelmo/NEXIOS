# telegram.py — Parser: Telegram mensajes
# Fuente: AppDomain-ph.telegra.Telegraph/tgdata.sqlite  (SQLite)

import logging
import sqlite3
from pathlib import Path

_log = logging.getLogger(__name__)

ARTIFACT_ID = "telegram"
NOMBRE      = "Telegram mensajes"


def parsear(ruta_db: str) -> list[dict]:
    """
    Parsea tgdata.sqlite de Telegram. Devuelve lista de mensajes.

    Campos: mid, fecha_raw, texto, cid (chat id), uid (user id), es_enviado.
    """
    ruta = Path(ruta_db)
    if not ruta.is_file():
        _log.warning("tgdata.sqlite no encontrado: %s", ruta_db)
        return []
    resultados = []
    try:
        con = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        # TODO: verificar esquema según versión de Telegram
        cur.execute("""
            SELECT
                mid,
                date        AS fecha_raw,
                message     AS texto,
                cid,
                uid,
                out         AS es_enviado,
                media_type
            FROM messages_v2
            ORDER BY date DESC
        """)
        for row in cur.fetchall():
            resultados.append(dict(row))
        con.close()
    except Exception as e:
        _log.error("Error parseando tgdata.sqlite: %s", e)
    _log.info("Telegram: %d mensajes", len(resultados))
    return resultados
