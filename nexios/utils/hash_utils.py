# hash_utils.py
# Utilidades de hashing SHA-256 para trazabilidad forense.
# Portado de CAPTA sin modificaciones funcionales.

import hashlib
import logging
import os

_log = logging.getLogger(__name__)


def calcular_hash(filepath: str) -> str:
    """
    Calcula SHA-256 de un archivo en bloques de 64 KB.

    Returns:
        Hash en hexadecimal, o "Error" si falla.
    """
    try:
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            while True:
                data = f.read(65536)
                if not data:
                    break
                sha256.update(data)
        resultado = sha256.hexdigest()
        _log.info("Hash calculado: %s → %s...", os.path.basename(filepath), resultado[:16])
        return resultado
    except Exception as e:
        _log.error("Error calculando hash de %s: %s", filepath, e)
        return "Error"
