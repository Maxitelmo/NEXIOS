# Política de seguridad

## Uso responsable

NEXIOS es una herramienta de forensia digital desarrollada para uso institucional en el **Ministerio Público Fiscal de la Nación Argentina**. Está diseñada exclusivamente para:

- Adquisición forense en dispositivos propios o con autorización judicial expresa.
- Uso por peritos y personal técnico habilitado.
- Operaciones dentro del marco legal vigente.

**El uso de NEXIOS sobre dispositivos sin autorización legal es ilegal.**

---

## Reportar una vulnerabilidad

Si encontrás una vulnerabilidad de seguridad en NEXIOS:

1. **No abras un Issue público** con detalles de la vulnerabilidad.
2. Enviá un reporte privado a: **maximilianotelmofg@gmail.com**
3. Incluí:
   - Descripción del problema.
   - Pasos para reproducirlo.
   - Impacto potencial.
4. Recibirás respuesta dentro de las 72 horas hábiles.

---

## Consideraciones de seguridad del diseño

- NEXIOS no transmite datos a servidores externos. Toda la información permanece localmente.
- Los pairing records de pymobiledevice3 se almacenan localmente y **no deben compartirse**.
- Las carpetas de relevamiento se bloquean en solo lectura al cierre para preservar integridad.
- El log forense usa hashing encadenado — cualquier modificación invalida la cadena completa.
