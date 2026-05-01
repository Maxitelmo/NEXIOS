# acquisition_panel.py
# Panel de adquisición de artifacts iOS con selección individual y barra de progreso.

import logging
import os
import threading

import customtkinter as ctk

from nexios.core.acquisition_service import ARTIFACTS, extraer_todos
from nexios.utils.forensic_log_chain import append_evento_forense, init_cadena

_log = logging.getLogger(__name__)

COLOR_OK     = "#2d7a2d"
COLOR_ALERTA = "#c0392b"
COLOR_BTN    = "#2e6da4"
COLOR_TEXTO  = "#e8eaf0"


class AcquisitionPanel(ctk.CTkFrame):
    """Panel de adquisición selectiva de artifacts forenses."""

    def __init__(self, master, main_window):
        super().__init__(master, fg_color="transparent")
        self.mw = main_window
        self._checks: dict[str, ctk.BooleanVar] = {}
        self._estados: dict[str, ctk.CTkLabel] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        ctk.CTkLabel(
            self,
            text="Adquisición de artifacts",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLOR_TEXTO,
        ).pack(anchor="w", padx=24, pady=(20, 4))
        ctk.CTkLabel(
            self,
            text="Seleccioná los artifacts a extraer y pulsá Extraer.",
            font=ctk.CTkFont(size=11),
            text_color="#6a8faf",
        ).pack(anchor="w", padx=24, pady=(0, 12))

        # Campos del caso
        caso_frame = ctk.CTkFrame(self, fg_color="#242b3d", corner_radius=8)
        caso_frame.pack(fill="x", padx=24, pady=(0, 12))
        for label, attr in [("Expediente:", "entry_exp"), ("Caso:", "entry_caso"), ("Operador:", "entry_op")]:
            row = ctk.CTkFrame(caso_frame, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=4)
            ctk.CTkLabel(row, text=label, width=90, anchor="w",
                         text_color="#6a8faf", font=ctk.CTkFont(size=10)).pack(side="left")
            entry = ctk.CTkEntry(row, width=300)
            entry.pack(side="left")
            setattr(self, attr, entry)

        # Checkboxes de artifacts
        scroll = ctk.CTkScrollableFrame(self, label_text="Artifacts disponibles", height=240)
        scroll.pack(fill="x", padx=24, pady=(0, 12))
        for defn in ARTIFACTS:
            row = ctk.CTkFrame(scroll, fg_color="transparent")
            row.pack(fill="x", pady=1)
            var = ctk.BooleanVar(value=True)
            self._checks[defn["id"]] = var
            ctk.CTkCheckBox(row, text=f"  {defn['nombre']}", variable=var,
                            font=ctk.CTkFont(size=11)).pack(side="left")
            lbl = ctk.CTkLabel(row, text="⏳", font=ctk.CTkFont(size=11), text_color="#6a8faf")
            lbl.pack(side="right", padx=8)
            self._estados[defn["id"]] = lbl

        # Botones
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(anchor="w", padx=24, pady=(0, 12))
        ctk.CTkButton(btn_frame, text="☑ Todos", width=90,
                      command=self._seleccionar_todos).pack(side="left", padx=(0, 4))
        ctk.CTkButton(btn_frame, text="☐ Ninguno", width=90,
                      command=self._deseleccionar_todos).pack(side="left", padx=(0, 12))
        self._btn_extraer = ctk.CTkButton(
            btn_frame, text="⚡  Extraer artifacts seleccionados",
            fg_color=COLOR_BTN, width=240, command=self._iniciar_extraccion,
        )
        self._btn_extraer.pack(side="left")

        # Barra de progreso y log
        self._progress = ctk.CTkProgressBar(self)
        self._progress.pack(fill="x", padx=24, pady=(0, 8))
        self._progress.set(0)
        self._log_box = ctk.CTkTextbox(self, height=100, state="disabled",
                                        font=ctk.CTkFont(family="Courier", size=9))
        self._log_box.pack(fill="both", expand=True, padx=24, pady=(0, 24))

    def _seleccionar_todos(self) -> None:
        for v in self._checks.values():
            v.set(True)

    def _deseleccionar_todos(self) -> None:
        for v in self._checks.values():
            v.set(False)

    def _log(self, mensaje: str) -> None:
        self._log_box.configure(state="normal")
        self._log_box.insert("end", mensaje + "\n")
        self._log_box.see("end")
        self._log_box.configure(state="disabled")

    def _iniciar_extraccion(self) -> None:
        if not self.mw.lockdown:
            self.mw.set_status("Primero conectá un dispositivo en el panel Dispositivo", "alerta")
            return
        expediente = self.entry_exp.get().strip()
        caso       = self.entry_caso.get().strip()
        operador   = self.entry_op.get().strip()
        if not expediente or not caso or not operador:
            self.mw.set_status("Completá expediente, caso y operador", "alerta")
            return
        ids_selec = [aid for aid, v in self._checks.items() if v.get()]
        if not ids_selec:
            self.mw.set_status("Seleccioná al menos un artifact", "alerta")
            return
        try:
            carpeta, ts = self.mw.fs.create_relevamiento_structure(expediente, caso, operador)
        except Exception as e:
            self.mw.set_status(f"Error creando carpeta: {e}", "alerta")
            return
        self.mw.carpeta_rel = carpeta
        init_cadena(carpeta)
        append_evento_forense(carpeta, f"INICIO RELEVAMIENTO: exp={expediente} | caso={caso} | operador={operador}")
        carpeta_artifacts = os.path.join(carpeta, "Artifacts")
        os.makedirs(carpeta_artifacts, exist_ok=True)
        self._btn_extraer.configure(state="disabled", text="Extrayendo...")
        self._progress.set(0)
        for lbl in self._estados.values():
            lbl.configure(text="⏳", text_color="#6a8faf")
        total = len(ids_selec)

        def progress_cb(artifact_id: str, estado: str) -> None:
            iconos = {"extrayendo": "⏳", "ok": "✅", "no_encontrado": "⚠️", "error": "❌"}
            icono = iconos.get(estado, "⏳")
            lbl = self._estados.get(artifact_id)
            if lbl:
                self.after(0, lambda: lbl.configure(text=icono))
            self.after(0, lambda: self._log(f"  {artifact_id}: {estado}"))

        def run():
            resultados = extraer_todos(
                lockdown=self.mw.lockdown,
                artifact_ids=ids_selec,
                carpeta_artifacts=carpeta_artifacts,
                carpeta_relevamiento=carpeta,
                progress_cb=lambda aid, est: (progress_cb(aid, est),
                                              self.after(0, lambda n=(ids_selec.index(aid)+1)/total:
                                                         self._progress.set(n)))[0],
            )
            self.after(0, lambda: self._on_extraccion_completa(resultados, carpeta))

        threading.Thread(target=run, daemon=True).start()

    def _on_extraccion_completa(self, resultados: list, carpeta: str) -> None:
        self._btn_extraer.configure(state="normal", text="⚡  Extraer artifacts seleccionados")
        self._progress.set(1)
        ok  = sum(1 for r in resultados if r.get("ok"))
        err = len(resultados) - ok
        self._log(f"\n  ✅ Completado: {ok} ok, {err} no disponibles")
        self._log(f"  📁 Carpeta: {carpeta}")
        self.mw.set_status(f"Extracción completada: {ok}/{len(resultados)} artifacts", "ok")
