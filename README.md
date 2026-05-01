# NEXIOS

**Núcleo de Extracción Forense en dispositivos iOS**

Herramienta de forensia digital móvil orientada al trabajo de **campo** (*live mobile forensics*) sobre dispositivos Apple iPhone. Desarrollada en el ámbito del **Ministerio Público Fiscal de la Nación Argentina**.

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![pymobiledevice3](https://img.shields.io/badge/pymobiledevice3-9.12.0-green.svg)](https://github.com/doronz88/pymobiledevice3)

---

## ¿Qué es NEXIOS?

NEXIOS permite realizar una **adquisición forense selectiva** de un iPhone desbloqueado conectado por USB en 2 a 5 minutos, sin jailbreak, desde una PC con Windows.

Es el proyecto hermano de [CAPTA](https://github.com/Maxitelmo/CAPTA) (herramienta de campo para Android), con quien comparte filosofía forense y estándares de integridad, pero no código base.

### Escenario de uso

- iPhone desbloqueado (el perito conoce el PIN y/o dispone de biométricos).
- PC conectada al iPhone por USB.
- **No se requiere jailbreak** en ninguna etapa.
- Pensado para operar en campo: rápido, portable, sin instalación.

---

## Características

- **Detección automática** del dispositivo y gestión del pairing record (se guarda para conexiones futuras).
- **Información técnica completa**: modelo, iOS, serial, IMEI, capacidad, batería.
- **21 artifacts forenses** extraíbles de forma selectiva.
- **Captura de pantalla** vía USB con detección automática de Developer Mode (iOS 16+).
- **Fotografías manuales** del operador con trazabilidad EXIF completa.
- **Hashing SHA-256** de cada archivo adquirido.
- **Log forense encadenado** (NIST Mobile Forensics 2014): cada evento se encadena criptográficamente al anterior.
- **Manifiesto de integridad** (`manifest_hashes.json`) y bloqueo en solo lectura al cierre.
- **Informe PDF** con cadena de custodia, hashes, capturas, fotos y firma del operador.
- **Portable**: corre desde pendrive, sin instalación en la PC del operativo.

---

## Los 21 artifacts

| # | Artifact | Tipo |
|---|----------|------|
| 1 | SMS / iMessage | SQLite |
| 2 | Contactos | SQLite |
| 3 | Historial de llamadas | SQLite |
| 4 | WhatsApp mensajes | SQLite |
| 5 | WhatsApp llamadas | SQLite |
| 6 | Fotos + EXIF | AFC (archivos) |
| 7 | Safari historial | SQLite |
| 8 | Notas | SQLite |
| 9 | Ubicaciones Maps | Plist |
| 10 | Calendario | SQLite |
| 11 | Recordatorios | SQLite |
| 12 | Telegram mensajes | SQLite |
| 13 | Grabaciones de voz | AFC (archivos) |
| 14 | Voicemail | AFC + SQLite |
| 15 | Info del dispositivo | Servicio lockdown |
| 16 | Apps instaladas | installation_proxy |
| 17 | Redes WiFi conocidas | Plist |
| 18 | Cuentas configuradas | SQLite |
| 19 | Fotos eliminadas | AFC (archivos) |
| 20 | Uso de apps | SQLite |
| 21 | Bluetooth dispositivos | Plist |

---

## Requisitos

- **Sistema operativo**: Windows 10/11 (64-bit)
- **Python**: 3.11 o superior (solo para desarrollo; el portable no requiere Python instalado)
- **Dependencias**: ver `requirements.txt`
- **Drivers USB**: [iTunes for Windows](https://support.apple.com/downloads/itunes) o los drivers de Apple instalados (para que Windows reconozca el iPhone)

### Dependencias principales

```
pymobiledevice3==9.12.0   # Adquisición iOS (GPLv3)
reportlab>=4.0.0,<4.4.0   # Generación de PDF
jinja2>=3.0.0             # Templates
customtkinter>=5.0.0      # Interfaz gráfica
Pillow>=9.0.0             # Procesamiento de imágenes
```

---

## Instalación (desarrollo)

```bash
git clone https://github.com/Maxitelmo/NEXIOS.git
cd NEXIOS
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

---

## Compilar el portable (PyInstaller)

```bash
cd NEXIOS
venv\Scripts\activate
pyinstaller build_nexios.spec
```

El ejecutable portable queda en `dist\NEXIOS_1.0.0\NEXIOS.exe`. Copiar la carpeta completa al pendrive.

---

## Flujo de uso en campo

```
1. DETECCIÓN
   Conectar iPhone por USB → NEXIOS detecta el dispositivo automáticamente
   Pantalla: modelo, iOS, serial, IMEI, batería

2. PAIRING (primera vez)
   iPhone muestra "¿Confiar en esta computadora?" → aceptar en el dispositivo
   El pairing record queda guardado para futuras sesiones

3. EXTRACCIÓN SELECTIVA
   Seleccionar los artifacts a extraer → pulsar "Extraer"
   Tiempo estimado: 2-5 minutos para los artifacts principales
   Fotos y media pueden extender el tiempo según volumen

4. CAPTURA DE PANTALLA
   NEXIOS detecta Developer Mode automáticamente
   ├── Activo → captura directa
   └── iOS 16+ sin Developer Mode → NEXIOS informa al operador
       └── Si activa → queda registrado en la cadena de custodia

5. FOTOGRAFÍAS MANUALES
   Importar fotos tomadas con el propio dispositivo del operador
   NEXIOS extrae EXIF, hashea y registra operador + descripción

6. CIERRE DEL RELEVAMIENTO
   SHA-256 de cada archivo extraído
   Log encadenado con hash_final_log
   manifest_hashes.json generado
   Carpeta bloqueada en solo lectura

7. INFORME PDF
   Portada, info del dispositivo, artifacts con hashes,
   capturas, fotos del operador, cadena de custodia
```

---

## Captura de pantalla — iOS 16+

A partir de iOS 16, Apple requiere que **Developer Mode** esté activo para usar `ScreenshotService` vía USB.

| iOS | Developer Mode requerido | Comportamiento |
|-----|-------------------------|----------------|
| 15 y anteriores | No | Captura directa automática |
| 16 en adelante | Sí | NEXIOS detecta el estado e informa al operador |

Si el operador activa Developer Mode, la activación y el reinicio del dispositivo quedan **registrados en la cadena de custodia** con timestamp.

---

## Cadena de custodia forense

NEXIOS implementa los tres pilares del núcleo forense portado de CAPTA:

### `hash_utils.py`
SHA-256 de cada archivo en bloques de 64 KB. Se aplica a cada artifact, captura y foto importada.

### `forensic_log_chain.py`
Log con hash encadenado alineado con **NIST Mobile Forensics 2014**. Cada evento del operativo se encadena criptográficamente al anterior:

```
hash_actual = SHA256(hash_anterior + "[timestamp] | " + evento)
```

Si alguien modifica una línea del log, la cadena completa queda inválida y el verificador lo detecta.

### `integrity.py`
Al cerrar el expediente genera `manifest_hashes.json` con SHA-256 de todos los archivos, bloquea la carpeta en solo lectura y registra el `HASH_FINAL_LOG` que ancla el expediente.

---

## Limitaciones

### Sin jailbreak
- Sin acceso al filesystem completo (`/private/var/`)
- Signal y apps con cifrado E2E: se registra presencia, no contenido
- Keychain de terceros inaccesible
- Datos exclusivos en iCloud requieren credenciales Apple ID

### Operativas de campo
- **Confianza del dispositivo**: el iPhone debe estar en estado AFU (*After First Unlock*) y confirmar "Confiar en esta computadora". En estado BFU (*Before First Unlock*) no es posible.
- **Inactivity Reboot (iOS 18+)**: el dispositivo se reinicia automáticamente tras 72 hs de inactividad, pasando a BFU. La extracción debe realizarse dentro de esa ventana.
- **Locked Apps (iOS 18+)**: apps individuales pueden estar bloqueadas con biométrico incluso con el dispositivo desbloqueado.
- **Captura de pantalla en iOS 16+**: requiere Developer Mode activo.

---

## Estructura del proyecto

```
NEXIOS/
├── main.py                          # Punto de entrada
├── version_nexios.py                # Versión
├── requirements.txt                 # Dependencias
├── build_nexios.spec                # Spec PyInstaller
└── nexios/
    ├── core/
    │   ├── device_service.py        # Detección, pairing, info dispositivo
    │   ├── acquisition_service.py   # Extracción de 21 artifacts
    │   └── screenshot_service.py    # Captura de pantalla
    ├── parsers/ios/                 # Un parser por artifact (19 módulos)
    ├── modules/
    │   └── fotos_operativo.py       # Fotografías del operador
    ├── utils/
    │   ├── file_system.py           # Gestión de rutas portable
    │   ├── hash_utils.py            # SHA-256
    │   ├── forensic_log_chain.py    # Log encadenado NIST
    │   └── integrity.py             # Manifiesto + bloqueo
    ├── pdf/
    │   └── report_generator.py      # Informe forense PDF
    └── ui/
        ├── main_window.py           # Ventana principal
        ├── device_panel.py          # Panel dispositivo
        ├── acquisition_panel.py     # Panel adquisición
        ├── screenshot_panel.py      # Panel captura
        └── fotos_panel.py           # Panel fotos operativo
```

---

## Relación con CAPTA

NEXIOS y CAPTA son herramientas complementarias del MPF:

| | CAPTA | NEXIOS |
|-|-------|--------|
| Plataforma | Android | iOS (iPhone) |
| Protocolo | ADB | pymobiledevice3 |
| Jailbreak/Root | No requerido | No requerido |
| Núcleo forense | ✅ | ✅ (portado de CAPTA) |
| Informe PDF | ✅ | ✅ |
| Portable | ✅ | ✅ |

---

## Licencia

**GNU General Public License v3.0**

Compatible con pymobiledevice3 (GPLv3). Cualquier trabajo derivado de NEXIOS debe mantener la misma licencia, garantizando que la herramienta permanezca open source.

Ver [LICENSE](LICENSE) para el texto completo.

---

## Autoría

**Autor:** Tec. Maximiliano Facundo Telmo González  
**Institución:** Ministerio Público Fiscal de la Nación — Dirección de Informática y Orientación al Ciudadano, Córdoba  
**Contacto:** maximilianotelmofg@gmail.com

---

*NEXIOS — Núcleo de Extracción Forense en dispositivos iOS*
