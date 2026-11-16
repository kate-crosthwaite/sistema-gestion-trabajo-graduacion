"""
Kate Crosthwaite · 8-1009-1386
Conexión SQLite, esquema relacional con restricciones, historial de solo inserción y control de transacciones.
"""
import sqlite3
from contextlib import contextmanager

from .. import config

ESQUEMA = """
CREATE TABLE IF NOT EXISTS facultad (id INTEGER PRIMARY KEY, nombre TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS carrera (
    id INTEGER PRIMARY KEY, nombre TEXT NOT NULL, departamento TEXT NOT NULL,
    facultad_id INTEGER NOT NULL REFERENCES facultad(id));
CREATE TABLE IF NOT EXISTS usuario (
    id INTEGER PRIMARY KEY, cedula TEXT NOT NULL UNIQUE, nombre_completo TEXT NOT NULL,
    correo_institucional TEXT NOT NULL UNIQUE, telefono TEXT,
    rol TEXT NOT NULL CHECK (rol IN ('ESTUDIANTE','ASESOR','JEFE','SECRETARIA','AUTORIDAD')),
    departamento TEXT, facultad_id INTEGER REFERENCES facultad(id), carrera_id INTEGER REFERENCES carrera(id),
    habilitado INTEGER NOT NULL DEFAULT 1, password_hash TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS modalidad (
    id INTEGER PRIMARY KEY, nombre TEXT NOT NULL UNIQUE, habilitada INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS documento_requerido (
    id INTEGER PRIMARY KEY, modalidad_id INTEGER NOT NULL REFERENCES modalidad(id),
    nombre TEXT NOT NULL, descripcion TEXT, obligatorio INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS solicitud (
    id INTEGER PRIMARY KEY, numero TEXT NOT NULL UNIQUE,
    estudiante_id INTEGER NOT NULL REFERENCES usuario(id),
    cedula TEXT, nombre_completo TEXT, correo_institucional TEXT, telefono TEXT,
    facultad_id INTEGER REFERENCES facultad(id), carrera_id INTEGER REFERENCES carrera(id),
    modalidad_id INTEGER REFERENCES modalidad(id), titulo TEXT,
    descripcion TEXT CHECK (length(descripcion) <= 1000),
    asesor_id INTEGER REFERENCES usuario(id),
    estado TEXT NOT NULL CHECK (estado IN ('BORRADOR','PENDIENTE_VALIDACION','REQUISITOS_VALIDADOS',
        'REVISION_ASESOR_APROBADA','APROBADA_DEPARTAMENTO','CORRECCIONES_SOLICITADAS','RECHAZADA','APROBADA')),
    estado_origen_correccion TEXT, fecha_registro TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 1);
CREATE INDEX IF NOT EXISTS ix_solicitud_estado ON solicitud(estado);
CREATE INDEX IF NOT EXISTS ix_solicitud_asesor ON solicitud(asesor_id, estado);
CREATE INDEX IF NOT EXISTS ix_solicitud_estudiante ON solicitud(estudiante_id);
CREATE TABLE IF NOT EXISTS documento_solicitud (
    id INTEGER PRIMARY KEY, solicitud_id INTEGER NOT NULL REFERENCES solicitud(id) ON DELETE CASCADE,
    documento_requerido_id INTEGER NOT NULL REFERENCES documento_requerido(id),
    estado TEXT NOT NULL CHECK (estado IN ('PENDIENTE','CARGADO','OPCIONAL')),
    UNIQUE (solicitud_id, documento_requerido_id));
CREATE TABLE IF NOT EXISTS archivo_documento (
    id INTEGER PRIMARY KEY,
    documento_solicitud_id INTEGER NOT NULL REFERENCES documento_solicitud(id) ON DELETE CASCADE,
    nombre_original TEXT NOT NULL, formato TEXT NOT NULL, tamano_bytes INTEGER NOT NULL,
    hash_sha256 TEXT NOT NULL, ruta TEXT NOT NULL, version INTEGER NOT NULL,
    vigente INTEGER NOT NULL DEFAULT 1, fecha_carga TEXT NOT NULL,
    UNIQUE (documento_solicitud_id, version));
CREATE TABLE IF NOT EXISTS requisito_academico (id INTEGER PRIMARY KEY, nombre TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS validacion_academica (
    id INTEGER PRIMARY KEY, solicitud_id INTEGER NOT NULL REFERENCES solicitud(id),
    secretaria_id INTEGER NOT NULL REFERENCES usuario(id),
    estado TEXT NOT NULL CHECK (estado IN ('BORRADOR','FINALIZADA')),
    decision TEXT CHECK (decision IN ('VALIDADA','RECHAZADA') OR decision IS NULL),
    observacion TEXT, codigo_validacion_digital TEXT, fecha_validacion TEXT,
    datos_academicos_consultados TEXT);
CREATE TABLE IF NOT EXISTS requisito_validado (
    id INTEGER PRIMARY KEY, validacion_id INTEGER NOT NULL REFERENCES validacion_academica(id) ON DELETE CASCADE,
    requisito_id INTEGER NOT NULL REFERENCES requisito_academico(id),
    estado TEXT CHECK (estado IN ('CUMPLE','PENDIENTE','NO_CUMPLE') OR estado IS NULL),
    UNIQUE (validacion_id, requisito_id));
CREATE TABLE IF NOT EXISTS criterio_revision (id INTEGER PRIMARY KEY, nombre TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS revision_asesor (
    id INTEGER PRIMARY KEY, solicitud_id INTEGER NOT NULL REFERENCES solicitud(id),
    asesor_id INTEGER NOT NULL REFERENCES usuario(id),
    estado TEXT NOT NULL CHECK (estado IN ('BORRADOR','FINALIZADA')),
    decision TEXT CHECK (decision IN ('APROBADA','CORRECCIONES') OR decision IS NULL),
    observaciones TEXT CHECK (length(observaciones) <= 1000), fecha_revision TEXT);
CREATE TABLE IF NOT EXISTS criterio_evaluado (
    id INTEGER PRIMARY KEY, revision_id INTEGER NOT NULL REFERENCES revision_asesor(id) ON DELETE CASCADE,
    criterio_id INTEGER NOT NULL REFERENCES criterio_revision(id),
    estado TEXT CHECK (estado IN ('CUMPLE','PENDIENTE','NO_CUMPLE') OR estado IS NULL),
    UNIQUE (revision_id, criterio_id));
CREATE TABLE IF NOT EXISTS historial_evento (
    id INTEGER PRIMARY KEY, solicitud_id INTEGER NOT NULL REFERENCES solicitud(id),
    usuario_id INTEGER NOT NULL REFERENCES usuario(id), usuario_nombre TEXT NOT NULL, rol TEXT NOT NULL,
    accion TEXT NOT NULL, resultado TEXT, detalle TEXT, fecha TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ix_historial_solicitud ON historial_evento(solicitud_id);
CREATE TRIGGER IF NOT EXISTS historial_sin_update BEFORE UPDATE ON historial_evento
    BEGIN SELECT RAISE(ABORT, 'El historial es de solo inserción'); END;
CREATE TRIGGER IF NOT EXISTS historial_sin_delete BEFORE DELETE ON historial_evento
    BEGIN SELECT RAISE(ABORT, 'El historial es de solo inserción'); END;
CREATE TABLE IF NOT EXISTS acceso_denegado (
    id INTEGER PRIMARY KEY, usuario_id INTEGER NOT NULL, solicitud_id INTEGER, accion TEXT NOT NULL, fecha TEXT NOT NULL);
"""


def conectar(ruta=None):
    conn = sqlite3.connect(ruta or config.DB_PATH, isolation_level=None, check_same_thread=False, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


@contextmanager
def transaccion(conn):
    """Una transacción por caso de uso: estado, datos e historial se guardan juntos o no se guardan (RNF-07)."""
    if conn.in_transaction:
        yield conn
        return
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise


def _migrar(conn):
    """Bases creadas antes de existir la carrera en la cuenta: agrega la columna y asigna la carrera a los estudiantes de demostración."""
    if "carrera_id" in [c["name"] for c in conn.execute("PRAGMA table_info(usuario)")]:
        return
    conn.execute("ALTER TABLE usuario ADD COLUMN carrera_id INTEGER REFERENCES carrera(id)")
    for cedula, carrera in (("8-900-1001", 1), ("8-910-2002", 2), ("8-930-4004", 3), ("8-940-5005", 1)):
        conn.execute("UPDATE usuario SET carrera_id = ? WHERE cedula = ?", [carrera, cedula])


def inicializar(conn, almacen):
    conn.executescript(ESQUEMA)
    _migrar(conn)
    if conn.execute("SELECT COUNT(*) FROM usuario").fetchone()[0] == 0:
        from .datos_demo import cargar
        cargar(conn, almacen)
