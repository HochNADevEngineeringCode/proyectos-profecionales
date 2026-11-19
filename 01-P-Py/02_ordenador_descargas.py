#IMPORTAMOS NUESTRAS LIBRERIAS NESESARIAS.
from datetime import datetime
import logging
from pathlib import Path
import shutil
import time
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

#DEFINIMOS LAS EXTENSIONES Y SUS CATEGORIAS.
EXTENSIONES_DESTINO: dict[str, str] = {
    ".pdf": "Documentos",
    ".doc": "Documentos",
    ".docx": "Documentos",
    ".xls": "Documentos",
    ".xlsx": "Documentos",
    ".txt": "Documentos",
    ".png": "Imagenes",
    ".jpg": "Imagenes",
    ".jpeg": "Imagenes",
    ".webp": "Imagenes",
    ".mp3": "Audios",
    ".wav": "Audios",
    ".ogg": "Audios",
    ".mp4": "Videos",
    ".mkv": "Videos",
    ".zip": "Comprimidos",
    ".rar": "Comprimidos",
    ".7z": "Comprimidos",
    ".exe": "Instaladores",
    ".msi": "Instaladores",
}
#DEFINIMOS LAS EXTENSIONES TEMPORALES QUE NO VAMOS A MOVER.
ARCHIVOS_TEMPORALES = {".tmp", ".crdownload", ".part"}

#CREAMOS NUESTRA FUNCION QUE VA A CONFIGURAR NUESTRO LOGGER.
def configurar_logger(ruta_log: Path) -> logging.Logger:
    ruta_log.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("ordenador_descargas")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formato = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    handler_archivo = logging.FileHandler(ruta_log, encoding="utf-8")
    handler_archivo.setFormatter(formato)

    handler_consola = logging.StreamHandler()
    handler_consola.setFormatter(formato)

    logger.addHandler(handler_archivo)
    logger.addHandler(handler_consola)
    return logger

#CREAMOS NUESTRA FUNCION QUE VA A RESOLVER LA RUTA UNICA.
def resolver_ruta_unica(destino: Path) -> Path:
    """Si ya existe un archivo con ese nombre, agrega un timestamp corto."""
    if not destino.exists():
        return destino
    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    return destino.with_name(f"{destino.stem}_{marca}{destino.suffix}")

#CREAMOS NUESTRA CLASE QUE VA A MANEJAR LOS EVENTOS DE DESCARGA.
class ManejadorDescargas(FileSystemEventHandler):
    def __init__(self, carpeta_vigilada: Path, carpeta_base_destino: Path, logger: logging.Logger) -> None:
        self.carpeta_vigilada = carpeta_vigilada
        self.carpeta_base_destino = carpeta_base_destino
        self.logger = logger
#CREAMOS NUESTRA FUNCION QUE VA A MANEJAR EL EVENTO DE CREACION DE ARCHIVOS.
    def on_created(self, event) -> None:
        if event.is_directory:
            return
        self._procesar_archivo(Path(event.src_path))
#CREAMOS NUESTRA FUNCION QUE VA A MANEJAR EL EVENTO DE MOVIMIENTO DE ARCHIVOS.
    def on_moved(self, event) -> None:
        """Útil cuando el navegador renombra un archivo .crdownload al terminar."""
        if event.is_directory:
            return
        self._procesar_archivo(Path(event.dest_path))
#CREAMOS NUESTRA FUNCION QUE VA A PROCESAR EL ARCHIVO.
    def _procesar_archivo(self, archivo: Path) -> None:
        if not archivo.exists():
            return

        extension = archivo.suffix.lower()
        if extension in ARCHIVOS_TEMPORALES:
            return

        #Pequeña pausa por si el archivo todavía se está escribiendo en disco.
        time.sleep(0.5)

        categoria = EXTENSIONES_DESTINO.get(extension, "Otros")
        carpeta_categoria = self.carpeta_base_destino / categoria
        carpeta_categoria.mkdir(parents=True, exist_ok=True)

        destino_final = resolver_ruta_unica(carpeta_categoria / archivo.name)
        try:
            shutil.move(str(archivo), str(destino_final))
            self.logger.info("Movido: '%s' -> '%s'", archivo.name, destino_final)
        except PermissionError:
            self.logger.warning("Archivo en uso, reintentar luego: '%s'", archivo.name)
        except Exception as err:
            self.logger.error("Error moviendo '%s': %s", archivo.name, err)

#CREAMOS NUESTRA FUNCION QUE VA A INICIAR LA VIGILANCIA DE LA CARPETA.
def iniciar_vigilancia(carpeta_vigilada: Path, carpeta_destino: Path, log_path: Path) -> None:
    logger = configurar_logger(log_path)
    carpeta_vigilada.mkdir(parents=True, exist_ok=True)
    carpeta_destino.mkdir(parents=True, exist_ok=True)

    evento_handler = ManejadorDescargas(carpeta_vigilada, carpeta_destino, logger)
    observador = Observer()
    observador.schedule(evento_handler, str(carpeta_vigilada), recursive=False)
    observador.start()

    logger.info("Vigilando '%s' -> organizando en '%s'", carpeta_vigilada, carpeta_destino)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Deteniendo vigilante por solicitud del usuario...")
        observador.stop()
    observador.join()

#CREAMOS NUESTRA FUNCION PRINCIPAL DE ACTIVACION DEL SISTEMA.
if __name__ == "__main__":
    descargas = Path.home() / "Downloads"
    # POR SEGURIDAD CREAMOS UNA CARPETA DE PRUEBAS EN LA DE DESCARGAS PARA NO MOVER ARCHIVOS REALES (esto se puede quitar a gusto).
    carpeta_prueba = Path.home() / "Downloads" / "Pruebas_Ordenador"
    salida_organizada = Path.home() / "Downloads" / "Organizados"
    archivo_log = Path(__file__).resolve().parent / "logs" / "ordenador.log"

    iniciar_vigilancia(carpeta_prueba, salida_organizada, archivo_log)