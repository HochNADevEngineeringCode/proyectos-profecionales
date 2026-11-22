import json
import re
import threading
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk
from typing import Optional

import requests
from bs4 import BeautifulSoup
from plyer import notification

# ==============================================================================
# CONFIGURACIÓN GLOBAL
# ==============================================================================
ARCHIVO_HISTORIAL = Path(__file__).parent / "historial_precios.json"

HEADERS_HTTP = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
}


# ==============================================================================
# LÓGICA DE LIMPIEZA, SCRAPING Y ALERTAS
# ==============================================================================
def sanear_url(url_cruda: str) -> str:
    """Limpia espacios, comillas o restos de formato Markdown pegados por error."""
    url_limpia = url_cruda.strip().strip('"').strip("'")
    # Si se pegó algo tipo 'https://a.com](https://a.com', nos quedamos con la primera URL
    if "](" in url_limpia:
        url_limpia = url_limpia.split("](", 1)[0]
    return url_limpia.strip()


def limpiar_precio(texto_precio: str) -> Optional[float]:
    """Convierte un texto de moneda (ej: '$ 1.250,50' o '£51.77') a float."""
    solo_numeros = re.sub(r"[^\d.,]", "", texto_precio.strip())
    if not solo_numeros:
        return None

    if "," in solo_numeros and "." in solo_numeros:
        if solo_numeros.rfind(",") > solo_numeros.rfind("."):
            solo_numeros = solo_numeros.replace(".", "").replace(",", ".")
        else:
            solo_numeros = solo_numeros.replace(",", "")
    elif "," in solo_numeros:
        partes = solo_numeros.split(",")
        if len(partes[-1]) in (1, 2):
            solo_numeros = solo_numeros.replace(",", ".")
        else:
            solo_numeros = solo_numeros.replace(",", "")
    elif "." in solo_numeros:
        partes = solo_numeros.split(".")
        if len(partes[-1]) == 3 and len(partes) > 1:
            solo_numeros = solo_numeros.replace(".", "")

    try:
        return float(solo_numeros)
    except ValueError:
        return None


def obtener_precio_actual(url: str, selector_css: str) -> tuple[Optional[float], str]:
    """Descarga la página y extrae el precio según el selector CSS."""
    url_valida = sanear_url(url)
    try:
        respuesta = requests.get(url_valida, headers=HEADERS_HTTP, timeout=15)
        respuesta.raise_for_status()
    except requests.RequestException as error:
        return None, f"Error HTTP ({url_valida}): {error}"

    sopa = BeautifulSoup(respuesta.text, "html.parser")
    elemento = sopa.select_one(selector_css.strip())

    if not elemento:
        return None, f"No se encontró el selector '{selector_css.strip()}' en la página."

    texto_crudo = elemento.get_text(strip=True)
    precio_numerico = limpiar_precio(texto_crudo)

    if precio_numerico is None:
        return None, f"Texto no numérico encontrado: '{texto_crudo}'"

    return precio_numerico, texto_crudo


def enviar_alerta_windows(titulo: str, mensaje: str) -> None:
    """Muestra notificación en el escritorio de Windows."""
    try:
        notification.notify(
            title=titulo,
            message=mensaje,
            app_name="Monitor de Precios Pro",
            timeout=10,
        )
    except Exception:
        pass


def enviar_alerta_discord(webhook_url: str, mensaje: str) -> bool:
    """Envía alerta por Webhook de Discord si se configuró una URL."""
    webhook_limpio = webhook_url.strip()
    if not webhook_limpio:
        return False
    try:
        resp = requests.post(
            webhook_limpio,
            json={"username": "Monitor de Precios Bot", "content": mensaje},
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except requests.RequestException:
        return False


def guardar_historial(url: str, precio: float, objetivo: float, alerta: bool) -> None:
    """Guarda cada lectura en historial_precios.json."""
    registros = []
    if ARCHIVO_HISTORIAL.exists():
        try:
            registros = json.loads(ARCHIVO_HISTORIAL.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            registros = []

    registros.append(
        {
            "fecha_hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "url": sanear_url(url),
            "precio_detectado": precio,
            "precio_objetivo": objetivo,
            "alerta_disparada": alerta,
        }
    )
    ARCHIVO_HISTORIAL.write_text(
        json.dumps(registros, indent=4, ensure_ascii=False), encoding="utf-8"
    )


# ==============================================================================
# INTERFAZ GRÁFICA CON TKINTER
# ==============================================================================
class MonitorPreciosApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Monitor de Precios y Ofertas — 04_monitor_precios.py")
        self.root.geometry("700x540")
        self.root.minsize(640, 480)

        self.monitoreando = False
        self.hilo_monitor: Optional[threading.Thread] = None

        self._construir_interfaz()

    def _construir_interfaz(self) -> None:
        marco_principal = ttk.Frame(self.root, padding=14)
        marco_principal.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            marco_principal,
            text="Monitor de Precios y Ofertas con Alerta",
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor=tk.W, pady=(0, 10))

        # Formulario de configuración
        form = ttk.LabelFrame(marco_principal, text="Configuración del objetivo", padding=10)
        form.pack(fill=tk.X)
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="URL del producto:").grid(row=0, column=0, sticky=tk.W, pady=4, padx=(0, 8))
        self.entry_url = ttk.Entry(form)
        self.entry_url.grid(row=0, column=1, columnspan=3, sticky=tk.EW, pady=4)
        self.entry_url.insert(
            0, "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
        )

        ttk.Label(form, text="Selector CSS:").grid(row=1, column=0, sticky=tk.W, pady=4, padx=(0, 8))
        self.entry_selector = ttk.Entry(form)
        self.entry_selector.grid(row=1, column=1, sticky=tk.EW, pady=4, padx=(0, 12))
        self.entry_selector.insert(0, ".price_color")

        ttk.Label(form, text="Precio máx.:").grid(row=1, column=2, sticky=tk.W, pady=4, padx=(0, 6))
        self.entry_max = ttk.Entry(form, width=14)
        self.entry_max.grid(row=1, column=3, sticky=tk.W, pady=4)
        self.entry_max.insert(0, "60")

        ttk.Label(form, text="Intervalo (seg):").grid(row=2, column=0, sticky=tk.W, pady=4, padx=(0, 8))
        self.entry_intervalo = ttk.Entry(form, width=14)
        self.entry_intervalo.grid(row=2, column=1, sticky=tk.W, pady=4)
        self.entry_intervalo.insert(0, "20")

        ttk.Label(form, text="Webhook Discord:").grid(row=3, column=0, sticky=tk.W, pady=4, padx=(0, 8))
        self.entry_webhook = ttk.Entry(form)
        self.entry_webhook.grid(row=3, column=1, columnspan=3, sticky=tk.EW, pady=4)

        # Botones de acción
        botones = ttk.Frame(marco_principal)
        botones.pack(fill=tk.X, pady=10)

        self.btn_iniciar = ttk.Button(botones, text="Iniciar monitoreo", command=self.iniciar)
        self.btn_iniciar.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_detener = ttk.Button(
            botones, text="Detener", command=self.detener, state=tk.DISABLED
        )
        self.btn_detener.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_limpiar = ttk.Button(botones, text="Limpiar registro", command=self.limpiar_log)
        self.btn_limpiar.pack(side=tk.RIGHT)

        # Consola de actividad
        ttk.Label(marco_principal, text="Registro de actividad:").pack(anchor=tk.W)
        self.txt_log = scrolledtext.ScrolledText(
            marco_principal, height=14, state=tk.DISABLED, font=("Consolas", 9)
        )
        self.txt_log.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

    def log(self, texto: str) -> None:
        """Agrega una línea con hora en la ventana de forma segura entre hilos."""
        def _escribir() -> None:
            hora = datetime.now().strftime("%H:%M:%S")
            self.txt_log.configure(state=tk.NORMAL)
            self.txt_log.insert(tk.END, f"[{hora}] {texto}\n")
            self.txt_log.see(tk.END)
            self.txt_log.configure(state=tk.DISABLED)

        self.root.after(0, _escribir)

    def limpiar_log(self) -> None:
        self.txt_log.configure(state=tk.NORMAL)
        self.txt_log.delete("1.0", tk.END)
        self.txt_log.configure(state=tk.DISABLED)

    def _leer_parametros(self) -> Optional[tuple[str, str, float, int, str]]:
        url = sanear_url(self.entry_url.get())
        selector = self.entry_selector.get().strip()
        webhook = self.entry_webhook.get().strip()

        if not url or not selector:
            messagebox.showwarning("Datos incompletos", "Ingresá la URL y el selector CSS.")
            return None

        try:
            precio_max = float(self.entry_max.get().strip().replace(",", "."))
        except ValueError:
            messagebox.showwarning("Precio inválido", "Ingresá un número válido en Precio máx.")
            return None

        try:
            intervalo = int(self.entry_intervalo.get().strip())
            if intervalo < 5:
                intervalo = 5
        except ValueError:
            messagebox.showwarning(
                "Intervalo inválido", "Ingresá solo números enteros en Intervalo (ej: 20)."
            )
            return None

        return url, selector, precio_max, intervalo, webhook

    def iniciar(self) -> None:
        if self.monitoreando:
            return
        params = self._leer_parametros()
        if not params:
            return

        self.monitoreando = True
        self.btn_iniciar.configure(state=tk.DISABLED)
        self.btn_detener.configure(state=tk.NORMAL)

        url, selector, precio_max, intervalo, webhook = params
        self.log(f"Monitoreo iniciado | Objetivo: ${precio_max:,.2f} | Cada {intervalo}s")

        self.hilo_monitor = threading.Thread(
            target=self._bucle_monitoreo,
            args=(url, selector, precio_max, intervalo, webhook),
            daemon=True,
        )
        self.hilo_monitor.start()

    def detener(self) -> None:
        if not self.monitoreando:
            return
        self.monitoreando = False
        self.btn_iniciar.configure(state=tk.NORMAL)
        self.btn_detener.configure(state=tk.DISABLED)
        self.log("Monitoreo detenido.")

    def _bucle_monitoreo(
        self, url: str, selector: str, precio_max: float, intervalo: int, webhook: str
    ) -> None:
        while self.monitoreando:
            precio, detalle = obtener_precio_actual(url, selector)
            if not self.monitoreando:
                break

            if precio is None:
                self.log(f"[AVISO] {detalle}")
            else:
                en_oferta = precio <= precio_max
                estado = "¡BAJÓ DEL LÍMITE!" if en_oferta else "Por encima del objetivo"
                self.log(f"Precio: ${precio:,.2f} ('{detalle}') -> {estado}")
                guardar_historial(url, precio, precio_max, en_oferta)

                if en_oferta:
                    msg = (
                        f"Precio actual: ${precio:,.2f} (Límite: ${precio_max:,.2f})\n"
                        f"Enlace: {url}"
                    )
                    enviar_alerta_windows("¡Oferta detectada!", msg)
                    if enviar_alerta_discord(webhook, f"🚨 **¡BAJÓ EL PRECIO!**\n{msg}"):
                        self.log("[OK] Alerta enviada a Discord.")

            # Esperar en tramos cortos para responder rápido si apretás "Detener"
            for _ in range(intervalo):
                if not self.monitoreando:
                    break
                time.sleep(1)


if __name__ == "__main__":
    ventana = tk.Tk()
    app = MonitorPreciosApp(ventana)
    ventana.mainloop()