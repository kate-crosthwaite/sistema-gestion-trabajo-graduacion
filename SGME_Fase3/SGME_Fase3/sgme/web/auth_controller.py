"""
Kate Crosthwaite · 8-1009-1386
Controlador de acceso (CU-01): inicio y cierre de sesión, recuperación simulada y redirección según el rol.
"""
import secrets
import time

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for

from ..dominio.errores import ErrorNegocio
from ..dominio.estados import Rol
from . import requiere_rol

bp = Blueprint("auth", __name__)

DESTINO_POR_ROL = {Rol.ESTUDIANTE: "solicitud.inicio", Rol.SECRETARIA: "validacion.listar",
                   Rol.ASESOR: "revision.listar"}


@bp.route("/")
def raiz():
    return redirect(url_for("auth.inicio"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    if g.usuario:
        return redirect(url_for("auth.inicio"))
    if request.method == "POST":
        try:
            usuario = g.servicios.autenticacion.iniciar_sesion(request.form.get("correo"), request.form.get("contrasena"))
        except ErrorNegocio as e:
            flash(e.mensaje, "error")
        else:
            session.clear()
            session.update(uid=usuario.id, ultima=time.time(), csrf=secrets.token_hex(16))
            return redirect(url_for("auth.inicio"))
    return render_template("login.html", correo=request.form.get("correo", ""))


@bp.route("/inicio")
@requiere_rol()
def inicio():
    return redirect(url_for(DESTINO_POR_ROL[g.usuario.rol]))


@bp.route("/salir", methods=["POST"])
def salir():
    session.clear()
    return redirect(url_for("auth.login"))


@bp.route("/recuperar", methods=["GET", "POST"])
def recuperar():
    if request.method == "POST":
        flash("Hemos recibido su solicitud. Si necesita acceso inmediato, comuníquese con Secretaría Académica.", "info")
        return redirect(url_for("auth.login"))
    return render_template("recuperar.html")

