# Changelog

Todos los cambios notables de NEXIOS se documentan aquí.  
Formato basado en [Keep a Changelog](https://keepachangelog.com/es/1.0.0/).

---

## [1.0.0] — 2026-05-01

### Agregado
- Estructura completa del proyecto: `core/`, `parsers/ios/`, `modules/`, `utils/`, `pdf/`, `ui/`.
- `core/device_service.py`: detección de dispositivos iOS por USB, pairing, información técnica completa (modelo, iOS, IMEI, serial, batería, capacidad).
- `core/acquisition_service.py`: definición y extracción selectiva de 21 artifacts forenses via backup domain, AFC e installation_proxy.
- `core/screenshot_service.py`: captura de pantalla vía ScreenshotService, detección automática de Developer Mode, registro de activación en cadena de custodia.
- `parsers/ios/`: 19 parsers independientes (SMS, contactos, llamadas, WhatsApp mensajes y llamadas, fotos+EXIF, Safari, notas, ubicaciones, calendario, recordatorios, Telegram, grabaciones, voicemail, apps instaladas, WiFi, cuentas, fotos eliminadas, uso de apps, Bluetooth).
- `modules/fotos_operativo.py`: importación de fotografías manuales del operador con EXIF, hash SHA-256 y registro en cadena de custodia.
- `utils/hash_utils.py`: SHA-256 en bloques de 64 KB (portado de CAPTA).
- `utils/forensic_log_chain.py`: log forense con hash encadenado NIST Mobile Forensics 2014 (portado de CAPTA).
- `utils/integrity.py`: manifiesto de integridad (`manifest_hashes.json`), bloqueo en solo lectura, verificador (portado de CAPTA).
- `utils/file_system.py`: gestión de rutas portable, detección de modo pendrive vs local, anti path-traversal.
- `pdf/report_generator.py`: generador de informe forense PDF con 7 secciones (portada, info dispositivo, artifacts, capturas, fotos operador, cadena de custodia).
- `ui/main_window.py`: ventana principal CustomTkinter con sidebar de navegación y barra de estado.
- `ui/device_panel.py`: panel de detección, pairing y visualización de info del dispositivo.
- `ui/acquisition_panel.py`: panel de adquisición selectiva con checkboxes, progreso en tiempo real y log.
- `ui/screenshot_panel.py`: panel de captura con verificación de Developer Mode y preview en vivo.
- `ui/fotos_panel.py`: panel de importación de fotografías del operador con selección múltiple.
- `build_nexios.spec`: spec PyInstaller para distribución portable onedir.
- `requirements.txt`: dependencias ancladas (`pymobiledevice3==9.12.0`).

---

*NEXIOS — Núcleo de Extracción Forense en dispositivos iOS*
