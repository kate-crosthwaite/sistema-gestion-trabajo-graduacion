"""
Kate Crosthwaite · 8-1009-1386
Punto de entrada del SGME: inicia el servidor local y abre el navegador en la pantalla de inicio de sesión.
Uso: python run.py  (con --reiniciar se restauran los datos de demostración).
"""
import logging
import shutil
import sys
import threading
import webbrowser

from werkzeug.serving import make_server

from sgme import config, create_app

DIRECCION, PUERTO = "127.0.0.1", 8000


def main():
    if "--reiniciar" in sys.argv:
        shutil.rmtree(config.DATA_DIR, ignore_errors=True)
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    servidor = make_server(DIRECCION, PUERTO, create_app(), threaded=True)
    threading.Timer(1.0, lambda: webbrowser.open(f"http://{DIRECCION}:{PUERTO}/")).start()
    servidor.serve_forever()


if __name__ == "__main__":
    main()
