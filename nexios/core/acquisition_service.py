# acquisition_service.py
# Extracción selectiva de artifacts iOS por dominio vía pymobiledevice3 v9 (async).
#
# Estrategia de extracción según tipo:
#   - "backup_domain": Mobilebackup2Service.backup() con filter_callback selectivo.
#     El archivo queda en {backup_dir}/{udid}/{file_id[:2]}/{file_id} (iOS backup format).
#     file_id = SHA1("{domain}-{relative_path}").
#   - "afc": AfcService.pull() — acceso directo al filesystem de media.
#   - "service": servicios específicos (installation_proxy, lockdown).

import asyncio
import hashlib
import json
import logging
import os
import shutil
from pathlib import Path
from typing import Callable, Optional

from nexios.utils.file_system import safe_join_and_validate
from nexios.utils.hash_utils import calcular_hash
from nexios.utils.forensic_log_chain import append_evento_forense

_log = logging.getLogger(__name__)

try:
    from pymobiledevice3.services.afc import AfcService
    from pymobiledevice3.services.mobilebackup2 import Mobilebackup2Service, BackupFile
    from pymobiledevice3.services.installation_proxy import InstallationProxyService
    _PMD3_AVAILABLE = True
except ImportError:
    _PMD3_AVAILABLE = False


# ── Definición de los 21 artifacts ─────────────────────────────────────────────
ARTIFACTS: list[dict] = [
    {"id": "sms",               "nombre": "SMS / iMessage",         "dominio": "HomeDomain",                                              "ruta": "Library/SMS/sms.db",                                     "tipo": "backup_domain"},
    {"id": "contactos",         "nombre": "Contactos",              "dominio": "HomeDomain",                                              "ruta": "Library/AddressBook/AddressBook.sqlitedb",                "tipo": "backup_domain"},
    {"id": "llamadas",          "nombre": "Historial de llamadas",  "dominio": "HomeDomain",                                              "ruta": "Library/CallHistory/call_history.db",                    "tipo": "backup_domain"},
    {"id": "whatsapp_mensajes", "nombre": "WhatsApp mensajes",      "dominio": "AppDomainGroup-group.net.whatsapp.WhatsApp.shared",        "ruta": "ChatStorage.sqlite",                                     "tipo": "backup_domain"},
    {"id": "whatsapp_llamadas", "nombre": "WhatsApp llamadas",      "dominio": "AppDomainGroup-group.net.whatsapp.WhatsApp.shared",        "ruta": "CallHistory.sqlite",                                     "tipo": "backup_domain"},
    {"id": "fotos",             "nombre": "Fotos + EXIF",           "dominio": "afc",                                                     "ruta": "DCIM",                                                   "tipo": "afc"},
    {"id": "safari",            "nombre": "Safari historial",       "dominio": "HomeDomain",                                              "ruta": "Library/Safari/History.db",                              "tipo": "backup_domain"},
    {"id": "notas",             "nombre": "Notas",                  "dominio": "HomeDomain",                                              "ruta": "Library/Notes/NotesStore.sqlite",                        "tipo": "backup_domain"},
    {"id": "ubicaciones",       "nombre": "Ubicaciones Maps",       "dominio": "HomeDomain",                                              "ruta": "Library/Maps/GeoHistory.mapsdata",                       "tipo": "backup_domain"},
    {"id": "calendario",        "nombre": "Calendario",             "dominio": "HomeDomain",                                              "ruta": "Library/Calendar/Calendar.sqlitedb",                     "tipo": "backup_domain"},
    {"id": "recordatorios",     "nombre": "Recordatorios",          "dominio": "HomeDomain",                                              "ruta": "Library/Reminders/RemindersDB",                          "tipo": "backup_domain"},
    {"id": "telegram",          "nombre": "Telegram mensajes",      "dominio": "AppDomain-ph.telegra.Telegraph",                          "ruta": "tgdata.sqlite",                                          "tipo": "backup_domain"},
    {"id": "grabaciones",       "nombre": "Grabaciones de voz",     "dominio": "afc",                                                     "ruta": "Recordings",                                             "tipo": "afc"},
    {"id": "voicemail",         "nombre": "Voicemail",              "dominio": "afc",                                                     "ruta": "Voicemail",                                              "tipo": "afc"},
    {"id": "apps_instaladas",   "nombre": "Apps instaladas",        "dominio": "installation_proxy",                                      "ruta": "",                                                       "tipo": "service"},
    {"id": "wifi",              "nombre": "Redes WiFi conocidas",   "dominio": "SystemPreferencesDomain",                                 "ruta": "SystemConfiguration/com.apple.wifi.plist",               "tipo": "backup_domain"},
    {"id": "cuentas",           "nombre": "Cuentas configuradas",   "dominio": "HomeDomain",                                              "ruta": "Library/Accounts/accounts3.sqlite",                      "tipo": "backup_domain"},
    {"id": "fotos_eliminadas",  "nombre": "Fotos eliminadas",       "dominio": "afc",                                                     "ruta": "PhotoData/Trash",                                        "tipo": "afc"},
    {"id": "uso_apps",          "nombre": "Uso de apps",            "dominio": "HomeDomain",                                              "ruta": "Library/application usage/DataUsage.sqlite",             "tipo": "backup_domain"},
    {"id": "bluetooth",         "nombre": "Bluetooth dispositivos", "dominio": "SystemPreferencesDomain",                                 "ruta": "com.apple.bluetooth.plist",                              "tipo": "backup_domain"},
    {"id": "info_dispositivo",  "nombre": "Info del dispositivo",   "dominio": "lockdown",                                                "ruta": "",                                                       "tipo": "service"},
]

_ARTIFACT_MAP: dict[str, dict] = {a["id"]: a for a in ARTIFACTS}


def get_artifact_def(artifact_id: str) -> Optional[dict]:
    return _ARTIFACT_MAP.get(artifact_id)


# ── API pública (sync, para uso desde UI/threads) ──────────────────────────────

def extraer_artifact(
    lockdown,
    artifact_id: str,
    carpeta_artifacts: str,
    carpeta_relevamiento: str,
    progress_cb: Optional[Callable[[str, str], None]] = None,
) -> dict:
    """
    Extrae un artifact individual al disco.

    Returns:
        dict con: ok, artifact_id, nombre, ruta_local, sha256, mensaje.
    """
    resultado = {"ok": False, "artifact_id": artifact_id, "nombre": "", "ruta_local": "", "sha256": "", "mensaje": ""}
    defn = get_artifact_def(artifact_id)
    if not defn:
        resultado["mensaje"] = f"Artifact desconocido: {artifact_id}"
        return resultado
    resultado["nombre"] = defn["nombre"]
    if progress_cb:
        progress_cb(artifact_id, "extrayendo")
    try:
        ruta_local = asyncio.run(_extraer_async(lockdown, defn, carpeta_artifacts))
        if ruta_local:
            sha = calcular_hash(ruta_local) if os.path.isfile(ruta_local) else ""
            resultado.update({"ok": True, "ruta_local": ruta_local, "sha256": sha})
            append_evento_forense(
                carpeta_relevamiento,
                f"ARTIFACT EXTRAÍDO: {defn['nombre']} | ruta={ruta_local} | sha256={sha}"
            )
            if progress_cb:
                progress_cb(artifact_id, "ok")
        else:
            resultado["mensaje"] = "No encontrado en el dispositivo"
            append_evento_forense(carpeta_relevamiento, f"ARTIFACT NO ENCONTRADO: {defn['nombre']}")
            if progress_cb:
                progress_cb(artifact_id, "no_encontrado")
    except Exception as e:
        resultado["mensaje"] = str(e)
        _log.error("Error extrayendo %s: %s", artifact_id, e)
        append_evento_forense(carpeta_relevamiento, f"ERROR ARTIFACT: {defn['nombre']} | error={e}")
        if progress_cb:
            progress_cb(artifact_id, "error")
    return resultado


def extraer_todos(
    lockdown,
    artifact_ids: list[str],
    carpeta_artifacts: str,
    carpeta_relevamiento: str,
    progress_cb: Optional[Callable[[str, str], None]] = None,
) -> list[dict]:
    """Extrae múltiples artifacts en secuencia. Devuelve lista de resultados."""
    return [
        extraer_artifact(lockdown, aid, carpeta_artifacts, carpeta_relevamiento, progress_cb)
        for aid in artifact_ids
    ]


# ── Lógica async de extracción ─────────────────────────────────────────────────

async def _extraer_async(lockdown, defn: dict, carpeta_destino: str) -> Optional[str]:
    tipo = defn["tipo"]
    if tipo == "backup_domain":
        return await _extraer_via_backup(lockdown, defn, carpeta_destino)
    if tipo == "afc":
        return await _extraer_via_afc(lockdown, defn, carpeta_destino)
    if tipo == "service":
        return await _extraer_via_service(lockdown, defn, carpeta_destino)
    raise ValueError(f"Tipo de extracción desconocido: {tipo}")


async def _extraer_via_backup(lockdown, defn: dict, carpeta_destino: str) -> Optional[str]:
    """
    Extrae un archivo de un dominio de backup usando Mobilebackup2Service.
    Usa backup selectivo con filter_callback + identifica el archivo por su file_id
    (SHA1 de "{domain}-{relative_path}") dentro de la estructura de backup de iOS.
    """
    if not _PMD3_AVAILABLE:
        raise RuntimeError("pymobiledevice3 no disponible")

    dominio = defn["dominio"]
    ruta_rel = defn["ruta"]
    artifact_id = defn["id"]

    # Calcular file_id: SHA1("{domain}-{relative_path}")
    file_id = hashlib.sha1(f"{dominio}-{ruta_rel}".encode()).hexdigest()

    # Directorio temporal de backup
    backup_dir = Path(carpeta_destino) / f"_backup_tmp_{artifact_id}"
    backup_dir.mkdir(parents=True, exist_ok=True)

    def _filtro(bf: "BackupFile") -> bool:
        return bf.domain == dominio and bf.relative_path == ruta_rel

    try:
        async with Mobilebackup2Service(lockdown) as backup:
            await backup.backup(
                full=True,
                backup_directory=str(backup_dir),
                filter_callback=_filtro,
            )
    except Exception as e:
        _log.error("Error en backup selectivo de %s: %s", artifact_id, e)
        return None

    # Localizar el archivo extraído en la estructura de backup
    udid = await lockdown.get_value(key="UniqueDeviceID")
    ruta_backup = backup_dir / str(udid) / file_id[:2] / file_id
    if not ruta_backup.is_file():
        # Intentar sin subdirectorio (algunos backups omiten la estructura hash)
        for f in backup_dir.rglob(file_id):
            if f.is_file():
                ruta_backup = f
                break
        else:
            _log.warning("Archivo no encontrado en backup: %s / %s", dominio, ruta_rel)
            shutil.rmtree(str(backup_dir), ignore_errors=True)
            return None

    # Copiar al destino final con nombre legible
    nombre_destino = f"{artifact_id}_{Path(ruta_rel).name}"
    ruta_final = safe_join_and_validate(carpeta_destino, nombre_destino)
    shutil.copy2(str(ruta_backup), ruta_final)
    shutil.rmtree(str(backup_dir), ignore_errors=True)
    return ruta_final


async def _extraer_via_afc(lockdown, defn: dict, carpeta_destino: str) -> Optional[str]:
    """Extrae archivos/carpeta vía AFC (Apple File Conduit) usando afc.pull()."""
    if not _PMD3_AVAILABLE:
        raise RuntimeError("pymobiledevice3 no disponible")

    ruta_afc = defn["ruta"]
    subcarpeta_local = safe_join_and_validate(carpeta_destino, defn["id"])
    os.makedirs(subcarpeta_local, exist_ok=True)

    async with AfcService(lockdown) as afc:
        try:
            info = await afc.stat(ruta_afc)
        except Exception:
            return None
        if info.get("st_ifmt") == "S_IFDIR":
            await afc.pull(ruta_afc, subcarpeta_local, progress_bar=False)
        else:
            nombre = Path(ruta_afc).name
            dest = safe_join_and_validate(subcarpeta_local, nombre)
            contenido = await afc.get_file_contents(ruta_afc)
            with open(dest, "wb") as f:
                f.write(contenido)
    return subcarpeta_local


async def _extraer_via_service(lockdown, defn: dict, carpeta_destino: str) -> Optional[str]:
    """Extrae información vía servicios específicos."""
    if defn["id"] == "apps_instaladas":
        async with InstallationProxyService(lockdown) as proxy:
            apps = await proxy.get_apps()
        ruta_local = safe_join_and_validate(carpeta_destino, "apps_instaladas.json")
        with open(ruta_local, "w", encoding="utf-8") as f:
            json.dump(apps, f, indent=2, ensure_ascii=False, default=str)
        return ruta_local

    if defn["id"] == "info_dispositivo":
        from nexios.core.device_service import _obtener_info_async
        info = await _obtener_info_async(lockdown)
        ruta_local = safe_join_and_validate(carpeta_destino, "info_dispositivo.json")
        with open(ruta_local, "w", encoding="utf-8") as f:
            json.dump(info, f, indent=2, ensure_ascii=False)
        return ruta_local

    return None
