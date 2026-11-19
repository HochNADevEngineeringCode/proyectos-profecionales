#INPORTAMOS NUESTRAS LIBRIAS NESESARIAS.
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
import qrcode

#CREAMOS NUESTRA FUNCION QUE VA A GENERAR EL CODIGO QR.
def generar_qr(contenido: str, ruta_salida: Path, color_relleno: str = "black", color_fondo: str = "white") -> Path:
    """Genera y guarda un código QR en formato PNG."""
    if not contenido.strip():
        raise ValueError("El contenido del QR no puede estar vacío.")

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(contenido.strip())
    qr.make(fit=True)

    imagen = qr.make_image(fill_color=color_relleno, back_color=color_fondo)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    imagen.save(ruta_salida)
    return ruta_salida

#CREAMOS NUESTRA FUNCION QUE VA A INICIAR NUESTRA APP.
def iniciar_app() -> None:
    ventana = tk.Tk()
    ventana.title("Generador de QR Inteligente")
    ventana.geometry("420x210")
    ventana.resizable(False, False)

    tk.Label(ventana, text="Texto, enlace o datos para el QR:", font=("Segoe UI", 10)).pack(pady=(15, 5))

    entrada = tk.Entry(ventana, width=48, font=("Segoe UI", 10))
    entrada.pack(pady=5)
    entrada.focus()
    #CREAMOS NUESTRA FUNCION QUE VA A GUARDAR EL CODIGO QR.
    def al_guardar() -> None:
        texto = entrada.get()
        archivo = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("Imagen PNG", "*.png")],
            initialfile="codigo_qr.png",
            title="Guardar código QR",
        )
        if not archivo:
            return

        try:
            ruta = generar_qr(texto, Path(archivo))
            messagebox.showinfo("Listo", f"QR guardado en:\n{ruta}")
        except ValueError as err:
            messagebox.showwarning("Atención", str(err))
        except Exception as err:
            messagebox.showerror("Error", f"No se pudo generar el QR:\n{err}")

    tk.Button(
        ventana,
        text="Generar y Guardar PNG",
        command=al_guardar,
        font=("Segoe UI", 10, "bold"),
        padx=14,
        pady=8,
    ).pack(pady=18)

    ventana.mainloop()

# CREAMOS NUESTRA FUNCION PRINCIPAL QUE VA A INICIAR NUESTRA APP.
if __name__ == "__main__":
    iniciar_app()