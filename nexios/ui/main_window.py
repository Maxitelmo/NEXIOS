# main_window.py
# Ventana principal de NEXIOS — CustomTkinter.
# Orquesta los paneles: device, acquisition, screenshot, fotos.

import logging
import os
import sys
import tkinter as tk
from typing import Optional

import customtkinter as ctk
from PIL import Image

from nexios.utils.file_system import FileSystemManager


def _media_path(nombre: str) -> str:
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, "media", nombre)
    return os.path.join(os.path.dirname(__file__), "..", "..", "media", nombre)

_log = logging.getLogger(__name__)

# Tema base
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Paleta NEXIOS
COLOR_PRIMARIO   = "#1a3a5c"
COLOR_SECUNDARIO = "#2e6da4"
COLOR_BG         = "#1a1f2e"
COLOR_PANEL      = "#242b3d"
COLOR_TEXTO      = "#e8eaf0"
COLOR_OK         = "#2d7a2d"
COLOR_ALERTA     = "#c0392b"
COLOR_BTN        = "#2e6da4"


class MainWindow(ctk.CTk):
    """Ventana principal de NEXIOS."""

    def __init__(self, version: str, file_system: FileSystemManager):
        super().__init__()
        self.version     = version
        self.fs          = file_system
        self.lockdown             = None  # LockdownClient activo
        self.carpeta_rel          = ""    # Carpeta del relevamiento actual
        self.info_disp            = {}    # Poblado por DevicePanel tras conexión
        self.resultados_artifacts = []    # Poblado por AcquisitionPanel tras extracción
        self.capturas             = []    # Poblado por ScreenshotPanel por cada captura
        self.fotos_op             = []    # Poblado por FotosPanel por cada lote importado
        self._build_ui()

    def _build_ui(self) -> None:
        self.title(f"NEXIOS v{self.version} — Núcleo de Extracción Forense iOS")
        self.geometry("1200x780")
        self.minsize(900, 620)
        self.configure(fg_color=COLOR_BG)
        self._build_header()
        self._build_sidebar()
        self._build_content_area()
        self._build_statusbar()
        self._show_panel("device")

    def _build_header(self) -> None:
        frame = ctk.CTkFrame(self, fg_color=COLOR_PRIMARIO, height=56, corner_radius=0)
        frame.pack(fill="x", side="top")
        frame.pack_propagate(False)
        # Logo
        logo_path = _media_path("NEXIOS-LOGO.png")
        if os.path.isfile(logo_path):
            try:
                img = Image.open(logo_path)
                ctk_logo = ctk.CTkImage(light_image=img, dark_image=img, size=(36, 36))
                ctk.CTkLabel(frame, image=ctk_logo, text="").pack(side="left", padx=(14, 4), pady=10)
            except Exception:
                pass
        ctk.CTkLabel(
            frame,
            text="NEXIOS",
            font=ctk.CTkFont(family="Helvetica", size=20, weight="bold"),
            text_color="#ffffff",
        ).pack(side="left", padx=(4, 0), pady=10)
        ctk.CTkLabel(
            frame,
            text="Núcleo de Extracción Forense en dispositivos iOS",
            font=ctk.CTkFont(size=11),
            text_color="#a8c4e0",
        ).pack(side="left", padx=10)
        ctk.CTkLabel(
            frame,
            text=f"v{self.version}",
            font=ctk.CTkFont(size=10),
            text_color="#6a8faf",
        ).pack(side="right", padx=20)

    def _build_sidebar(self) -> None:
        self._sidebar = ctk.CTkFrame(self, fg_color=COLOR_PANEL, width=200, corner_radius=0)
        self._sidebar.pack(fill="y", side="left")
        self._sidebar.pack_propagate(False)
        ctk.CTkLabel(
            self._sidebar,
            text="MENÚ",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#6a8faf",
        ).pack(pady=(16, 4), padx=16, anchor="w")
        self._sidebar_btns: dict[str, ctk.CTkButton] = {}
        items = [
            ("device",      "📱  Dispositivo"),
            ("acquisition", "🗂  Adquisición"),
            ("screenshot",  "🖥  Captura pantalla"),
            ("fotos",       "📷  Fotos operativo"),
        ]
        for panel_id, label in items:
            btn = ctk.CTkButton(
                self._sidebar,
                text=label,
                anchor="w",
                fg_color="transparent",
                hover_color="#2e3d57",
                text_color=COLOR_TEXTO,
                font=ctk.CTkFont(size=12),
                command=lambda pid=panel_id: self._show_panel(pid),
            )
            btn.pack(fill="x", padx=8, pady=2)
            self._sidebar_btns[panel_id] = btn

    def _build_content_area(self) -> None:
        self._content = ctk.CTkFrame(self, fg_color=COLOR_BG, corner_radius=0)
        self._content.pack(fill="both", expand=True, side="left", padx=0, pady=0)
        # Los paneles se crean lazily al primer acceso
        self._panels: dict[str, ctk.CTkFrame] = {}
        self._panel_activo: Optional[str] = None

    def _build_statusbar(self) -> None:
        self._statusbar = ctk.CTkFrame(self, fg_color=COLOR_PANEL, height=28, corner_radius=0)
        self._statusbar.pack(fill="x", side="bottom")
        self._statusbar.pack_propagate(False)
        self._status_lbl = ctk.CTkLabel(
            self._statusbar,
            text="Sin dispositivo conectado",
            font=ctk.CTkFont(size=10),
            text_color="#6a8faf",
        )
        self._status_lbl.pack(side="left", padx=12, pady=4)

    def set_status(self, mensaje: str, tipo: str = "info") -> None:
        """Actualiza la barra de estado. tipo: 'info' | 'ok' | 'alerta'."""
        colores = {"info": "#6a8faf", "ok": COLOR_OK, "alerta": COLOR_ALERTA}
        self._status_lbl.configure(
            text=mensaje,
            text_color=colores.get(tipo, "#6a8faf"),
        )

    def _show_panel(self, panel_id: str) -> None:
        for pid, btn in self._sidebar_btns.items():
            btn.configure(fg_color=COLOR_BTN if pid == panel_id else "transparent")
        if self._panel_activo and self._panel_activo in self._panels:
            self._panels[self._panel_activo].pack_forget()
        if panel_id not in self._panels:
            self._panels[panel_id] = self._create_panel(panel_id)
        self._panels[panel_id].pack(fill="both", expand=True)
        self._panel_activo = panel_id

    def _create_panel(self, panel_id: str) -> ctk.CTkFrame:
        from nexios.ui.device_panel      import DevicePanel
        from nexios.ui.acquisition_panel import AcquisitionPanel
        from nexios.ui.screenshot_panel  import ScreenshotPanel
        from nexios.ui.fotos_panel       import FotosPanel
        constructores = {
            "device":      DevicePanel,
            "acquisition": AcquisitionPanel,
            "screenshot":  ScreenshotPanel,
            "fotos":       FotosPanel,
        }
        cls = constructores[panel_id]
        return cls(master=self._content, main_window=self)
