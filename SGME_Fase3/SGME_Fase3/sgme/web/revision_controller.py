"""
Kate Crosthwaite · 8-1009-1386
RevisionController (CU-05): listado de solicitudes asignadas y pantalla de revisión del profesor asesor.
"""
from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from ..dominio.errores import ErrorNegocio
from ..dominio.estados import Rol
from . import PROPAGAR, requiere_rol

bp = Blueprint("revision", __name__)


@bp.route("/asesor")
@requiere_rol(Rol.ASESOR)
def listar():
    return render_template("revision_lista.html", solicitudes=g.servicios.revision.listar_asignadas(g.usuario))


@bp.route("/asesor/revisar/<int:solicitud_id>", methods=["GET", "POST"])
@requiere_rol(Rol.ASESOR)
def revisar(solicitud_id):
    servicio = g.servicios.revision
    estados = {int(k[5:]): v for k, v in request.form.items() if k.startswith("crit_") and k[5:].isdigit()}
    observaciones = request.form.get("observaciones", "")
    campos_error = set()
    if request.method == "POST":
        accion = request.form.get("accion")
        try:
            if accion == "aprobar":
                servicio.aprobar(g.usuario, solicitud_id, estados, observaciones)
                flash("La revisión de la modalidad de egreso fue registrada correctamente.", "exito")
                return redirect(url_for("revision.listar"))
            if accion == "correcciones":
                servicio.solicitar_correcciones(g.usuario, solicitud_id, estados, observaciones)
                flash("Las correcciones fueron solicitadas correctamente.", "exito")
                return redirect(url_for("revision.listar"))
            servicio.guardar_borrador(g.usuario, solicitud_id, estados, observaciones)
            flash("El borrador se guardó correctamente.", "exito")
            return redirect(url_for("revision.revisar", solicitud_id=solicitud_id))
        except PROPAGAR:
            raise
        except ErrorNegocio as e:
            flash(e.mensaje, "error")
            campos_error = e.campos
    try:
        s, r = servicio.abrir_revision(g.usuario, solicitud_id)
    except PROPAGAR:
        raise
    except ErrorNegocio as e:
        flash(e.mensaje, "error")
        return redirect(url_for("revision.listar"))
    if request.method == "POST":
        for criterio_id, estado in estados.items():
            r.evaluar_criterio(criterio_id, estado)
        r.observaciones = observaciones
    return render_template("revisar.html", s=s, r=r, campos_error=campos_error,
                           historial=g.servicios.historial.listar(s.id))
