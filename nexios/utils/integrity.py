# integrity.py
# Manifiesto de integridad y bloqueo de carpeta de evidencia.
# Portado de CAPTA sin modificaciones funcionales.

import hashlib
import json
import logging
import os
import stat
from datetime import datetime

from nexios.utils.file_system import safe_join_and_validate

MANIFEST_FILENAME = "manifest_hashes.json"
_log = logging.getLogger(__name__)


def _file_sha256(filepath: str, blocksize: int = 65536) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while True:
            block = f.read(blocksize)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def generate_manifest_hashes(
    carpeta_relevamiento: str,
    version_nexios: str,
    session_uuid: str = None,
    logger=None,
    hash_final_log: str = None,
) -> str:
    """
    Genera manifest_hashes.json con lista de archivos y SHA-256.
    No incluye el propio manifest en la lista.

    Returns:
        Ruta completa del manifest generado.
    """
    log = logger or _log
    carpeta = os.path.abspath(os.path.normpath(carpeta_relevamiento))
    if not os.path.isdir(carpeta):
        raise NotADirectoryError(f"No existe la carpeta de relevamiento: {carpeta}")
    if not session_uuid:
        try:
            ruta_sesion = safe_join_and_validate(carpeta, "sesion_guardada.json")
            if os.path.isfile(ruta_sesion):
                with open(ruta_sesion, "r", encoding="utf-8") as f:
                    datos = json.load(f)
                session_uuid = datos.get("session_uuid") or datos.get("uuid") or ""
        except Exception:
            session_uuid = ""
    archivos = []
    for root, _dirs, files in os.walk(carpeta):
        for name in files:
            ruta_abs = os.path.join(root, name)
            try:
                ruta_rel = os.path.relpath(ruta_abs, carpeta)
                if ruta_rel.replace("\\", "/") == MANIFEST_FILENAME:
                    continue
                sha = _file_sha256(ruta_abs)
                entry: dict = {"ruta_relativa": ruta_rel.replace("\\", "/"), "sha256": sha}
                try:
                    stat_info = os.stat(ruta_abs)
                    entry["size"] = stat_info.st_size
                    entry["mtime"] = datetime.fromtimestamp(stat_info.st_mtime).strftime("%Y-%m-%dT%H:%M:%S")
                except OSError:
                    pass
                archivos.append(entry)
            except Exception as e:
                log.warning("No se pudo hashear %s: %s", ruta_abs, e)
    fecha = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    manifest: dict = {
        "fecha_generacion": fecha,
        "version_nexios": version_nexios,
        "uuid_sesion": session_uuid or "",
        "archivos": archivos,
    }
    if hash_final_log is not None:
        manifest["hash_final_log"] = hash_final_log
    ruta_manifest = safe_join_and_validate(carpeta, MANIFEST_FILENAME)
    with open(ruta_manifest, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    _log.info("Manifiesto de integridad generado: %s (%d archivos)", ruta_manifest, len(archivos))
    return ruta_manifest


def set_evidence_folder_readonly(carpeta_relevamiento: str, logger=None) -> None:
    """Establece solo lectura en todos los archivos y carpetas del relevamiento."""
    log = logger or _log
    carpeta = os.path.abspath(os.path.normpath(carpeta_relevamiento))
    if not os.path.isdir(carpeta):
        raise NotADirectoryError(f"No existe la carpeta: {carpeta}")
    count = 0
    for root, dirs, files in os.walk(carpeta, topdown=False):
        for name in files:
            path = os.path.join(root, name)
            try:
                os.chmod(path, stat.S_IREAD)
                count += 1
            except Exception as e:
                log.warning("No se pudo establecer solo lectura en %s: %s", path, e)
        for name in dirs:
            path = os.path.join(root, name)
            try:
                os.chmod(path, stat.S_IREAD)
                count += 1
            except Exception as e:
                log.warning("No se pudo establecer solo lectura en carpeta %s: %s", path, e)
    try:
        os.chmod(carpeta, stat.S_IREAD)
        count += 1
    except Exception as e:
        log.warning("No se pudo establecer solo lectura en raíz %s: %s", carpeta, e)
    _log.info("Carpeta de evidencia en solo lectura: %s (%d elementos)", carpeta, count)


def verify_manifest_integrity(carpeta_relevamiento: str, logger=None) -> dict:
    """
    Verifica integridad del relevamiento comparando hashes actuales con el manifest.

    Returns dict con: ok, sin_manifiesto, modificados, eliminados, añadidos.
    """
    log = logger or _log
    carpeta = os.path.abspath(os.path.normpath(carpeta_relevamiento))
    resultado = {
        "ok": False,
        "sin_manifiesto": False,
        "modificados": [],
        "eliminados": [],
        "añadidos": [],
    }
    if not os.path.isdir(carpeta):
        return resultado
    ruta_manifest = safe_join_and_validate(carpeta, MANIFEST_FILENAME)
    if not os.path.isfile(ruta_manifest):
        resultado["sin_manifiesto"] = True
        return resultado
    try:
        with open(ruta_manifest, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except Exception as e:
        log.warning("No se pudo leer el manifiesto: %s", e)
        return resultado
    esperado: dict[str, str] = {}
    for item in manifest.get("archivos", []):
        r = (item.get("ruta_relativa") or "").replace("\\", "/")
        if r:
            esperado[r] = item.get("sha256") or ""
    actuales: set[str] = set()
    for root, _dirs, files in os.walk(carpeta):
        for name in files:
            ruta_abs = os.path.join(root, name)
            ruta_rel = os.path.relpath(ruta_abs, carpeta).replace("\\", "/")
            actuales.add(ruta_rel)
            if ruta_rel == MANIFEST_FILENAME:
                continue
            if ruta_rel in esperado:
                try:
                    sha_actual = _file_sha256(ruta_abs)
                    if sha_actual != esperado[ruta_rel]:
                        resultado["modificados"].append(ruta_rel)
                except Exception as e:
                    log.warning("No se pudo hashear %s: %s", ruta_abs, e)
                    resultado["modificados"].append(ruta_rel)
            else:
                resultado["añadidos"].append(ruta_rel)
    for r in esperado:
        if r not in actuales:
            resultado["eliminados"].append(r)
    resultado["ok"] = (
        not resultado["modificados"]
        and not resultado["eliminados"]
        and not resultado["añadidos"]
    )
    return resultado
