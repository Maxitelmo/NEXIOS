# screenshot_panel.py
# Panel de captura de pantalla del dispositivo iOS.
# Detecta automáticamente Developer Mode y maneja iOS 16+.

import logging
import threading

import customtkinter as ctk

from nexios.core import screenshot_service

_log = logging.getLogger(__name__)

COLOR_OK     = "#2d7a2d"
COLOR_ALERTA = "#c0392b"
COLOR_BTN    = "#2e6da4"
COLOR_TEXTO  = "#e8eaf0"

try:
    from PIL import Image, ImageTk
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False


class ScreenshotPanel(ctk.CTkFrame):
    """Panel de captura de pantalla con detección de Developer Mode."""

    def __init__(self, master, main_window):
        super().__init__(master, fg_color="transparent")
        self.mw = main_window
        self._contador = 0
        self._capturas: list[dict] = []
        self._build_ui()

    def _build_ui(self) -> None:
        ctk.CTkLabel(
            self,
            text="Captura de pantalla",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLOR_TEXTO,
        ).pack(anchor="w", padx=24, pady=(20, 4))

        # Estado Developer Mode
        dm_frame = ctk.CTkFrame(self, fg_color="#242b3d", corner_radius=8)
        dm_frame.pack(fill="x", padx=24, pady=(0, 12))
        ctk.CTkLabel(dm_frame, text="Developer Mode:", text_color="#6a8faf",
                     font=ctk.CTkFont(size=10)).pack(anchor="w", padx=12, pady=(8, 0))
        self._lbl_dm = ctk.CTkLabel(
            dm_frame,
            text="Sin verificar",
            font=ctk.CTkFont(size=11),
            text_color="#6a8faf",
        )
        self._lbl_dm.pack(anchor="w", padx=12, pady=(2, 8))

        # Descripción
        desc_frame = ctk.CTkFrame(self, fg_color="transparent")
        desc_frame.pack(fill="x", padx=24, pady=(0, 12))
        ctk.CTkLabel(desc_frame, text="Descripción:", text_color="#6a8faf",
                     font=ctk.CTkFont(size=10)).pack(anchor="w")
        self._entry_desc = ctk.CTkEntry(desc_frame, width=400,
                                         placeholder_text="(opcional) descripción de la captura")
        self._entry_desc.pack(anchor="w", pady=(4, 0))

        # Botones
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(anchor="w", padx=24, pady=(0, 12))
        ctk.CTkButton(
            btn_frame, text="🔍  Verificar Developer Mode", width=200,
            fg_color="#3a5a7c", command=self._verificar_dm,
        ).pack(side="left", padx=(0, 8))
        self._btn_capturar = ctk.CTkButton(
            btn_frame, text="📸  Capturar pantalla", fg_color=COLOR_BTN, width=180,
            command=self._capturar, state="disabled",
        )
        self._btn_capturar.pack(side="left")

        # Advertencia Developer Mode
        self._lbl_aviso = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=10),
            text_color=COLOR_ALERTA,
            wraplength=600,
            justify="left",
        )
        self._lbl_aviso.pack(anchor="w", padx=24, pady=(0, 8))

        # Preview de la última captura
        ctk.CTkLabel(self, text="Última captura:", text_color="#6a8faf",
                     font=ctk.CTkFont(size=10)).pack(anchor="w", padx=24)
        self._preview = ctk.CTkLabel(self, text="(ninguna)", fg_color="#1a1f2e",
                                      width=400, height=260)
        self._preview.pack(padx=24, pady=(4, 0))

        # Log
        self._log_box = ctk.CTkTextbox(self, height=80, state="disabled",
                                        font=ctk.CTkFont(family="Courier", size=9))
        self._log_box.pack(fill="x", padx=24, pady=(8, 24))

    def _log(self, msg: str) -> None:
        self._log_box.configure(state="normal")
        self._log_box.insert("end", msg + "\n")
        self._log_box.see("end")
        self._log_box.configure(state="disabled")

    def _verificar_dm(self) -> None:
        if not self.mw.lockdown:
            self.mw.set_status("Primero conectá un dispositivo", "alerta")
            return
        def run():
            estado = screenshot_service.verificar_developer_mode(self.mw.lockdown)
            self.after(0, lambda: self._on_dm_verificado(estado))
        threading.Thread(target=run, daemon=True).start()

    def _on_dm_verificado(self, estado: dict) -> None:
        requiere = estado.get("requiere_dev_mode", False)
        if not requiere:
            self._lbl_dm.configure(
                text=f"✅ Sin restricciones — iOS {estado['ios_version']}", text_color=COLOR_OK)
            self._lbl_aviso.configure(text="")
            self.mw.set_status("Captura habilitada sin restricciones", "ok")
        else:
            self._lbl_dm.configure(
                text=f"⚠️ Requiere Developer Mode — iOS {estado['ios_version']}", text_color=COLOR_ALERTA)
            self._lbl_aviso.configure(text=estado["mensaje"])
            self.mw.set_status("iOS 16+: se necesita Developer Mode activo", "alerta")
        # Habilitar siempre: si DM está inactivo, capturar_pantalla() informará claramente
        self._btn_capturar.configure(state="normal")
        self._log(estado["mensaje"])

    def _capturar(self) -> None:
        if not self.mw.lockdown or not self.mw.carpeta_rel:
            self.mw.set_status("Conectá dispositivo e iniciá un relevamiento primero", "alerta")
            return
        self._btn_capturar.configure(state="disabled", text="Capturando...")
        self._contador += 1
        import os
        carpeta_cap = os.path.join(self.mw.carpeta_rel, "Capturas")
        def run():
            r = screenshot_service.capturar_pantalla(
                lockdown=self.mw.lockdown,
                carpeta_capturas=carpeta_cap,
                carpeta_relevamiento=self.mw.carpeta_rel,
                numero=self._contador,
                descripcion=self._entry_desc.get().strip(),
            )
            self.after(0, lambda: self._on_captura(r))
        threading.Thread(target=run, daemon=True).start()

    def _on_captura(self, resultado: dict) -> None:
        self._btn_capturar.configure(state="normal", text="📸  Capturar pantalla")
        if resultado["ok"]:
            self._capturas.append(resultado)
            self.mw.capturas.append(resultado)
            self._log(f"  ✅ {resultado['ruta_local']}")
            self._log(f"     SHA-256: {resultado['sha256']}")
            self.mw.set_status(f"Captura #{self._contador} guardada", "ok")
            self._mostrar_preview(resultado["ruta_local"])
        else:
            self._log(f"  ❌ Error: {resultado['mensaje']}")
            self.mw.set_status(f"Error en captura: {resultado['mensaje']}", "alerta")

    def _mostrar_preview(self, ruta: str) -> None:
        if not _PIL_AVAILABLE:
            return
        try:
            img = Image.open(ruta)
            img.thumbnail((400, 260))
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(img.width, img.height))
            self._preview.configure(image=ctk_img, text="")
            self._preview._image = ctk_img  # evitar GC
        except Exception as e:
            _log.warning("No se pudo mostrar preview: %s", e)
