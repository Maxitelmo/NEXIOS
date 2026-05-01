# voicemail.py — Parser: Voicemail
# Fuente: AFC /Voicemail/  (archivos .amr/.m4a + metadata en voicemail.db)

import logging
import os
import sqlite3
from pathlib import Path

_log = logging.getLogger(__name__)

ARTIFACT_ID = "voicemail"
NOMBRE      = "Voicemail"


def parsear(carpeta_voicemail: str) -> list[dict]:
    """
    Parsea la carpeta Voicemail descargada. Une metadata de voicemail.db con archivos de audio.

    Campos: rowid, remitente, fecha_raw, duracion, ruta_audio.
    """
    carpeta = Path(carpeta_voicemail)
    if not carpeta.is_dir():
        _log.warning("Carpeta Voicemail no encontrada: %s", carpeta_voicemail)
        return []
    resultados = []
    ruta_db = carpeta / "voicemail.db"
    if ruta_db.is_file():
        try:
            con = sqlite3.connect(f"file:{ruta_db}?mode=ro", uri=True)
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            cur.execute("""
                SELECT
                    ROWID,
                    sender     AS remitente,
                    date       AS fecha_raw,
                    duration   AS duracion,
                    ROWID || '.amr' AS archivo_audio
                FROM voicemail
                ORDER BY date DESC
            """)
            for row in cur.fetchall():
                d = dict(row)
                ruta_audio = carpeta / d.get("archivo_audio", "")
                d["ruta_audio"] = str(ruta_audio) if ruta_audio.is_file() else ""
                resultados.append(d)
            con.close()
        except Exception as e:
            _log.error("Error parseando voicemail.db: %s", e)
    else:
        # Fallback: listar archivos de audio sin metadata
        for f in sorted(carpeta.iterdir()):
            if f.is_file() and f.suffix.lower() in (".amr", ".m4a"):
                resultados.append({
                    "nombre": f.name,
                    "ruta_audio": str(f),
                    "tamaño_bytes": f.stat().st_size,
                })
    _log.info("Voicemail: %d mensajes", len(resultados))
    return resultados
