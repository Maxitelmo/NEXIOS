# fotos_panel.py
# Panel de fotografías manuales del operador.

import logging
import os
import threading
import tkinter.filedialog as fd

import customtkinter as ctk

from nexios.modules.fotos_operativo import importar_lote

_log = logging.getLogger(__name__)

COLOR_OK     = "#2d7a2d"
COLOR_ALERTA = "#c0392b"
COLOR_BTN    = "#2e6da4"
COLOR_TEXTO  = "#e8eaf0"

try:
    from PIL import Image
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False


class FotosPanel(ctk.CTkFrame):
    """Panel de importación de fotografías del operador al expediente."""

    def __init__(self, master, main_window):
        super().__init__(master, fg_color="transparent")
        self.mw = main_window
        self._rutas_selec: list[str] = []
        self._numero_siguiente = 1
        self._build_ui()

    def _build_ui(self) -> None:
        ctk.CTkLabel(
            self,
            text="Fotografías del operador",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLOR_TEXTO,
        ).pack(anchor="w", padx=24, pady=(20, 4))
        ctk.CTkLabel(
            self,
            text="Importá fotos tomadas con tu propio dispositivo para incorporarlas al expediente.",
            font=ctk.CTkFont(size=11),
            text_color="#6a8faf",
        ).pack(anchor="w", padx=24, pady=(0, 12))

        # Operador y descripción
        datos_frame = ctk.CTkFrame(self, fg_color="#242b3d", corner_radius=8)
        datos_frame.pack(fill="x", padx=24, pady=(0, 12))
        for label, attr, placeholder in [
            ("Operador:", "entry_op", "Nombre del operador que tomó las fotos"),
            ("Descripción:", "entry_desc", "(opcional) descripción del lote de fotos"),
        ]:
            row = ctk.CTkFrame(datos_frame, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=4)
            ctk.CTkLabel(row, text=label, width=90, anchor="w",
                         text_color="#6a8faf", font=ctk.CTkFont(size=10)).pack(side="left")
            entry = ctk.CTkEntry(row, width=400, placeholder_text=placeholder)
            entry.pack(side="left")
            setattr(self, attr, entry)

        # Botones de selección e importación
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(anchor="w", padx=24, pady=(0, 8))
        ctk.CTkButton(
            btn_frame, text="🗂  Seleccionar fotos", width=180,
            fg_color="#3a5a7c", command=self._seleccionar_fotos,
        ).pack(side="left", padx=(0, 8))
        self._btn_importar = ctk.CTkButton(
            btn_frame, text="📥  Importar al expediente", fg_color=COLOR_BTN, width=220,
            command=self._importar, state="disabled",
        )
        self._btn_importar.pack(side="left")

        # Lista de archivos seleccionados
        ctk.CTkLabel(self, text="Archivos seleccionados:", text_color="#6a8faf",
                     font=ctk.CTkFont(size=10)).pack(anchor="w", padx=24, pady=(4, 0))
        self._lista_box = ctk.CTkTextbox(self, height=120, state="disabled",
                                          font=ctk.CTkFont(family="Courier", size=9))
        self._lista_box.pack(fill="x", padx=24, pady=(4, 12))

        # Log de importación
        ctk.CTkLabel(self, text="Log de importación:", text_color="#6a8faf",
                     font=ctk.CTkFont(size=10)).pack(anchor="w", padx=24)
        self._log_box = ctk.CTkTextbox(self, height=120, state="disabled",
                                        font=ctk.CTkFont(family="Courier", size=9))
        self._log_box.pack(fill="both", expand=True, padx=24, pady=(4, 24))

    def _log(self, msg: str) -> None:
        self._log_box.configure(state="normal")
        self._log_box.insert("end", msg + "\n")
        self._log_box.see("end")
        self._log_box.configure(state="disabled")

    def _seleccionar_fotos(self) -> None:
        rutas = fd.askopenfilenames(
            title="Seleccionar fotografías del operador",
            filetypes=[
                ("Imágenes", "*.jpg *.jpeg *.png *.heic *.tiff *.bmp *.gif"),
                ("Todos los archivos", "*.*"),
            ],
        )
        if not rutas:
            return
        self._rutas_selec = list(rutas)
        self._lista_box.configure(state="normal")
        self._lista_box.delete("1.0", "end")
        for r in self._rutas_selec:
            self._lista_box.insert("end", f"  {os.path.basename(r)}\n")
        self._lista_box.configure(state="disabled")
        self._btn_importar.configure(state="normal")
        self.mw.set_status(f"{len(self._rutas_selec)} foto(s) seleccionada(s)")

    def _importar(self) -> None:
        if not self.mw.carpeta_rel:
            self.mw.set_status("Iniciá un relevamiento desde el panel Adquisición primero", "alerta")
            return
        operador = self.entry_op.get().strip()
        if not operador:
            self.mw.set_status("Completá el nombre del operador", "alerta")
            return
        self._btn_importar.configure(state="disabled", text="Importando...")
        carpeta_fotos = os.path.join(self.mw.carpeta_rel, "Fotos_Operativo")
        desc = self.entry_desc.get().strip()
        descripciones = [desc] * len(self._rutas_selec) if desc else []
        num_inicio = self._numero_siguiente

        def run():
            resultados = importar_lote(
                rutas_origen=self._rutas_selec,
                carpeta_fotos=carpeta_fotos,
                carpeta_relevamiento=self.mw.carpeta_rel,
                operador=operador,
                descripciones=descripciones,
                numero_inicio=num_inicio,
            )
            self.after(0, lambda: self._on_importado(resultados))

        threading.Thread(target=run, daemon=True).start()

    def _on_importado(self, resultados: list) -> None:
        self._btn_importar.configure(state="normal", text="📥  Importar al expediente")
        ok  = sum(1 for r in resultados if r.get("ok"))
        err = len(resultados) - ok
        self._numero_siguiente += ok
        for r in resultados:
            if r.get("ok"):
                self.mw.fotos_op.append(r)
                self._log(f"  ✅ #{r['numero']} {os.path.basename(r['ruta_local'])}  sha={r['sha256'][:12]}...")
            else:
                self._log(f"  ❌ Error: {r.get('mensaje', '')}")
        self._log(f"\n  Total: {ok} importada(s), {err} error(es)")
        self.mw.set_status(f"Fotos importadas: {ok}/{len(resultados)}", "ok" if not err else "alerta")
        self._rutas_selec = []
        self._lista_box.configure(state="normal")
        self._lista_box.delete("1.0", "end")
        self._lista_box.configure(state="disabled")
        self._btn_importar.configure(state="disabled")
