"""
Kate Crosthwaite · 8-1009-1386
Parámetros de configuración del SGME: rutas de datos, límites de archivos y de sesión.
"""
import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "datos")
DB_PATH = os.path.join(DATA_DIR, "sgme.db")
ARCHIVOS_DIR = os.path.join(DATA_DIR, "archivos")

TAMANO_MAX_BYTES = 20 * 1024 * 1024
FORMATOS_PERMITIDOS = ("pdf", "docx")
MAX_CARACTERES = 1000
DOMINIO_INSTITUCIONAL = "@utp.ac.pa"
MINUTOS_INACTIVIDAD = 20
TIEMPO_LIMITE_CONSULTA_ACADEMICA = 3
SEMESTRE_ACADEMICO = "II Semestre 2026"
SECRET_KEY = os.environ.get("SGME_SECRET_KEY", "sgme-clave-de-demostracion")
