"""
Kate Crosthwaite · 8-1009-1386
Utilidades de la capa de presentación: decorador de acceso por rol (RNF-01) y errores que no deben capturarse.
"""
from functools import wraps

from flask import abort, g, redirect, request, url_for

from ..dominio.errores import AccesoDenegado, NoEncontrado

PROPAGAR = (AccesoDenegado, NoEncontrado)


def requiere_rol(*roles):
    """Exige sesión iniciada y, si se indican roles, que el usuario pertenezca a alguno de ellos."""
    def decorador(vista):
        @wraps(vista)
        def interior(*args, **kwargs):
            if g.usuario is None:
                return redirect(url_for("auth.login"))
            if not g.servicios.autorizacion.verificar_rol(g.usuario, roles, request.path):
                abort(403)
            return vista(*args, **kwargs)
        return interior
    return decorador
