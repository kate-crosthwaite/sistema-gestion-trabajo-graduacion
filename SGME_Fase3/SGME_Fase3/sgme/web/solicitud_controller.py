"""
Kate Crosthwaite · 8-1009-1386
SolicitudController (CU-02): portal del estudiante para registrar, guardar borrador, enviar y consultar solicitudes.
"""
from flask import Blueprint, flash, g, redirect, render_template, request, send_file, url_for

from ..dominio.errores import ErrorNegocio
from ..dominio.estados import Rol
from . import PROPAGAR, requiere_rol

bp = Blueprint("solicitud", __name__)

MIME = {"pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}


@bp.route("/estudiante")
@requiere_rol(Rol.ESTUDIANTE)
def inicio():
    return render_template("solicitud_inicio.html", solicitudes=g.servicios.solicitudes.listar_de_estudiante(g.usuario))


@bp.route("/estudiante/solicitud/nueva", methods=["GET", "POST"], defaults={"solicitud_id": None})
@bp.route("/estudiante/solicitud/<int:solicitud_id>/editar", methods=["GET", "POST"])
@requiere_rol(Rol.ESTUDIANTE)
def registrar(solicitud_id):
    servicio = g.servicios.solicitudes
    es_envio = request.method == "POST"
    s = servicio.armar_solicitud(g.usuario, solicitud_id, request.form if es_envio else None)
    campos_error, mensajes_doc = set(), {}
    if es_envio:
        archivos = {int(k[4:]): f for k, f in request.files.items()
                    if k.startswith("doc_") and k[4:].isdigit() and f.filename}
        try:
            s, errores = servicio.guardar_borrador(g.usuario, s, archivos)
            nombres = {d.requerido_id: d.nombre for d in s.documentos}
            for requerido_id, mensaje in errores:
                mensajes_doc[requerido_id] = mensaje
                campos_error.add(f"doc_{requerido_id}")
                flash(f"{nombres.get(requerido_id, 'Documento')}: {mensaje}", "error")
            if request.form.get("accion") == "enviar":
                if not errores:
                    servicio.enviar(g.usuario, s.id)
                    flash("La solicitud fue registrada correctamente y quedó en estado «Pendiente de validación».", "exito")
                    return redirect(url_for("solicitud.inicio"))
            else:
                flash("El borrador se guardó correctamente.", "exito")
                return redirect(url_for("solicitud.registrar", solicitud_id=s.id))
        except PROPAGAR:
            raise
        except ErrorNegocio as e:
            flash(e.mensaje, "error")
            campos_error |= e.campos
    actuales = {d.requerido_id: {"estado": d.estado, "archivo": d.archivo.nombre_original if d.archivo else ""}
                for d in s.documentos}
    return render_template("solicitud_form.html", s=s, cat=servicio.catalogos(), campos_error=campos_error,
                           actuales=actuales, mensajes_doc=mensajes_doc,
                           de_cuenta=servicio.campos_de_cuenta(g.usuario),
                           academica=servicio.informacion_academica(g.usuario))


@bp.route("/solicitud/<int:solicitud_id>")
@requiere_rol()
def detalle(solicitud_id):
    s, historial = g.servicios.solicitudes.detalle(g.usuario, solicitud_id)
    return render_template("solicitud_detalle.html", s=s, historial=historial)


@bp.route("/documento/<int:archivo_id>")
@requiere_rol()
def documento(archivo_id):
    archivo, ruta = g.servicios.documentos.obtener_archivo(g.usuario, archivo_id)
    return send_file(ruta, mimetype=MIME[archivo.formato], as_attachment=False, download_name=archivo.nombre_original)
