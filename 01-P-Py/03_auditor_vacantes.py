# Este sistema lo diseñe para auditar vacantes de ConquerBlocks 
# y generar un Excel con tres cuadros: activas, falsas activas y errores de sitio web, 
# encontrar realmente las vacantes que si estan activas.

# INPORTAMOS LIBRERIAS.
from pathlib import Path
import re
from urllib.parse import unquote, urlparse
import unicodedata
import requests
from bs4 import BeautifulSoup
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

# ==============================================================================
# 1. CONFIGURACIÓN PRINCIPAL
# ==============================================================================
URL_PORTAL = "https://junior-offers.conquerblocks.com/"

# True: intenta primero una consulta HTTP rápida antes de abrir Chromium.
# False: abre todas las ofertas directamente con Playwright.
MODO_RAPIDO_HIBRIDO = True

FRASES_BAJA = [
    # Español
    "ya no se aceptan solicitudes",
    "no se aceptan solicitudes",
    "no se aceptan mas postulaciones",
    "la convocatoria ha terminado",
    "la convocatoria a terminado",
    "vacante ya no esta disponible",
    "esta vacante ya no esta disponible",
    "vacante ya finalizo",
    "vacante ya finaliso",
    "oferta cerrada",
    "oferta expirada",
    "esta pagina no se ha encontrado",
    "pagina no encontrada",
    "puesto cubierto",
    # Inglés
    "this job is closed",
    "no longer accepting applications",
    "no longer available",
    "job is closed",
    "job has expired",
    "position has been filled",
    "page not found",
]

URLS_BAJA = ("/closedjob", "job-closed", "not-found", "/404")

PAISES_LATAM = (
    "argentina", "brasil", "brazil", "mexico", "méxico", "colombia",
    "chile", "peru", "perú", "uruguay", "paraguay", "bolivia",
    "ecuador", "costa rica", "panama", "panamá", "latam", "latinoamerica",
)

PAISES_EUROPA = (
    "espana", "españa", "alemania", "germany", "francia", "france",
    "italia", "italy", "portugal", "reino unido", "uk", "united kingdom",
    "irlanda", "ireland", "paises bajos", "países bajos", "netherlands",
    "belgica", "bélgica", "belgium", "suiza", "switzerland", "austria",
    "polonia", "poland", "suecia", "sweden", "noruega", "norway", "europa",
)


# ==============================================================================
# 2. UTILIDADES DE TEXTO, REGIÓN Y DETECCIÓN DE ESTADO
# ==============================================================================
def normalizar_texto(texto: str) -> str:
    """Convierte a minúsculas, quita tildes y limpia espacios repetidos."""
    texto = texto.lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(ch for ch in texto if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", texto).strip()


def resumir_error_red(mensaje: str) -> str:
    """Resume mensajes técnicos largos en una causa corta y legible."""
    m = mensaje.lower()
    if "err_cert_" in m or "certificate" in m:
        return "Error de certificado SSL"
    if "interrupted by another navigation" in m:
        return "Navegación interrumpida por redirección"
    if "err_name_not_resolved" in m:
        return "Dominio no encontrado (DNS)"
    return "Error de conexión"


def titulo_desde_url(url: str) -> str:
    """Si la tarjeta no da buen título, lo construye desde el final de la URL."""
    path = unquote(urlparse(url).path).strip("/")
    if not path:
        return url
    ultimo_tramo = path.split("/")[-1]
    ultimo_tramo = re.sub(r"^\d+[-_]", "", ultimo_tramo)
    limpio = re.sub(r"[-_]+", " ", ultimo_tramo).strip()
    return limpio.title()[:100] if limpio else url[:100]


def detectar_region(texto_tarjeta: str, url: str) -> str:
    """Detecta si la vacante es LATAM o EUROPA según la tarjeta o la URL."""
    combinado = normalizar_texto(f"{texto_tarjeta} {url}")
    if re.search(r"\beuropa\b", combinado) or any(re.search(rf"\b{re.escape(p)}\b", normalizar_texto(p)) and re.search(rf"\b{re.escape(normalizar_texto(p))}\b", combinado) for p in PAISES_EUROPA):
        return "EUROPA"
    if re.search(r"\blatam\b", combinado) or any(re.search(rf"\b{re.escape(normalizar_texto(p))}\b", combinado) for p in PAISES_LATAM):
        return "LATAM"
    return "GENERAL / NO ESPECIFICADA"


def analizar_contenido(texto_visible: str, url_final: str, status_code: int | None) -> tuple[str, str] | None:
    """Evalúa estado HTTP, URL final y texto visible para detectar vacantes caídas."""
    if status_code in (404, 410):
        return "CAIDA", f"Respuesta HTTP {status_code}"

    url_lower = url_final.lower()
    for patron in URLS_BAJA:
        if patron in url_lower:
            return "CAIDA", f"Redirigida a cierre ({patron})"

    texto_norm = normalizar_texto(texto_visible)
    for frase in FRASES_BAJA:
        if frase in texto_norm:
            return "CAIDA", f"Mensaje detectado: '{frase}'"

    if len(texto_norm) >= 150:
        return "ACTIVA", "Activa y sin señales de cierre"

    return None


def chequeo_rapido_http(url: str) -> tuple[str, str] | None:
    """Chequeo veloz por requests; devuelve None si necesita navegador completo."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        )
    }
    try:
        resp = requests.get(url, headers=headers, timeout=6, allow_redirects=True)
    except Exception:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    texto = soup.get_text(" ", strip=True)

    resultado = analizar_contenido(texto, resp.url, resp.status_code)
    if resultado and resultado[0] == "ACTIVA" and len(normalizar_texto(texto)) < 400:
        return None
    return resultado


def evaluar_con_navegador(pagina, url: str) -> tuple[str, str]:
    """Abre la vacante en Chromium y analiza el contenido final cargado."""
    try:
        resp = pagina.goto(url, wait_until="domcontentloaded", timeout=15000)
        pagina.wait_for_timeout(1800)
    except PlaywrightTimeout:
        return "ERROR_WEB", "Tiempo de espera agotado al cargar"
    except Exception as err:
        return "ERROR_WEB", resumir_error_red(str(err))

    status = resp.status if resp else None
    try:
        texto_body = pagina.inner_text("body")
    except Exception:
        texto_body = ""

    evaluacion = analizar_contenido(texto_body, pagina.url, status)
    if evaluacion:
        return evaluacion

    if len(normalizar_texto(texto_body)) == 0:
        return "ERROR_WEB", "Pantalla sin texto visible (posible bloqueo o carga JS)"

    return "ERROR_WEB", "Poco texto visible; conviene revisar a mano"


def evaluar_vacante(pagina, url: str) -> tuple[str, str]:
    """Evalúa una vacante usando el modo configurado."""
    if MODO_RAPIDO_HIBRIDO:
        rapido = chequeo_rapido_http(url)
        if rapido is not None:
            return rapido
    return evaluar_con_navegador(pagina, url)


# ==============================================================================
# 3. FILTRO FIJO (LISTA > ACTIVAS > TODOS > TODAS) Y EXTRACCIÓN DE VACANTES
# ==============================================================================
def obtener_total_en_pantalla(pagina) -> int | None:
    """Lee el número N de 'Ofertas (N)' que muestra la web."""
    loc = pagina.locator("text=/Ofertas\\s*\\(\\d+\\)/i").first
    if loc.count() == 0:
        return None
    match = re.search(r"\((\d+)\)", loc.inner_text())
    return int(match.group(1)) if match else None


def clic_en_grupo(pagina, etiquetas_del_grupo: tuple[str, ...], objetivo: str) -> bool:
    """Hace clic en 'objetivo' dentro del grupo de filtros correspondiente."""
    grupo = pagina.locator("div")
    for etq in etiquetas_del_grupo:
        grupo = grupo.filter(has=pagina.get_by_text(re.compile(rf"^\s*{re.escape(etq)}\s*$", re.IGNORECASE)))

    for i in range(grupo.count() - 1, -1, -1):
        cont = grupo.nth(i)
        botones = cont.locator("button, a, div, span").filter(
            has_text=re.compile(rf"^\s*{re.escape(objetivo)}\s*$", re.IGNORECASE)
        )
        for j in range(botones.count()):
            el = botones.nth(j)
            try:
                if el.is_visible() and len(el.inner_text().strip()) <= 20:
                    el.click()
                    pagina.wait_for_timeout(800)
                    return True
            except Exception:
                continue
    return False


def esperar_estabilidad(pagina, esperado: int | None, max_espera_ms: int = 5000) -> int:
    """Espera hasta que la cantidad de enlaces 'Aplicar' coincida o se estabilice."""
    transcurrido = 0
    paso = 250
    ultimo = -1
    estables = 0

    while transcurrido < max_espera_ms:
        actual = pagina.locator("a:has-text('Aplicar')").count()
        if esperado is not None and actual == esperado:
            return actual
        if actual == ultimo and actual > 0:
            estables += 1
            if estables >= 3:
                return actual
        else:
            estables = 0
            ultimo = actual
        pagina.wait_for_timeout(paso)
        transcurrido += paso

    return pagina.locator("a:has-text('Aplicar')").count()


def recolectar_ofertas_activas(pagina) -> list[dict[str, str]]:
    """Aplica LISTA > ACTIVAS > TODOS > TODAS y obtiene título, región y URL."""
    pagina.goto(URL_PORTAL, wait_until="networkidle", timeout=30000)
    pagina.wait_for_timeout(1000)

    clic_en_grupo(pagina, ("LISTA", "POR EMPRESA"), "LISTA")
    clic_en_grupo(pagina, ("ACTIVAS", "INACTIVAS", "TODAS"), "ACTIVAS")
    clic_en_grupo(pagina, ("JUNIOR", "MID", "SENIOR", "TODOS"), "TODOS")
    clic_en_grupo(pagina, ("TODAS", "EUROPA", "LATAM"), "TODAS")

    total_web = obtener_total_en_pantalla(pagina)
    esperar_estabilidad(pagina, total_web)

    links_aplicar = pagina.locator("a:has-text('Aplicar')")
    cantidad = links_aplicar.count()
    print(f"Contador en web: {total_web} | Enlaces 'Aplicar' detectados: {cantidad}")

    ruido = {
        "APLICAR", "ME INTERESA", "☆ ME INTERESA", "JUNIOR", "MID", "SENIOR",
        "TODOS", "LATAM", "EUROPA", "TODAS", "ACTIVA", "INACTIVA"
    }

    ofertas: list[dict[str, str]] = []
    urls_vistas: set[str] = set()

    for i in range(cantidad):
        enlace = links_aplicar.nth(i)
        href = (enlace.get_attribute("href") or "").strip()
        if not href or href in urls_vistas:
            continue
        urls_vistas.add(href)

        nombre = ""
        texto_tarjeta_completo = ""
        for nivel in range(2, 7):
            try:
                texto_anc = enlace.locator(f"xpath=ancestor::*[{nivel}]").inner_text()
            except Exception:
                continue
            lineas = []
            for ln in texto_anc.splitlines():
                limpia = ln.strip()
                if not limpia or limpia.upper() in ruido:
                    continue
                if "€" in limpia or "$" in limpia or " de 202" in limpia.lower():
                    continue
                if limpia not in lineas:
                    lineas.append(limpia)
            if 1 <= len(lineas) <= 4 and sum(len(x) for x in lineas) < 220:
                texto_tarjeta_completo = texto_anc
                nombre = " - ".join(lineas[:2])
                break

        if not nombre:
            nombre = titulo_desde_url(href)

        region = detectar_region(texto_tarjeta_completo, href)
        ofertas.append({
            "nombre": nombre[:120],
            "region": region,
            "url": href,
        })

    return ofertas


# ==============================================================================
# 4. EXPORTACIÓN A EXCEL (.XLSX) EN TRES CUADROS ESTILIZADOS
# ==============================================================================
def _escribir_cuadro(
    ws,
    fila_inicio: int,
    titulo_cuadro: str,
    descripcion_cuadro: str,
    filas: list[dict[str, str]],
    color_banner: str,
    color_encabezado: str,
    color_fila_par: str,
    borde_fino: Border,
    fuente_base: Font,
) -> int:
    """Dibuja un cuadro completo (título, explicación, cabeceras y filas) y devuelve la próxima fila."""
    fill_banner = PatternFill(start_color=color_banner, end_color=color_banner, fill_type="solid")
    fill_cabecera = PatternFill(start_color=color_encabezado, end_color=color_encabezado, fill_type="solid")
    fill_par = PatternFill(start_color=color_fila_par, end_color=color_fila_par, fill_type="solid")
    fill_blanco = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")

    # Banner del cuadro (columnas A a D)
    ws.merge_cells(start_row=fila_inicio, start_column=1, end_row=fila_inicio, end_column=4)
    celda_titulo = ws.cell(row=fila_inicio, column=1, value=titulo_cuadro)
    celda_titulo.font = Font(name="Calibri", size=13, bold=True, color="FFFFFF")
    celda_titulo.fill = fill_banner
    celda_titulo.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[fila_inicio].height = 28

    # Fila de explicación del cuadro
    fila_desc = fila_inicio + 1
    ws.merge_cells(start_row=fila_desc, start_column=1, end_row=fila_desc, end_column=4)
    celda_desc = ws.cell(row=fila_desc, column=1, value=descripcion_cuadro)
    celda_desc.font = Font(name="Calibri", size=10, italic=True, color="374151")
    celda_desc.fill = fill_par
    celda_desc.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True, indent=1)
    ws.row_dimensions[fila_desc].height = 24

    for c in range(1, 5):
        ws.cell(row=fila_inicio, column=c).border = borde_fino
        ws.cell(row=fila_desc, column=c).border = borde_fino

    # Encabezados de columnas
    fila_cab = fila_inicio + 2
    cabeceras = ["Nombre / Título de la vacante", "Región", "Enlace de la vacante", "Detalle / Estado"]
    for idx_col, texto_cab in enumerate(cabeceras, start=1):
        celda = ws.cell(row=fila_cab, column=idx_col, value=texto_cab)
        celda.font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        celda.fill = fill_cabecera
        celda.alignment = Alignment(horizontal="center", vertical="center")
        celda.border = borde_fino
    ws.row_dimensions[fila_cab].height = 23

    # Filas de datos o mensaje vacío
    fila_actual = fila_cab + 1
    if not filas:
        ws.merge_cells(start_row=fila_actual, start_column=1, end_row=fila_actual, end_column=4)
        vacia = ws.cell(row=fila_actual, column=1, value="No hay vacantes en esta categoría.")
        vacia.font = Font(name="Calibri", size=10, italic=True, color="6B7280")
        vacia.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[fila_actual].height = 22
        for c in range(1, 5):
            ws.cell(row=fila_actual, column=c).border = borde_fino
        return fila_actual + 2

    for idx_item, item in enumerate(filas):
        fill_uso = fill_par if idx_item % 2 == 1 else fill_blanco
        valores = [item["nombre"], item["region"], item["url"], item["detalle"]]

        for idx_col, val in enumerate(valores, start=1):
            celda = ws.cell(row=fila_actual, column=idx_col, value=val)
            celda.font = fuente_base
            celda.fill = fill_uso
            celda.border = borde_fino
            if idx_col == 2:
                celda.alignment = Alignment(horizontal="center", vertical="center")
                celda.font = Font(name="Calibri", size=10, bold=True, color="111827")
            else:
                celda.alignment = Alignment(horizontal="left", vertical="center", wrap_text=(idx_col in (1, 3, 4)))

        ws.row_dimensions[fila_actual].height = 26
        fila_actual += 1

    return fila_actual + 2


def exportar_excel_tres_cuadros(ruta_xlsx: Path, resultados: list[dict[str, str]]) -> None:
    """Genera el Excel dividido en 3 cuadros claros con colores, bordes y buena tipografía."""
    activas_ok = [r for r in resultados if r["estado"] == "ACTIVA"]
    falsas_activas = [r for r in resultados if r["estado"] == "CAIDA"]
    errores_sitio = [r for r in resultados if r["estado"] == "ERROR_WEB"]

    wb = Workbook()
    ws = wb.active
    ws.title = "Reporte Vacantes"
    ws.views.sheetView[0].showGridLines = True

    borde_fino = Border(
        left=Side(style="thin", color="D1D5DB"),
        right=Side(style="thin", color="D1D5DB"),
        top=Side(style="thin", color="D1D5DB"),
        bottom=Side(style="thin", color="D1D5DB"),
    )
    fuente_base = Font(name="Calibri", size=10, color="1F2937")

    fila = 1

    # Cuadro 1: Activas y funcionando
    fila = _escribir_cuadro(
        ws=ws,
        fila_inicio=fila,
        titulo_cuadro=f"CUADRO 1: VACANTES ACTIVAS Y FUNCIONANDO ({len(activas_ok)})",
        descripcion_cuadro="Figuran como ACTIVAS en ConquerBlocks y al abrir el enlace se muestran disponibles sin señales de cierre.",
        filas=activas_ok,
        color_banner="1E6B3A",
        color_encabezado="2E8B57",
        color_fila_par="EAF7EE",
        borde_fino=borde_fino,
        fuente_base=fuente_base,
    )

    # Cuadro 2: Marcadas como activas en Conquer pero cerradas / no disponibles
    fila = _escribir_cuadro(
        ws=ws,
        fila_inicio=fila,
        titulo_cuadro=f"CUADRO 2: ACTIVAS EN CONQUER PERO NO ACTIVAS / CERRADAS ({len(falsas_activas)})",
        descripcion_cuadro="Aparecen como ACTIVAS en el portal, pero su página indica que cerraron, no aceptan solicitudes o redirigen a baja.",
        filas=falsas_activas,
        color_banner="9B1C1C",
        color_encabezado="C81E1E",
        color_fila_par="FDE8E8",
        borde_fino=borde_fino,
        fuente_base=fuente_base,
    )

    # Cuadro 3: Vacantes cuyo sitio web da error o no funciona
    _escribir_cuadro(
        ws=ws,
        fila_inicio=fila,
        titulo_cuadro=f"CUADRO 3: VACANTES CON ERROR EN EL SITIO WEB O A REVISAR ({len(errores_sitio)})",
        descripcion_cuadro="Sitios que tardaron demasiado, dieron error de conexión/certificado o cargaron vacíos al momento de comprobar.",
        filas=errores_sitio,
        color_banner="92400E",
        color_encabezado="D97706",
        color_fila_par="FEF3C7",
        borde_fino=borde_fino,
        fuente_base=fuente_base,
    )

    anchos_columnas = {1: 46, 2: 24, 3: 58, 4: 38}
    for col_idx, ancho in anchos_columnas.items():
        ws.column_dimensions[get_column_letter(col_idx)].width = ancho

    ruta_xlsx.parent.mkdir(parents=True, exist_ok=True)
    wb.save(ruta_xlsx)


# ==============================================================================
# 5. EJECUCIÓN PRINCIPAL
# ==============================================================================
def main() -> None:
    salida_xlsx = Path(__file__).resolve().parent / "vacantes_activas_caidas.xlsx"
    resultados: list[dict[str, str]] = []

    with sync_playwright() as p:
        navegador = p.chromium.launch(headless=True)
        contexto = navegador.new_context(locale="es-ES")
        pagina_portal = contexto.new_page()
        pagina_oferta = contexto.new_page()

        print("Aplicando filtro LISTA > ACTIVAS > TODOS > TODAS...")
        ofertas = recolectar_ofertas_activas(pagina_portal)
        total = len(ofertas)
        print(f"Total de ofertas únicas a verificar: {total}\n")

        for idx, of in enumerate(ofertas, start=1):
            estado, detalle = evaluar_vacante(pagina_oferta, of["url"])
            print(f"[{idx}/{total}] [{of['region']}] {estado} -> {of['nombre']} ({detalle})")

            resultados.append({
                "nombre": of["nombre"],
                "region": of["region"],
                "url": of["url"],
                "estado": estado,
                "detalle": detalle,
            })

        navegador.close()

    exportar_excel_tres_cuadros(salida_xlsx, resultados)
    print(f"\nListo. Excel con 3 cuadros generado en:\n{salida_xlsx}")


if __name__ == "__main__":
    main()