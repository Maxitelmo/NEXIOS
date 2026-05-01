# report_generator.py
# Generación del informe forense PDF de NEXIOS.
# Usa reportlab (mismo patrón que CAPTA — módulos Mixin por sección).
# TODO: implementar cada sección como un Mixin (portada, técnica, artifacts, capturas, fotos, cadena).

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

_log = logging.getLogger(__name__)

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm, mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, Image as RLImage, HRFlowable,
    )
    from reportlab.platypus.flowables import Flowable
    _RL_AVAILABLE = True
except ImportError:
    _RL_AVAILABLE = False
    _log.warning("reportlab no disponible — generación de PDF deshabilitada")

try:
    from PIL import Image as PILImage
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False


# ── Paleta de colores institucional ────────────────────────────────────────────
COLOR_PRIMARIO    = colors.HexColor("#1a3a5c")   # Azul MPF oscuro
COLOR_SECUNDARIO  = colors.HexColor("#2e6da4")   # Azul MPF medio
COLOR_ACENTO      = colors.HexColor("#e8f0fa")   # Fondo tabla encabezado
COLOR_TEXTO       = colors.HexColor("#1a1a1a")
COLOR_OK          = colors.HexColor("#2d7a2d")
COLOR_ALERTA      = colors.HexColor("#c0392b")


class GeneradorPDF:
    """
    Generador del informe forense NEXIOS en PDF.

    Secciones:
        1. Portada
        2. Información del dispositivo
        3. Artifacts extraídos (tabla de hashes)
        4. Capturas de pantalla
        5. Fotografías del operador
        6. Cadena de custodia (log forense)
        7. Acta de recolección
    """

    def __init__(
        self,
        carpeta_relevamiento: str,
        expediente: str,
        operador: str,
        info_dispositivo: dict,
        resultados_artifacts: list[dict],
        capturas: list[dict],
        fotos_operativo: list[dict],
        hash_final_log: str,
        version: str,
        logger=None,
        base_path: str = "",
    ):
        self.carpeta    = carpeta_relevamiento
        self.expediente = expediente
        self.operador   = operador
        self.info_disp  = info_dispositivo
        self.artifacts  = resultados_artifacts
        self.capturas   = capturas
        self.fotos_op   = fotos_operativo
        self.hash_final = hash_final_log
        self.version    = version
        self.logger     = logger or _log
        self.base_path  = base_path
        self.timestamp  = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    def exportar_pdf(self, ruta_salida: Optional[str] = None) -> str:
        """
        Genera el PDF y lo guarda en ruta_salida (o en Reporte_Forense/ por defecto).

        Returns:
            Ruta completa del PDF generado.
        """
        if not _RL_AVAILABLE:
            raise RuntimeError("reportlab no disponible — no se puede generar el PDF")

        if not ruta_salida:
            reporte_folder = os.path.join(self.carpeta, "Reporte_Forense")
            os.makedirs(reporte_folder, exist_ok=True)
            nombre = f"NEXIOS_{self.expediente}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            ruta_salida = os.path.join(reporte_folder, nombre)

        doc = SimpleDocTemplate(
            ruta_salida,
            pagesize=A4,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            topMargin=2.5 * cm,
            bottomMargin=2 * cm,
            title=f"NEXIOS — Informe Forense {self.expediente}",
            author=self.operador,
        )
        story = []
        styles = getSampleStyleSheet()

        story += self._seccion_portada(styles)
        story.append(PageBreak())
        story += self._seccion_info_dispositivo(styles)
        story.append(PageBreak())
        story += self._seccion_artifacts(styles)
        story.append(PageBreak())
        story += self._seccion_capturas(styles)
        if self.fotos_op:
            story.append(PageBreak())
            story += self._seccion_fotos_operativo(styles)
        story.append(PageBreak())
        story += self._seccion_cadena_custodia(styles)

        doc.build(story)
        self.logger.info("PDF generado: %s", ruta_salida)
        return ruta_salida

    # ── Secciones ──────────────────────────────────────────────────────────────

    def _seccion_portada(self, styles) -> list:
        """TODO: portada completa con logo MPF, datos del expediente, hashes."""
        story = []
        titulo = ParagraphStyle(
            "titulo_portada",
            parent=styles["Title"],
            fontSize=28,
            textColor=COLOR_PRIMARIO,
            spaceAfter=20,
        )
        subtitulo = ParagraphStyle(
            "subtitulo_portada",
            parent=styles["Heading2"],
            fontSize=14,
            textColor=COLOR_SECUNDARIO,
            spaceAfter=8,
        )
        normal = styles["Normal"]
        story.append(Spacer(1, 3 * cm))
        story.append(Paragraph("NEXIOS", titulo))
        story.append(Paragraph("Núcleo de Extracción Forense en dispositivos iOS", subtitulo))
        story.append(HRFlowable(width="100%", thickness=2, color=COLOR_PRIMARIO))
        story.append(Spacer(1, 1 * cm))
        datos_portada = [
            ["Expediente:", self.expediente],
            ["Operador:", self.operador],
            ["Dispositivo:", self._nombre_dispositivo()],
            ["iOS:", self.info_disp.get("ios_version", "")],
            ["IMEI:", self.info_disp.get("imei", "")],
            ["Serial:", self.info_disp.get("serial", "")],
            ["Fecha/hora:", self.timestamp],
            ["Versión NEXIOS:", self.version],
        ]
        tabla = Table(datos_portada, colWidths=[5 * cm, 11 * cm])
        tabla.setStyle(TableStyle([
            ("FONTNAME",    (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE",    (0, 0), (-1, -1), 10),
            ("TEXTCOLOR",   (0, 0), (0, -1), COLOR_PRIMARIO),
            ("FONTNAME",    (0, 0), (0, -1), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, COLOR_ACENTO]),
            ("TOPPADDING",  (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(tabla)
        story.append(Spacer(1, 2 * cm))
        story.append(Paragraph(
            f"<b>HASH FINAL LOG:</b> <font name='Courier'>{self.hash_final or 'N/D'}</font>",
            normal,
        ))
        story.append(Spacer(1, 1 * cm))
        story.append(Paragraph(
            "Ministerio Público Fiscal de la Nación — Córdoba",
            ParagraphStyle("inst", parent=styles["Normal"], textColor=COLOR_SECUNDARIO, fontSize=9),
        ))
        return story

    def _seccion_info_dispositivo(self, styles) -> list:
        """TODO: tabla completa con info técnica del dispositivo."""
        story = [Paragraph("Información del dispositivo", styles["Heading1"])]
        campos = [
            ("Nombre", "nombre"), ("Modelo", "modelo_str"), ("iOS", "ios_version"),
            ("Build", "build_version"), ("Serial", "serial"), ("IMEI", "imei"),
            ("UDID", "udid"), ("Hardware", "nombre_hw"), ("Capacidad", "capacidad_gb"),
            ("Batería", "bateria_pct"), ("Color", "color"),
        ]
        datos = [["Campo", "Valor"]]
        for label, key in campos:
            datos.append([label, str(self.info_disp.get(key) or "")])
        tabla = Table(datos, colWidths=[5 * cm, 11 * cm])
        tabla.setStyle(TableStyle([
            ("BACKGROUND",  (0, 0), (-1, 0), COLOR_PRIMARIO),
            ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
            ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_ACENTO]),
            ("GRID",        (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTSIZE",    (0, 0), (-1, -1), 9),
            ("TOPPADDING",  (0, 0), (-1, -1), 4),
        ]))
        story.append(tabla)
        return story

    def _seccion_artifacts(self, styles) -> list:
        """Tabla de artifacts extraídos con hashes SHA-256."""
        story = [Paragraph("Artifacts extraídos", styles["Heading1"])]
        datos = [["#", "Artifact", "Estado", "SHA-256"]]
        for i, r in enumerate(self.artifacts, 1):
            estado = "OK" if r.get("ok") else r.get("mensaje", "NO ENCONTRADO")[:30]
            sha = (r.get("sha256") or "")[:16] + "..." if r.get("sha256") else ""
            datos.append([str(i), r.get("nombre", ""), estado, sha])
        tabla = Table(datos, colWidths=[1 * cm, 6 * cm, 4 * cm, 5 * cm])
        tabla.setStyle(TableStyle([
            ("BACKGROUND",  (0, 0), (-1, 0), COLOR_PRIMARIO),
            ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
            ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",    (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_ACENTO]),
            ("GRID",        (0, 0), (-1, -1), 0.3, colors.grey),
        ]))
        story.append(tabla)
        return story

    def _seccion_capturas(self, styles) -> list:
        """Capturas de pantalla con hash y descripción."""
        story = [Paragraph("Capturas de pantalla", styles["Heading1"])]
        if not self.capturas:
            story.append(Paragraph("No se realizaron capturas de pantalla.", styles["Normal"]))
            return story
        for cap in self.capturas:
            if cap.get("ruta_local") and os.path.isfile(cap["ruta_local"]):
                try:
                    img = RLImage(cap["ruta_local"], width=15 * cm, height=10 * cm, kind="proportional")
                    story.append(img)
                except Exception:
                    pass
            story.append(Paragraph(f"SHA-256: {cap.get('sha256', '')}", styles["Normal"]))
            story.append(Spacer(1, 0.5 * cm))
        return story

    def _seccion_fotos_operativo(self, styles) -> list:
        """Fotografías manuales del operador."""
        story = [Paragraph("Fotografías del operador", styles["Heading1"])]
        for foto in self.fotos_op:
            story.append(Paragraph(
                f"<b>#{foto.get('numero', '')} — {foto.get('descripcion', '(sin descripción)')}</b>",
                styles["Normal"],
            ))
            story.append(Paragraph(f"Operador: {foto.get('operador', '')}", styles["Normal"]))
            story.append(Paragraph(f"SHA-256: {foto.get('sha256', '')}", styles["Normal"]))
            exif = foto.get("exif", {})
            if exif.get("fecha"):
                story.append(Paragraph(f"Fecha EXIF: {exif['fecha']}", styles["Normal"]))
            if exif.get("gps_lat"):
                story.append(Paragraph(f"GPS: {exif['gps_lat']}, {exif['gps_lon']}", styles["Normal"]))
            if foto.get("ruta_local") and os.path.isfile(foto["ruta_local"]):
                try:
                    img = RLImage(foto["ruta_local"], width=15 * cm, height=10 * cm, kind="proportional")
                    story.append(img)
                except Exception:
                    pass
            story.append(Spacer(1, 0.5 * cm))
        return story

    def _seccion_cadena_custodia(self, styles) -> list:
        """Resumen de cadena de custodia con hash final."""
        story = [Paragraph("Cadena de custodia", styles["Heading1"])]
        story.append(Paragraph(
            f"<b>HASH_FINAL_LOG:</b> <font name='Courier'>{self.hash_final or 'N/D'}</font>",
            styles["Normal"],
        ))
        story.append(Spacer(1, 0.5 * cm))
        ruta_log = os.path.join(self.carpeta, "registro_forense.log")
        if os.path.isfile(ruta_log):
            story.append(Paragraph(
                "El log forense completo está disponible en <i>registro_forense.log</i> "
                "dentro de la carpeta del relevamiento. La cadena de hashes puede "
                "verificarse con NEXIOS Verificador.",
                styles["Normal"],
            ))
        return story

    def _nombre_dispositivo(self) -> str:
        nombre = self.info_disp.get("nombre") or ""
        modelo = self.info_disp.get("modelo_str") or ""
        if nombre and modelo:
            return f"{nombre} ({modelo})"
        return nombre or modelo or "Desconocido"
