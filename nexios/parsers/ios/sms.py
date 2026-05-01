# sms.py — Parser: SMS / iMessage
# Fuente: HomeDomain/Library/SMS/sms.db  (SQLite)

import logging
import sqlite3
from pathlib import Path
from typing import Optional

_log = logging.getLogger(__name__)

ARTIFACT_ID = "sms"
NOMBRE      = "SMS / iMessage"
DOMINIO     = "HomeDomain"
RUTA_DB     = "Library/SMS/sms.db"


def parsear(ruta_db: str) -> list[dict]:
    """
    Parsea sms.db y devuelve lista de mensajes ordenados por fecha DESC.

    Campos por mensaje: rowid, fecha, texto, es_enviado, numero, servicio, is_read.
    """
    ruta = Path(ruta_db)
    if not ruta.is_file():
        _log.warning("sms.db no encontrado: %s", ruta_db)
        return []
    resultados = []
    try:
        con = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        # TODO: ajustar JOIN según versión de iOS (la tabla handle puede cambiar)
        cur.execute("""
            SELECT
                m.ROWID       AS rowid,
                m.date        AS fecha_raw,
                m.text        AS texto,
                m.is_from_me  AS es_enviado,
                m.service     AS servicio,
                m.is_read     AS is_read,
                h.id          AS numero
            FROM message m
            LEFT JOIN handle h ON m.handle_id = h.ROWID
            ORDER BY m.date DESC
        """)
        for row in cur.fetchall():
            resultados.append(dict(row))
        con.close()
    except Exception as e:
        _log.error("Error parseando sms.db: %s", e)
    _log.info("SMS/iMessage: %d mensajes", len(resultados))
    return resultados


def resumen(datos: list[dict]) -> dict:
    enviados  = sum(1 for r in datos if r.get("es_enviado"))
    recibidos = len(datos) - enviados
    return {"total": len(datos), "enviados": enviados, "recibidos": recibidos}
