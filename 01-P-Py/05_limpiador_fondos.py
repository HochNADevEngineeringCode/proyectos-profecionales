# ==============================================================================
# PROYECTO: Limpiador de Fondos de Imágenes por Lotes (Batch Remover)
# ESTADO : En desarrollo / pausado por optimización de recursos de CPU.
# DESCRIPCIÓN: Procesa lotes de imágenes y genera versiones PNG sin fondo.
# Nota: el procesamiento con modelos de segmentación en CPU puede exigir
# recursos en equipos modestos, por lo que queda sujeto a pruebas/optimización.
# ==============================================================================

import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk
from typing import Optional

from PIL import Image
from rembg import remove

# ==============================================================================
# CONFIGURACIÓN DE FORMATOS SOPORTADOS
# ==============================================================================
EXTENSIONES_IMAGEN = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


# ==============================================================================
# LÓGICA DE PROCESAMIENTO POR LOTES
# ==============================================================================
def listar_imagenes(carpeta_entrada: Path) -> list[Path]:
    """Devuelve la lista ordenada de archivos de imagen en la carpeta indicada."""
    if not carpeta_entrada.exists() or not carpeta_entrada.is_dir():
        return []
    return sorted(
        archivo
        for archivo in carpeta_entrada.iterdir()
        if archivo.is_file() and archivo.suffix.lower() in EXTENSIONES_IMAGEN
    )


def quitar_fondo_archivo(origen: Path, destino: Path) -> tuple[bool, str]:
    """
    Elimina el fondo de una imagen y guarda el resultado en PNG con transparencia.
    Retorna (exito, mensaje).
    """
    try:
        destino.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(origen) as img_original:
            # Convertir a RGBA para asegurar soporte de canal alfa (transparencia)
            img_rgba = img_original.convert("RGBA")
            img_sin_fondo = remove(img_rgba)
            img_sin_fondo.save(destino, format="PNG")
        return True, f"OK -> {destino.name}"
    except Exception as error:
        return False, f"Error en '{origen.name}': {error}"


# ==============================================================================
# INTERFAZ GRÁFICA CON TKINTER
# ==============================================================================
class LimpiadorFondosApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Limpiador de Fondos por Lotes — 05_limpiador_fondos.py")
        self.root.geometry("700x520")
        self.root.minsize(620, 460)

        self.procesando = False
        self.hilo_lote: Optional[threading.Thread] = None

        self._construir_interfaz()

    def _construir_interfaz(self) -> None:
        marco = ttk.Frame(self.root, padding=14)
        marco.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            marco,
            text="Limpiador de Fondos de Imágenes por Lotes",
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor=tk.W, pady=(0, 10))

        # Selección de carpetas
        grupo_carpetas = ttk.LabelFrame(marco, text="Carpetas de trabajo", padding=10)
        grupo_carpetas.pack(fill=tk.X)
        grupo_carpetas.columnconfigure(1, weight=1)

        ttk.Label(grupo_carpetas, text="Carpeta origen:").grid(
            row=0, column=0, sticky=tk.W, pady=4, padx=(0, 8)
        )
        self.entry_origen = ttk.Entry(grupo_carpetas)
        self.entry_origen.grid(row=0, column=1, sticky=tk.EW, pady=4, padx=(0, 8))
        ttk.Button(grupo_carpetas, text="Examinar...", command=self._elegir_origen).grid(
            row=0, column=2, pady=4
        )

        ttk.Label(grupo_carpetas, text="Carpeta salida:").grid(
            row=1, column=0, sticky=tk.W, pady=4, padx=(0, 8)
        )
        self.entry_salida = ttk.Entry(grupo_carpetas)
        self.entry_salida.grid(row=1, column=1, sticky=tk.EW, pady=4, padx=(0, 8))
        ttk.Button(grupo_carpetas, text="Examinar...", command=self._elegir_salida).grid(
            row=1, column=2, pady=4
        )

        # Barra de progreso y botones
        barra_frame = ttk.Frame(marco)
        barra_frame.pack(fill=tk.X, pady=(12, 6))

        self.progreso = ttk.Progressbar(barra_frame, mode="determinate")
        self.progreso.pack(fill=tk.X)

        self.lbl_estado = ttk.Label(barra_frame, text="Listo para procesar imágenes.")
        self.lbl_estado.pack(anchor=tk.W, pady=(4, 0))

        botones = ttk.Frame(marco)
        botones.pack(fill=tk.X, pady=(4, 10))

        self.btn_procesar = ttk.Button(
            botones, text="Procesar lote", command=self.iniciar_lote
        )
        self.btn_procesar.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_limpiar = ttk.Button(
            botones, text="Limpiar registro", command=self.limpiar_log
        )
        self.btn_limpiar.pack(side=tk.RIGHT)

        # Consola de resultados
        ttk.Label(marco, text="Detalle del lote:").pack(anchor=tk.W)
        self.txt_log = scrolledtext.ScrolledText(
            marco, height=13, state=tk.DISABLED, font=("Consolas", 9)
        )
        self.txt_log.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

    def _elegir_origen(self) -> None:
        carpeta = filedialog.askdirectory(title="Seleccioná la carpeta con imágenes")
        if carpeta:
            self.entry_origen.delete(0, tk.END)
            self.entry_origen.insert(0, carpeta)
            if not self.entry_salida.get().strip():
                salida_sugerida = str(Path(carpeta) / "sin_fondo")
                self.entry_salida.delete(0, tk.END)
                self.entry_salida.insert(0, salida_sugerida)

    def _elegir_salida(self) -> None:
        carpeta = filedialog.askdirectory(title="Seleccioná la carpeta de salida")
        if carpeta:
            self.entry_salida.delete(0, tk.END)
            self.entry_salida.insert(0, carpeta)

    def log(self, texto: str) -> None:
        def _escribir() -> None:
            hora = datetime.now().strftime("%H:%M:%S")
            self.txt_log.configure(state=tk.NORMAL)
            self.txt_log.insert(tk.END, f"[{hora}] {texto}\n")
            self.txt_log.see(tk.END)
            self.txt_log.configure(state=tk.DISABLED)

        self.root.after(0, _escribir)

    def _actualizar_progreso(self, actual: int, total: int, estado: str) -> None:
        def _ui() -> None:
            self.progreso["maximum"] = max(total, 1)
            self.progreso["value"] = actual
            self.lbl_estado.config(text=estado)

        self.root.after(0, _ui)

    def limpiar_log(self) -> None:
        self.txt_log.configure(state=tk.NORMAL)
        self.txt_log.delete("1.0", tk.END)
        self.txt_log.configure(state=tk.DISABLED)

    def iniciar_lote(self) -> None:
        if self.procesando:
            return

        origen_str = self.entry_origen.get().strip()
        salida_str = self.entry_salida.get().strip()

        if not origen_str:
            messagebox.showwarning("Falta origen", "Seleccioná una carpeta con imágenes.")
            return

        carpeta_origen = Path(origen_str)
        carpeta_salida = Path(salida_str) if salida_str else carpeta_origen / "sin_fondo"

        archivos = listar_imagenes(carpeta_origen)
        if not archivos:
            messagebox.showinfo(
                "Sin imágenes",
                "No se encontraron imágenes (.png, .jpg, .jpeg, .webp, .bmp) en la carpeta.",
            )
            return

        self.procesando = True
        self.btn_procesar.configure(state=tk.DISABLED)
        self.log(f"Iniciando lote de {len(archivos)} imagen(es) hacia '{carpeta_salida}'...")
        self._actualizar_progreso(0, len(archivos), f"Procesando 0/{len(archivos)}...")

        self.hilo_lote = threading.Thread(
            target=self._ejecutar_lote,
            args=(archivos, carpeta_salida),
            daemon=True,
        )
        self.hilo_lote.start()

    def _ejecutar_lote(self, archivos: list[Path], carpeta_salida: Path) -> None:
        total = len(archivos)
        exitos = 0

        for idx, archivo in enumerate(archivos, start=1):
            destino = carpeta_salida / f"{archivo.stem}_sin_fondo.png"
            ok, detalle = quitar_fondo_archivo(archivo, destino)
            if ok:
                exitos += 1
            self.log(detalle)
            self._actualizar_progreso(idx, total, f"Procesadas {idx}/{total} imágenes...")

        def _finalizar() -> None:
            self.procesando = False
            self.btn_procesar.configure(state=tk.NORMAL)
            self.lbl_estado.config(text=f"Completado: {exitos}/{total} imágenes procesadas.")
            messagebox.showinfo(
                "Proceso terminado",
                f"Se limpiaron {exitos} de {total} imágenes en:\n{carpeta_salida}",
            )

        self.root.after(0, _finalizar)


if __name__ == "__main__":
    ventana = tk.Tk()
    app = LimpiadorFondosApp(ventana)
    ventana.mainloop()