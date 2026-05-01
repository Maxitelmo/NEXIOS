# whatsapp.py — Parser: WhatsApp mensajes y llamadas
# Fuentes:
#   AppDomainGroup-group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite  (mensajes)
#   AppDomainGroup-group.net.whatsapp.WhatsApp.shared/CallHistory.sqlite  (llamadas)

import logging
import sqlite3
from pathlib import Path

_log = logging.getLogger(__name__)

ARTIFACT_ID_MENSAJES = "whatsapp_mensajes"
ARTIFACT_ID_LLAMADAS = "whatsapp_llamadas"
NOMBRE               = "WhatsApp"


def parsear_mensajes(ruta_db: str) -> list[dict]:
    """
    Parsea ChatStorage.sqlite. Devuelve lista de mensajes.

    Campos: rowid, z_pk, fecha_raw, texto, jid_remitente, tipo_media, es_enviado, grupo.
    """
    ruta = Path(ruta_db)
    if not ruta.is_file():
        _log.warning("ChatStorage.sqlite no encontrado: %s", ruta_db)
        return []
    resultados = []
    try:
        con = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        # TODO: unir con ZWACHATSESSION para nombre del chat
        cur.execute("""
            SELECT
                m.Z_PK,
                m.ZMESSAGEDATE AS fecha_raw,
                m.ZTEXT        AS texto,
                m.ZISFROMME    AS es_enviado,
                m.ZMEDIAITEM   AS tiene_media,
                s.ZCONTACTJID  AS jid_chat
            FROM ZWAMESSAGE m
            LEFT JOIN ZWACHATSESSION s ON m.ZCHATSESSION = s.Z_PK
            ORDER BY m.ZMESSAGEDATE DESC
        """)
        for row in cur.fetchall():
            resultados.append(dict(row))
        con.close()
    except Exception as e:
        _log.error("Error parseando ChatStorage.sqlite: %s", e)
    _log.info("WhatsApp mensajes: %d", len(resultados))
    return resultados


def parsear_llamadas(ruta_db: str) -> list[dict]:
    """
    Parsea CallHistory.sqlite. Devuelve lista de llamadas.

    Campos: rowid, fecha_raw, duracion, jid, tipo (voz/video), es_llamada_saliente.
    """
    ruta = Path(ruta_db)
    if not ruta.is_file():
        _log.warning("CallHistory.sqlite no encontrado: %s", ruta_db)
        return []
    resultados = []
    try:
        con = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute("""
            SELECT
                Z_PK,
                ZDATE          AS fecha_raw,
                ZDURATION      AS duracion,
                ZJID           AS jid,
                ZCALLTYPE      AS tipo,
                ZISFROMME      AS es_saliente
            FROM ZWACALLHISTORYITEM
            ORDER BY ZDATE DESC
        """)
        for row in cur.fetchall():
            resultados.append(dict(row))
        con.close()
    except Exception as e:
        _log.error("Error parseando CallHistory.sqlite: %s", e)
    _log.info("WhatsApp llamadas: %d", len(resultados))
    return resultados
