"""
Kate Crosthwaite · 8-1009-1386
Fábrica de la aplicación web SGME: configuración, conexión por petición, sesión, CSRF y páginas de error.
"""
import os
import secrets
import time
from datetime import datetime

from flask import Flask, flash, g, render_template, request, session, url_for

from . import config
from .contenedor import Servicios
from .dominio.errores import AccesoDenegado, ErrorNegocio, NoEncontrado
from .dominio.estados import (ETIQUETA_DOCUMENTO, ETIQUETA_ESTADO, ETIQUETA_EVALUACION, ETIQUETA_ROL, Rol,
                              etapas_del_proceso)
from .infraestructura.almacen_archivos import AlmacenArchivos
from .infraestructura.db import conectar, inicializar
from .web.iconos import icono


def _menu(usuario):
    """Opciones de la barra lateral por rol: (texto, url, prefijo de ruta para marcarla como activa)."""
    if usuario is None:
        return []
    opciones = {
        Rol.ESTUDIANTE: [("Inicio", "inicio", url_for("solicitud.inicio"), None),
                         ("Registrar Modalidad de Egreso", "nuevo", url_for("solicitud.registrar"), "/estudiante/solicitud")],
        Rol.SECRETARIA: [("Validar Requisitos Académicos", "validar", url_for("validacion.listar"), "/secretaria")],
        Rol.ASESOR: [("Revisar Modalidad de Egreso", "revisar", url_for("revision.listar"), "/asesor")],
    }.get(usuario.rol, [])
    return [{"texto": t, "icono": i, "url": u, "activo": request.path == u or bool(p and request.path.startswith(p))}
            for t, i, u, p in opciones]


def create_app(ajustes=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=config.SECRET_KEY, DB_PATH=config.DB_PATH, ARCHIVOS_DIR=config.ARCHIVOS_DIR,
        MINUTOS_INACTIVIDAD=config.MINUTOS_INACTIVIDAD, MAX_CONTENT_LENGTH=100 * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")
    app.config.update(ajustes or {})
    app.jinja_env.globals.update(icono=icono, etapas_del_proceso=etapas_del_proceso)
    os.makedirs(os.path.dirname(app.config["DB_PATH"]), exist_ok=True)
    os.makedirs(app.config["ARCHIVOS_DIR"], exist_ok=True)
    conn = conectar(app.config["DB_PATH"])
    inicializar(conn, AlmacenArchivos(app.config["ARCHIVOS_DIR"]))
    conn.close()

    from .web import auth_controller, revision_controller, solicitud_controller, validacion_controller
    for modulo in (auth_controller, solicitud_controller, validacion_controller, revision_controller):
        app.register_blueprint(modulo.bp)

    @app.before_request
    def preparar_peticion():
        if request.endpoint == "static":
            return None
        g.conn = conectar(app.config["DB_PATH"])
        g.servicios = Servicios(g.conn, app.config["ARCHIVOS_DIR"])
        g.usuario = None
        if session.get("uid"):
            if time.time() - session.get("ultima", 0) > app.config["MINUTOS_INACTIVIDAD"] * 60:
                session.clear()
                flash("Su sesión expiró por inactividad. Inicie sesión nuevamente.", "aviso")
            else:
                g.usuario = g.servicios.autenticacion.cargar_usuario(session["uid"])
                if g.usuario is None:
                    session.clear()
                else:
                    session["ultima"] = time.time()
        if request.method == "POST":
            enviado = request.form.get("csrf", "").encode()
            if not secrets.compare_digest(enviado, session.get("csrf", "-").encode()):
                return render_template("error.html", titulo="Solicitud no válida",
                                       mensaje="El formulario expiró o no es válido. Recargue la página e intente nuevamente."), 400
        return None

    @app.teardown_request
    def cerrar_conexion(_error):
        conn = g.pop("conn", None)
        if conn is not None:
            conn.close()

    @app.after_request
    def cabeceras(respuesta):
        respuesta.headers["X-Content-Type-Options"] = "nosniff"
        respuesta.headers["Cache-Control"] = "no-store"
        return respuesta

    @app.context_processor
    def contexto_plantillas():
        def csrf():
            if "csrf" not in session:
                session["csrf"] = secrets.token_hex(16)
            return session["csrf"]
        usuario = g.get("usuario")
        return dict(csrf=csrf, usuario=usuario, menu=_menu(usuario), ETIQUETA_ESTADO=ETIQUETA_ESTADO,
                    ETIQUETA_EVAL=ETIQUETA_EVALUACION, ETIQUETA_ROL=ETIQUETA_ROL, ETIQUETA_DOC=ETIQUETA_DOCUMENTO,
                    SEMESTRE=config.SEMESTRE_ACADEMICO)

    @app.template_filter("fecha")
    def filtro_fecha(valor):
        if not valor:
            return "—"
        try:
            return datetime.strptime(valor, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
        except ValueError:
            return valor

    @app.errorhandler(403)
    @app.errorhandler(AccesoDenegado)
    def prohibido(_error):
        return render_template("error.html", titulo="Acceso denegado",
                               mensaje="No tiene permisos para acceder a este recurso. El intento quedó registrado."), 403

    @app.errorhandler(404)
    @app.errorhandler(NoEncontrado)
    def no_encontrado(_error):
        return render_template("error.html", titulo="No encontrado", mensaje="El recurso solicitado no existe."), 404

    @app.errorhandler(ErrorNegocio)
    def error_de_negocio(error):
        return render_template("error.html", titulo="No fue posible completar la acción", mensaje=error.mensaje), 400

    @app.errorhandler(413)
    def demasiado_grande(_error):
        return render_template("error.html", titulo="Carga demasiado grande",
                               mensaje="El tamaño total de la carga supera el límite permitido. Cada archivo puede pesar hasta 20 MB."), 413

    return app
