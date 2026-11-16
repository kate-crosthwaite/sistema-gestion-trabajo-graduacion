"""
Kate Crosthwaite · 8-1009-1386
AutorizacionService (M1): control de acceso centralizado por rol y por solicitud (ADR-004, RNF-01 y RNF-02).
"""
from ..dominio.errores import AccesoDenegado
from ..dominio.estados import EstadoSolicitud as E
from ..dominio.estados import Rol

PERMISOS = {
    Rol.ESTUDIANTE: {"registrar", "editar", "ver", "ver_documento"},
    Rol.SECRETARIA: {"listar_validacion", "validar", "ver", "ver_documento"},
    Rol.ASESOR: {"listar_revision", "revisar", "ver", "ver_documento"},
    Rol.JEFE: {"ver", "ver_documento"},
    Rol.AUTORIDAD: {"ver", "ver_documento"},
}
_NO_VISIBLES_ASESOR = (E.BORRADOR, E.PENDIENTE_VALIDACION)
_VISIBLES_JEFE = (E.REVISION_ASESOR_APROBADA, E.APROBADA_DEPARTAMENTO, E.CORRECCIONES_SOLICITADAS, E.RECHAZADA, E.APROBADA)
_VISIBLES_AUTORIDAD = (E.APROBADA_DEPARTAMENTO, E.RECHAZADA, E.APROBADA)


class AutorizacionService:
    def __init__(self, conn, historial):
        self.conn = conn
        self.historial = historial

    def verificar_rol(self, usuario, roles, ruta="acceso_modulo"):
        permitido = not roles or (usuario is not None and usuario.rol in roles)
        if not permitido:
            self.historial.registrar_acceso_denegado(usuario, None, ruta)
        return permitido

    def verificar_acceso(self, usuario, solicitud, accion):
        permitido = self._permitido(usuario, solicitud, accion)
        if not permitido:
            self.historial.registrar_acceso_denegado(usuario, solicitud.id if solicitud else None, accion)
        return permitido

    def exigir_acceso(self, usuario, solicitud, accion):
        if not self.verificar_acceso(usuario, solicitud, accion):
            raise AccesoDenegado("No tiene permisos para realizar esta acción.")

    @staticmethod
    def _permitido(u, s, accion):
        if u is None or not u.habilitado or accion not in PERMISOS.get(u.rol, ()):
            return False
        if s is None:
            return True
        if u.rol == Rol.ESTUDIANTE:
            return s.es_propietario(u) and (accion != "editar" or s.estado == E.BORRADOR)
        if u.rol == Rol.SECRETARIA:
            return s.estado != E.BORRADOR
        if u.rol == Rol.ASESOR:
            return s.asesor_id == u.id and s.estado not in _NO_VISIBLES_ASESOR
        if u.rol == Rol.JEFE:
            return s.departamento == u.departamento and s.estado in _VISIBLES_JEFE
        if u.rol == Rol.AUTORIDAD:
            return s.facultad_id == u.facultad_id and s.estado in _VISIBLES_AUTORIDAD
        return False
