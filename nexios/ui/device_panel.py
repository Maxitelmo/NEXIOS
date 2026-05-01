# device_panel.py
# Panel de conexión, pairing e información del dispositivo iOS.

import logging
import threading

import customtkinter as ctk

from nexios.core import device_service

_log = logging.getLogger(__name__)

COLOR_PRIMARIO  = "#1a3a5c"
COLOR_PANEL     = "#242b3d"
COLOR_TEXTO     = "#e8eaf0"
COLOR_OK        = "#2d7a2d"
COLOR_ALERTA    = "#c0392b"
COLOR_BTN       = "#2e6da4"


class DevicePanel(ctk.CTkFrame):
    """Panel de detección, pairing y visualización de info del dispositivo."""

    def __init__(self, master, main_window):
        super().__init__(master, fg_color="transparent")
        self.mw = main_window
        self._build_ui()

    def _build_ui(self) -> None:
        # Título
        ctk.CTkLabel(
            self,
            text="Dispositivo",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLOR_TEXTO,
        ).pack(anchor="w", padx=24, pady=(20, 4))
        ctk.CTkLabel(
            self,
            text="Conectá el iPhone por USB y pulsá Detectar.",
            font=ctk.CTkFont(size=11),
            text_color="#6a8faf",
        ).pack(anchor="w", padx=24, pady=(0, 16))

        # Botones
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(anchor="w", padx=24, pady=(0, 16))
        self._btn_detectar = ctk.CTkButton(
            btn_frame,
            text="🔍  Detectar dispositivo",
            fg_color=COLOR_BTN,
            command=self._detectar,
            width=200,
        )
        self._btn_detectar.pack(side="left", padx=(0, 8))
        self._btn_conectar = ctk.CTkButton(
            btn_frame,
            text="🔗  Conectar",
            fg_color=COLOR_OK,
            command=self._conectar,
            width=160,
            state="disabled",
        )
        self._btn_conectar.pack(side="left", padx=(0, 8))

        # Lista de dispositivos detectados
        ctk.CTkLabel(self, text="Dispositivos detectados:", text_color="#6a8faf",
                     font=ctk.CTkFont(size=10)).pack(anchor="w", padx=24)
        self._lista_devs = ctk.CTkTextbox(self, height=60, state="disabled",
                                           font=ctk.CTkFont(family="Courier", size=10))
        self._lista_devs.pack(fill="x", padx=24, pady=(4, 16))

        # Tarjeta de información del dispositivo
        ctk.CTkLabel(self, text="Información del dispositivo:", text_color="#6a8faf",
                     font=ctk.CTkFont(size=10)).pack(anchor="w", padx=24)
        self._info_box = ctk.CTkTextbox(self, height=300, state="disabled",
                                         font=ctk.CTkFont(family="Courier", size=10))
        self._info_box.pack(fill="both", expand=True, padx=24, pady=(4, 24))

        self._devices: list[dict] = []

    def _detectar(self) -> None:
        self._btn_detectar.configure(state="disabled", text="Detectando...")
        self.mw.set_status("Detectando dispositivos iOS...")
        def run():
            devs = device_service.listar_dispositivos()
            self.after(0, lambda: self._on_detectados(devs))
        threading.Thread(target=run, daemon=True).start()

    def _on_detectados(self, devs: list[dict]) -> None:
        self._btn_detectar.configure(state="normal", text="🔍  Detectar dispositivo")
        self._devices = devs
        self._lista_devs.configure(state="normal")
        self._lista_devs.delete("1.0", "end")
        if devs:
            for d in devs:
                self._lista_devs.insert("end", f"  {d.get('nombre')}  —  {d.get('udid')}\n")
            self._btn_conectar.configure(state="normal")
            self.mw.set_status(f"{len(devs)} dispositivo(s) encontrado(s)", "ok")
        else:
            self._lista_devs.insert("end", "  (ningún dispositivo encontrado)")
            self._btn_conectar.configure(state="disabled")
            self.mw.set_status("Sin dispositivos iOS detectados", "alerta")
        self._lista_devs.configure(state="disabled")

    def _conectar(self) -> None:
        self._btn_conectar.configure(state="disabled", text="Conectando...")
        udid = self._devices[0]["udid"] if self._devices else None
        def run():
            lockdown = device_service.conectar(udid=udid)
            self.after(0, lambda: self._on_conectado(lockdown))
        threading.Thread(target=run, daemon=True).start()

    def _on_conectado(self, lockdown) -> None:
        self._btn_conectar.configure(state="normal", text="🔗  Conectar")
        if not lockdown:
            self.mw.set_status("Error al conectar — aceptar 'Confiar en esta computadora' en el iPhone", "alerta")
            return
        self.mw.lockdown = lockdown
        info = device_service.obtener_info_dispositivo(lockdown)
        self.mw.set_status(f"Conectado: {info.get('nombre')} ({info.get('ios_version')})", "ok")
        self._mostrar_info(info)

    def _mostrar_info(self, info: dict) -> None:
        self._info_box.configure(state="normal")
        self._info_box.delete("1.0", "end")
        campos = [
            ("Nombre",       info.get("nombre",        "")),
            ("Modelo",       info.get("modelo_str",    "")),
            ("iOS",          info.get("ios_version",   "")),
            ("Build",        info.get("build_version", "")),
            ("Serial",       info.get("serial",        "")),
            ("IMEI",         info.get("imei",          "")),
            ("UDID",         info.get("udid",          "")),
            ("Hardware",     info.get("nombre_hw",     "")),
            ("Capacidad",    info.get("capacidad_gb",  "")),
            ("Batería",      info.get("bateria_pct",   "")),
        ]
        for label, valor in campos:
            self._info_box.insert("end", f"  {label:<14}: {valor}\n")
        self._info_box.configure(state="disabled")
