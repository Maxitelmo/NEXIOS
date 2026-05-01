# Contribuciones a NEXIOS

Gracias por tu interés en contribuir. NEXIOS es una herramienta de uso forense institucional; las contribuciones deben mantener los estándares de calidad, trazabilidad y licencia open source del proyecto.

---

## Cómo contribuir

### Reportar un bug

Abrí un [Issue](https://github.com/Maxitelmo/NEXIOS/issues) con:

- Versión de NEXIOS y versión de iOS del dispositivo afectado.
- Pasos para reproducir el problema.
- Comportamiento esperado vs comportamiento real.
- Si es posible: el log `registro_forense.log` **sin datos de dispositivos reales** (anonimizá UDIDs, IMEIs, números de teléfono).

### Proponer un artifact nuevo

Abrí un Issue con:

- Nombre del artifact.
- Dominio y ruta exacta en iOS.
- Tipo de extracción (backup_domain / AFC / service).
- Ejemplo de estructura del archivo (esquema SQLite o plist).

### Pull Request

1. Forkear el repositorio.
2. Crear una rama descriptiva: `feature/parser-signal`, `fix/afc-timeout`, `docs/manual-usuario`.
3. Asegurarse de que el código nuevo:
   - No rompe imports existentes.
   - Maneja errores con `try/except` y los registra con `logging`.
   - No commitea datos de dispositivos reales ni pairing records.
4. Abrir el PR con descripción clara del cambio.

---

## Estándares de código

- **Python 3.11+**, sin dependencias adicionales a las declaradas en `requirements.txt`.
- Nombres de variables y funciones en **español** (consistente con CAPTA y el resto del proyecto).
- Sin comentarios que expliquen qué hace el código — solo comentarios que expliquen el **por qué** cuando no es obvio.
- Cada parser debe seguir el patrón: `parsear(ruta) -> list[dict]`, con `ARTIFACT_ID` y `NOMBRE` como constantes de módulo.
- Toda acción del operativo que modifique el estado del dispositivo o adquiera evidencia debe registrarse con `append_evento_forense()`.

---

## Licencia

Al contribuir aceptás que tu código se distribuirá bajo **GPLv3**, igual que el resto del proyecto.

---

## Contacto

Maximiliano Telmo — maximilianotelmofg@gmail.com  
Ministerio Público Fiscal de la Nación — Córdoba
