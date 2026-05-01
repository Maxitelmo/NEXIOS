# forensic_log_chain.py
# Sistema de hash encadenado (SHA-256) para registro_forense.log.
# Alineado con buenas prácticas forenses (NIST Mobile Forensics 2014):
# no alteración, reproducibilidad, verificabilidad. Cada evento se encadena
# criptográficamente al anterior; HASH_FINAL_LOG ancla el log en manifest y PDF.
# Portado de CAPTA sin modificaciones funcionales.

import hashlib
import logging
import os
import re
import threading
from datetime import datetime

from nexios.utils.file_system import safe_join_and_validate

LOG_FILENAME       = "registro_forense.log"
INITIAL_HASH       = "0" * 64
_HASH_LINE_PREFIX  = "HASH: "
_HASH_FINAL_PREFIX = "HASH_FINAL_LOG: "
_EVENT_PREFIX_RE   = re.compile(r"^\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\] \| ")

# Estado por carpeta: { path_abs: { "hash_prev": str, "lock": threading.Lock } }
_chain_state: dict = {}
_state_lock = threading.Lock()


def _norm_path(carpeta: str) -> str:
    if not carpeta:
        return ""
    return os.path.abspath(os.path.normpath(carpeta))


def _get_or_create_carpeta_state(carpeta: str) -> dict:
    key = _norm_path(carpeta)
    with _state_lock:
        if key not in _chain_state:
            _chain_state[key] = {"hash_prev": INITIAL_HASH, "lock": threading.Lock()}
        return _chain_state[key]


def _log_path(carpeta_relevamiento: str) -> str:
    return safe_join_and_validate(carpeta_relevamiento, LOG_FILENAME)


def _read_last_chain_hash(ruta_log: str) -> str:
    if not os.path.isfile(ruta_log):
        return INITIAL_HASH
    last_hash = INITIAL_HASH
    try:
        with open(ruta_log, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.rstrip("\n\r")
                if line.startswith(_HASH_LINE_PREFIX):
                    val = line[len(_HASH_LINE_PREFIX):].strip()
                    if len(val) == 64 and all(c in "0123456789abcdef" for c in val.lower()):
                        last_hash = val.lower()
                elif line.startswith(_HASH_FINAL_PREFIX):
                    val = line[len(_HASH_FINAL_PREFIX):].strip()
                    if len(val) == 64 and all(c in "0123456789abcdef" for c in val.lower()):
                        last_hash = val.lower()
    except Exception:
        return INITIAL_HASH
    return last_hash


def init_cadena(carpeta_relevamiento: str) -> None:
    """
    Inicializa la cadena para la carpeta de relevamiento.
    Si registro_forense.log existe y contiene líneas HASH:, hash_prev se toma del último valor.
    Debe llamarse al iniciar sesión.
    """
    if not carpeta_relevamiento or not os.path.isdir(carpeta_relevamiento):
        return
    try:
        ruta = _log_path(carpeta_relevamiento)
    except ValueError:
        return
    state = _get_or_create_carpeta_state(carpeta_relevamiento)
    with state["lock"]:
        state["hash_prev"] = _read_last_chain_hash(ruta)


def append_evento_forense(carpeta_relevamiento: str, evento: str) -> None:
    """
    Registra un evento en registro_forense.log con hash encadenado.
    Formato: data = hash_prev + "[timestamp_iso] | " + evento;
    hash_actual = SHA256(data). Thread-safe por carpeta.
    """
    if not carpeta_relevamiento:
        return
    evento = (evento or "").strip()
    if not evento:
        return
    try:
        ruta = _log_path(carpeta_relevamiento)
    except ValueError:
        return
    state = _get_or_create_carpeta_state(carpeta_relevamiento)
    with state["lock"]:
        hash_prev = state["hash_prev"]
        timestamp_iso = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        lineas = evento.split("\n")
        primera = f"[{timestamp_iso}] | {lineas[0]}"
        bloque_escrito = primera + ("\n" + "\n".join(lineas[1:]) if len(lineas) > 1 else "")
        data = hash_prev + "[" + timestamp_iso + "] | " + evento
        hash_actual = hashlib.sha256(data.encode("utf-8")).hexdigest()
        try:
            with open(ruta, "a", encoding="utf-8") as f:
                f.write(bloque_escrito + "\n")
                f.write(_HASH_LINE_PREFIX + hash_actual + "\n")
                f.flush()
                if hasattr(os, "fsync"):
                    try:
                        os.fsync(f.fileno())
                    except (OSError, AttributeError):
                        pass
        except Exception:
            raise
        state["hash_prev"] = hash_actual


def obtener_y_registrar_hash_final(carpeta_relevamiento: str) -> str:
    """
    Escribe HASH_FINAL_LOG: hash_prev y devuelve ese hash.
    Llamar al cerrar el relevamiento, antes de generate_manifest_hashes.
    """
    if not carpeta_relevamiento:
        return ""
    try:
        ruta = _log_path(carpeta_relevamiento)
    except ValueError:
        return ""
    state = _get_or_create_carpeta_state(carpeta_relevamiento)
    with state["lock"]:
        hash_final = state["hash_prev"]
        try:
            with open(ruta, "a", encoding="utf-8") as f:
                f.write(_HASH_FINAL_PREFIX + hash_final + "\n")
                f.flush()
                if hasattr(os, "fsync"):
                    try:
                        os.fsync(f.fileno())
                    except (OSError, AttributeError):
                        pass
        except Exception:
            pass
        return hash_final


def verificar_cadena_registro_forense(ruta_log: str, logger=None) -> dict:
    """
    Verifica la integridad de la cadena de hashes en registro_forense.log.
    Recalcula SHA256(hash_prev + evento) y compara con el hash almacenado.

    Returns dict con: ok, hash_final, cantidad_eventos, evento_alterado, sin_hash_final, mensaje.
    """
    log = logger or logging.getLogger(__name__)
    resultado = {
        "ok": False,
        "hash_final": "",
        "cantidad_eventos": 0,
        "evento_alterado": None,
        "sin_hash_final": False,
        "mensaje": "",
    }
    if not ruta_log or not os.path.isfile(ruta_log):
        resultado["mensaje"] = "Archivo de log no encontrado."
        return resultado
    try:
        with open(ruta_log, "r", encoding="utf-8", errors="replace") as f:
            contenido = f.read()
    except Exception as e:
        resultado["mensaje"] = str(e)
        return resultado
    lineas = contenido.splitlines()
    eventos: list[tuple[str, str]] = []
    i = 0
    while i < len(lineas):
        lin = lineas[i]
        if _EVENT_PREFIX_RE.match(lin):
            m = re.match(r"^\[([^\]]+)\] \| (.*)", lin)
            if m:
                ts = m.group(1)
                cuerpo_lista = [m.group(2)]
                i += 1
                while i < len(lineas) and not lineas[i].startswith(_HASH_LINE_PREFIX) and not lineas[i].startswith(_HASH_FINAL_PREFIX):
                    cuerpo_lista.append(lineas[i])
                    i += 1
                cuerpo_evento = "\n".join(cuerpo_lista)
                if i < len(lineas):
                    hash_lin = lineas[i].strip()
                    if hash_lin.startswith(_HASH_LINE_PREFIX):
                        eventos.append((f"[{ts}] | {cuerpo_evento}", hash_lin[len(_HASH_LINE_PREFIX):].strip()))
                    elif hash_lin.startswith(_HASH_FINAL_PREFIX):
                        eventos.append((f"[{ts}] | {cuerpo_evento}", hash_lin[len(_HASH_FINAL_PREFIX):].strip()))
                    i += 1
                    continue
        i += 1
    if not eventos:
        resultado["mensaje"] = "No se encontraron eventos con formato de cadena."
        resultado["sin_hash_final"] = True
        return resultado
    hash_prev = INITIAL_HASH
    for idx, (cuerpo_completo, hash_almacenado) in enumerate(eventos):
        data = hash_prev + cuerpo_completo
        hash_esperado = hashlib.sha256(data.encode("utf-8")).hexdigest()
        hash_almacenado = (hash_almacenado or "").lower().strip()
        if len(hash_almacenado) != 64:
            resultado["evento_alterado"] = idx + 1
            resultado["mensaje"] = f"Evento {idx + 1}: valor de hash inválido."
            return resultado
        if hash_esperado != hash_almacenado:
            resultado["evento_alterado"] = idx + 1
            resultado["mensaje"] = f"Evento {idx + 1}: hash no coincide (alteración detectada)."
            return resultado
        hash_prev = hash_esperado
    ultima = ""
    for j in range(len(lineas) - 1, -1, -1):
        s = lineas[j].strip()
        if s:
            ultima = s
            break
    if not ultima.startswith(_HASH_FINAL_PREFIX):
        resultado["sin_hash_final"] = True
        resultado["mensaje"] = "El log no termina con HASH_FINAL_LOG (ancla final ausente o truncado)."
        resultado["cantidad_eventos"] = len(eventos)
        return resultado
    valor_ancla = ultima[len(_HASH_FINAL_PREFIX):].strip().lower()
    if len(valor_ancla) != 64 or not all(c in "0123456789abcdef" for c in valor_ancla):
        resultado["mensaje"] = "HASH_FINAL_LOG contiene un valor inválido (posible manipulación)."
        resultado["cantidad_eventos"] = len(eventos)
        resultado["sin_hash_final"] = True
        return resultado
    if valor_ancla != hash_prev.lower():
        resultado["mensaje"] = "HASH_FINAL_LOG no coincide con la cadena recalculada (posible manipulación del ancla final)."
        resultado["cantidad_eventos"] = len(eventos)
        resultado["hash_final"] = hash_prev
        resultado["sin_hash_final"] = True
        return resultado
    resultado["ok"] = True
    resultado["hash_final"] = hash_prev
    resultado["cantidad_eventos"] = len(eventos)
    resultado["mensaje"] = f"Cadena verificada correctamente ({len(eventos)} eventos)."
    return resultado


class ForensicLogHandler(logging.Handler):
    """
    Handler de logging que encadena cada mensaje en registro_forense.log.
    Requiere que el LogRecord tenga el atributo 'carpeta_relevamiento'.
    """

    def __init__(self, carpeta_relevamiento_getter=None):
        super().__init__()
        self._carpeta_getter = carpeta_relevamiento_getter

    def emit(self, record: logging.LogRecord) -> None:
        try:
            carpeta = getattr(record, "carpeta_relevamiento", None)
            if self._carpeta_getter and callable(self._carpeta_getter):
                carpeta = self._carpeta_getter() or carpeta
            if not carpeta:
                return
            msg = self.format(record)
            if msg:
                append_evento_forense(carpeta, msg)
        except Exception:
            self.handleError(record)
