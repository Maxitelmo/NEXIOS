# acquisition_service.py
# Extracción selectiva de artifacts iOS por dominio vía pymobiledevice3.
# Soporta extracción individual o por lotes con callback de progreso.

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
    from pymobiledevice3.services.mobile_backup2 import MobileBackup2Service
    _PMD3_AVAILABLE = True
except ImportError:
    _PMD3_AVAILABLE = False


# ── Definición de los 21 artifacts ─────────────────────────────────────────────
# Cada artifact: id, nombre_display, dominio, ruta_relativa_en_dominio, tipo_extraccion
# tipo_extraccion: "backup_domain" | "afc"
ARTIFACTS: list[dict] = [
    {
        "id": "sms",
        "nombre": "SMS / iMessage",
        "dominio": "HomeDomain",
        "ruta": "Library/SMS/sms.db",
        "tipo": "backup_domain",
        "parser": "nexios.parsers.ios.sms",
    },
    {
        "id": "contactos",
        "nombre": "Contactos",
        "dominio": "HomeDomain",
        "ruta": "Library/AddressBook/AddressBook.sqlitedb",
        "tipo": "backup_domain",
        "parser": "nexios.parsers.ios.contactos",
    },
    {
        "id": "llamadas",
        "nombre": "Historial de llamadas",
        "dominio": "HomeDomain",
        "ruta": "Library/CallHistory/call_history.db",
        "tipo": "backup_domain",
        "parser": "nexios.parsers.ios.llamadas",
    },
    {
        "id": "whatsapp_mensajes",
        "nombre": "WhatsApp mensajes",
        "dominio": "AppDomainGroup-group.net.whatsapp.WhatsApp.shared",
        "ruta": "ChatStorage.sqlite",
        "tipo": "backup_domain",
        "parser": "nexios.parsers.ios.whatsapp",
    },
    {
        "id": "whatsapp_llamadas",
        "nombre": "WhatsApp llamadas",
        "dominio": "AppDomainGroup-group.net.whatsapp.WhatsApp.shared",
        "ruta": "CallHistory.sqlite",
        "tipo": "backup_domain",
        "parser": "nexios.parsers.ios.whatsapp",
    },
    {
        "id": "fotos",
        "nombre": "Fotos + EXIF",
        "dominio": "afc",
        "ruta": "DCIM",
        "tipo": "afc",
        "parser": "nexios.parsers.ios.fotos",
    },
    {
        "id": "safari",
        "nombre": "Safari historial",
        "dominio": "HomeDomain",
        "ruta": "Library/Safari/History.db",
        "tipo": "backup_domain",
        "parser": "nexios.parsers.ios.safari",
    },
    {
        "id": "notas",
        "nombre": "Notas",
        "dominio": "HomeDomain",
        "ruta": "Library/Notes/NotesStore.sqlite",
        "tipo": "backup_domain",
        "parser": "nexios.parsers.ios.notas",
    },
    {
        "id": "ubicaciones",
        "nombre": "Ubicaciones Maps",
        "dominio": "HomeDomain",
        "ruta": "Library/Maps/GeoHistory.mapsdata",
        "tipo": "backup_domain",
        "parser": "nexios.parsers.ios.ubicaciones",
    },
    {
        "id": "calendario",
        "nombre": "Calendario",
        "dominio": "HomeDomain",
        "ruta": "Library/Calendar/Calendar.sqlitedb",
        "tipo": "backup_domain",
        "parser": "nexios.parsers.ios.calendario",
    },
    {
        "id": "recordatorios",
        "nombre": "Recordatorios",
        "dominio": "HomeDomain",
        "ruta": "Library/Reminders/RemindersDB",
        "tipo": "backup_domain",
        "parser": "nexios.parsers.ios.recordatorios",
    },
    {
        "id": "telegram",
        "nombre": "Telegram mensajes",
        "dominio": "AppDomain-ph.telegra.Telegraph",
        "ruta": "tgdata.sqlite",
        "tipo": "backup_domain",
        "parser": "nexios.parsers.ios.telegram",
    },
    {
        "id": "grabaciones",
        "nombre": "Grabaciones de voz",
        "dominio": "afc",
        "ruta": "Recordings",
        "tipo": "afc",
        "parser": "nexios.parsers.ios.grabaciones",
    },
    {
        "id": "voicemail",
        "nombre": "Voicemail",
        "dominio": "afc",
        "ruta": "Voicemail",
        "tipo": "afc",
        "parser": "nexios.parsers.ios.voicemail",
    },
    {
        "id": "apps_instaladas",
        "nombre": "Apps instaladas",
        "dominio": "installation_proxy",
        "ruta": "",
        "tipo": "service",
        "parser": "nexios.parsers.ios.apps_instaladas",
    },
    {
        "id": "wifi",
        "nombre": "Redes WiFi conocidas",
        "dominio": "SystemPreferencesDomain",
        "ruta": "SystemConfiguration/com.apple.wifi.plist",
        "tipo": "backup_domain",
        "parser": "nexios.parsers.ios.wifi",
    },
    {
        "id": "cuentas",
        "nombre": "Cuentas configuradas",
        "dominio": "HomeDomain",
        "ruta": "Library/Accounts/accounts3.sqlite",
        "tipo": "backup_domain",
        "parser": "nexios.parsers.ios.cuentas",
    },
    {
        "id": "fotos_eliminadas",
        "nombre": "Fotos eliminadas",
        "dominio": "afc",
        "ruta": "PhotoData/Trash",
        "tipo": "afc",
        "parser": "nexios.parsers.ios.fotos_eliminadas",
    },
    {
        "id": "uso_apps",
        "nombre": "Uso de apps",
        "dominio": "HomeDomain",
        "ruta": "Library/application usage/DataUsage.sqlite",
        "tipo": "backup_domain",
        "parser": "nexios.parsers.ios.uso_apps",
    },
    {
        "id": "bluetooth",
        "nombre": "Bluetooth dispositivos",
        "dominio": "SystemPreferencesDomain",
        "ruta": "com.apple.bluetooth.plist",
        "tipo": "backup_domain",
        "parser": "nexios.parsers.ios.bluetooth",
    },
    {
        "id": "info_dispositivo",
        "nombre": "Info del dispositivo",
        "dominio": "lockdown",
        "ruta": "",
        "tipo": "service",
        "parser": "nexios.parsers.ios.apps_instaladas",  # usa device_service
    },
]

_ARTIFACT_MAP: dict[str, dict] = {a["id"]: a for a in ARTIFACTS}


def get_artifact_def(artifact_id: str) -> Optional[dict]:
    return _ARTIFACT_MAP.get(artifact_id)


def extraer_artifact(
    lockdown,
    artifact_id: str,
    carpeta_artifacts: str,
    carpeta_relevamiento: str,
    progress_cb: Optional[Callable[[str, str], None]] = None,
) -> dict:
    """
    Extrae un artifact individual al disco.

    Args:
        lockdown: LockdownClient conectado.
        artifact_id: ID del artifact (ver ARTIFACTS).
        carpeta_artifacts: Carpeta destino para guardar el archivo extraído.
        carpeta_relevamiento: Carpeta raíz del relevamiento (para log forense).
        progress_cb: Callback opcional (artifact_id, estado) para actualizar UI.

    Returns:
        dict con: ok, artifact_id, nombre, ruta_local, sha256, mensaje.
    """
    resultado = {
        "ok": False,
        "artifact_id": artifact_id,
        "nombre": "",
        "ruta_local": "",
        "sha256": "",
        "mensaje": "",
    }
    defn = get_artifact_def(artifact_id)
    if not defn:
        resultado["mensaje"] = f"Artifact desconocido: {artifact_id}"
        return resultado
    resultado["nombre"] = defn["nombre"]
    if progress_cb:
        progress_cb(artifact_id, "extrayendo")
    try:
        ruta_local = _extraer_segun_tipo(lockdown, defn, carpeta_artifacts)
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
            resultado["mensaje"] = "No se encontró el archivo en el dispositivo"
            append_evento_forense(
                carpeta_relevamiento,
                f"ARTIFACT NO ENCONTRADO: {defn['nombre']}"
            )
            if progress_cb:
                progress_cb(artifact_id, "no_encontrado")
    except Exception as e:
        resultado["mensaje"] = str(e)
        _log.error("Error extrayendo %s: %s", artifact_id, e)
        append_evento_forense(
            carpeta_relevamiento,
            f"ERROR ARTIFACT: {defn['nombre']} | error={e}"
        )
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
    resultados = []
    for aid in artifact_ids:
        r = extraer_artifact(lockdown, aid, carpeta_artifacts, carpeta_relevamiento, progress_cb)
        resultados.append(r)
    return resultados


# ── Lógica interna de extracción según tipo ────────────────────────────────────

def _extraer_segun_tipo(lockdown, defn: dict, carpeta_destino: str) -> Optional[str]:
    tipo = defn["tipo"]
    if tipo == "backup_domain":
        return _extraer_via_backup(lockdown, defn, carpeta_destino)
    if tipo == "afc":
        return _extraer_via_afc(lockdown, defn, carpeta_destino)
    if tipo == "service":
        return _extraer_via_service(lockdown, defn, carpeta_destino)
    raise ValueError(f"Tipo de extracción desconocido: {tipo}")


def _extraer_via_backup(lockdown, defn: dict, carpeta_destino: str) -> Optional[str]:
    """Extrae un archivo de un dominio de backup usando MobileBackup2Service."""
    if not _PMD3_AVAILABLE:
        raise RuntimeError("pymobiledevice3 no disponible")
    dominio = defn["dominio"]
    ruta_rel = defn["ruta"]
    nombre_archivo = Path(ruta_rel).name
    ruta_local = safe_join_and_validate(carpeta_destino, defn["id"] + "_" + nombre_archivo)
    with MobileBackup2Service(lockdown) as backup:
        # Solicitar solo el archivo específico del dominio
        backup.backup_file(domain=dominio, relative_path=ruta_rel, dest=ruta_local)
    return ruta_local if os.path.isfile(ruta_local) else None


def _extraer_via_afc(lockdown, defn: dict, carpeta_destino: str) -> Optional[str]:
    """Extrae archivos/carpeta vía AFC (Apple File Conduit)."""
    if not _PMD3_AVAILABLE:
        raise RuntimeError("pymobiledevice3 no disponible")
    ruta_afc = defn["ruta"]
    subcarpeta_local = safe_join_and_validate(carpeta_destino, defn["id"])
    os.makedirs(subcarpeta_local, exist_ok=True)
    with AfcService(lockdown) as afc:
        try:
            info = afc.stat(ruta_afc)
        except Exception:
            return None
        if info.get("st_ifmt") == "S_IFDIR":
            _afc_pull_dir(afc, ruta_afc, subcarpeta_local)
        else:
            dest = safe_join_and_validate(subcarpeta_local, Path(ruta_afc).name)
            with afc.open(ruta_afc, "rb") as src, open(dest, "wb") as dst:
                shutil.copyfileobj(src, dst)
    return subcarpeta_local


def _afc_pull_dir(afc, ruta_remota: str, ruta_local: str) -> None:
    """Descarga recursivamente un directorio vía AFC."""
    try:
        entries = afc.listdir(ruta_remota)
    except Exception:
        return
    for entry in entries:
        if entry in (".", ".."):
            continue
        remoto = f"{ruta_remota}/{entry}"
        local  = os.path.join(ruta_local, entry)
        try:
            info = afc.stat(remoto)
        except Exception:
            continue
        if info.get("st_ifmt") == "S_IFDIR":
            os.makedirs(local, exist_ok=True)
            _afc_pull_dir(afc, remoto, local)
        else:
            with afc.open(remoto, "rb") as src, open(local, "wb") as dst:
                shutil.copyfileobj(src, dst)


def _extraer_via_service(lockdown, defn: dict, carpeta_destino: str) -> Optional[str]:
    """Extrae información vía servicios específicos (installation_proxy, lockdown)."""
    import json
    if defn["id"] == "apps_instaladas":
        try:
            from pymobiledevice3.services.installation_proxy import InstallationProxyService
            with InstallationProxyService(lockdown) as proxy:
                apps = proxy.get_apps()
            ruta_local = safe_join_and_validate(carpeta_destino, "apps_instaladas.json")
            with open(ruta_local, "w", encoding="utf-8") as f:
                json.dump(apps, f, indent=2, ensure_ascii=False, default=str)
            return ruta_local
        except Exception as e:
            raise RuntimeError(f"Error extrayendo apps instaladas: {e}") from e
    if defn["id"] == "info_dispositivo":
        from nexios.core.device_service import obtener_info_dispositivo
        info = obtener_info_dispositivo(lockdown)
        ruta_local = safe_join_and_validate(carpeta_destino, "info_dispositivo.json")
        with open(ruta_local, "w", encoding="utf-8") as f:
            json.dump(info, f, indent=2, ensure_ascii=False)
        return ruta_local
    return None
