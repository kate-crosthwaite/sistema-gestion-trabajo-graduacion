"""
Kate Crosthwaite · 8-1009-1386
ValidacionController (CU-03): listado de solicitudes pendientes y pantalla de validación académica.
"""
from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from ..dominio.errores import ConsultaNoDisponible, ErrorNegocio
from ..dominio.estados import Rol
from . import PROPAGAR, requiere_rol

bp = Blueprint("validacion", __name__)


@bp.route("/secretaria")
@requiere_rol(Rol.SECRETARIA)
def listar():
    return render_template("validacion_lista.html", solicitudes=g.servicios.validacion.listar_pendientes(g.usuario))


@bp.route("/secretaria/validar/<int:solicitud_id>", methods=["GET", "POST"])
@requiere_rol(Rol.SECRETARIA)
def validar(solicitud_id):
    servicio = g.servicios.validacion
    estados = {int(k[4:]): v for k, v in request.form.items() if k.startswith("req_") and k[4:].isdigit()}
    observacion = request.form.get("observacion", "")
    campos_error = set()
    if request.method == "POST":
        accion = request.form.get("accion")
        try:
            if accion == "validar":
                servicio.validar(g.usuario, solicitud_id, estados, observacion)
                flash("La validación de requisitos académicos ha sido registrada correctamente.", "exito")
                return redirect(url_for("validacion.listar"))
            if accion == "rechazar":
                servicio.rechazar(g.usuario, solicitud_id, observacion, estados)
                flash("La solicitud ha sido rechazada correctamente.", "exito")
                return redirect(url_for("validacion.listar"))
            servicio.guardar_borrador(g.usuario, solicitud_id, estados, observacion)
            flash("El borrador se guardó correctamente.", "exito")
            return redirect(url_for("validacion.validar", solicitud_id=solicitud_id))
        except PROPAGAR:
            raise
        except ConsultaNoDisponible as e:
            flash(e.mensaje, "error")
            return redirect(url_for("validacion.listar"))
        except ErrorNegocio as e:
            flash(e.mensaje, "error")
            campos_error = e.campos
    try:
        s, v, info = servicio.abrir_validacion(g.usuario, solicitud_id)
    except PROPAGAR:
        raise
    except ErrorNegocio as e:
        flash(e.mensaje, "error")
        return redirect(url_for("validacion.listar"))
    if request.method == "POST":
        for requisito_id, estado in estados.items():
            v.establecer_estado(requisito_id, estado)
        v.observacion = observacion
    return render_template("validar.html", s=s, v=v, info=info, campos_error=campos_error,
                           historial=g.servicios.historial.listar(s.id))
