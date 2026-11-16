"""
Kate Crosthwaite · 8-1009-1386
ValidacionAcademicaService (M4, CU-03): valida o rechaza solicitudes según seis requisitos académicos.
"""
from ..dominio.errores import ErrorNegocio, NoEncontrado
from ..dominio.estados import EstadoSolicitud
from ..infraestructura.db import transaccion
from .academico import consultar_con_limite

MSG_FE1 = "Debe seleccionar un estado para todos los requisitos."
MSG_FE2 = ("No es posible validar la solicitud mientras existan requisitos pendientes o no cumplidos. "
           "Registre una observación y guarde el borrador, o rechace la solicitud.")
MSG_RECHAZO = "Debe registrar una observación que justifique el rechazo."


class ValidacionAcademicaService:
    def __init__(self, conn, repo, solicitudes, puerto_academico, historial, autorizacion):
        self.conn = conn
        self.repo = repo
        self.solicitudes = solicitudes
        self.puerto = puerto_academico
        self.historial = historial
        self.autorizacion = autorizacion

    def listar_pendientes(self, usuario):
        self.autorizacion.exigir_acceso(usuario, None, "listar_validacion")
        return self.repo.listar_pendientes()

    def abrir_validacion(self, usuario, solicitud_id):
        s = self._solicitud_pendiente(usuario, solicitud_id)
        info = self._consultar(s.cedula)
        return s, self._validacion_vigente(s, usuario), info

    def guardar_borrador(self, usuario, solicitud_id, estados, observacion):
        s = self._solicitud_pendiente(usuario, solicitud_id)
        v = self._validacion_vigente(s, usuario)
        self._aplicar(v, estados, observacion)
        with transaccion(self.conn):
            self.repo.guardar(v)
        return v

    def validar(self, usuario, solicitud_id, estados, observacion):
        s = self._solicitud_pendiente(usuario, solicitud_id)
        v = self._validacion_vigente(s, usuario)
        self._aplicar(v, estados, observacion)
        if not v.todos_evaluados():
            raise ErrorNegocio(MSG_FE1, {f"req_{r.item_id}" for r in v.requisitos if not r.estado})
        if not v.todos_cumplen():
            raise ErrorNegocio(MSG_FE2, {f"req_{r.item_id}" for r in v.requisitos if r.estado != "CUMPLE"})
        info = self._consultar(s.cedula)
        with transaccion(self.conn):
            v.finalizar("VALIDADA", info.a_json())
            self.repo.guardar(v)
            s.cambiar_estado(EstadoSolicitud.REQUISITOS_VALIDADOS, usuario.rol)
            self.solicitudes.guardar(s)
            self.historial.registrar(s, usuario, "Requisitos académicos validados", "Requisitos validados",
                                     f"Validación digital {v.codigo_validacion_digital}")
        return v

    def rechazar(self, usuario, solicitud_id, observacion, estados=None):
        s = self._solicitud_pendiente(usuario, solicitud_id)
        if not (observacion or "").strip():
            raise ErrorNegocio(MSG_RECHAZO, {"observacion"})
        v = self._validacion_vigente(s, usuario)
        self._aplicar(v, estados or {}, observacion)
        with transaccion(self.conn):
            v.finalizar("RECHAZADA")
            self.repo.guardar(v)
            s.cambiar_estado(EstadoSolicitud.RECHAZADA, usuario.rol)
            self.solicitudes.guardar(s)
            self.historial.registrar(s, usuario, "Solicitud rechazada en la validación académica", "Rechazada", v.observacion)
        return v

    def _solicitud_pendiente(self, usuario, solicitud_id):
        s = self.solicitudes.buscar_por_id(solicitud_id)
        if s is None:
            raise NoEncontrado("La solicitud no existe.")
        self.autorizacion.exigir_acceso(usuario, s, "validar")
        if s.estado != EstadoSolicitud.PENDIENTE_VALIDACION:
            raise ErrorNegocio("La solicitud ya no está pendiente de validación.")
        return s

    def _validacion_vigente(self, s, usuario):
        v = self.repo.buscar_por_solicitud(s.id)
        if v is None or v.estado == "FINALIZADA":
            return self.repo.nueva(s.id, usuario.id)
        v.secretaria_id = usuario.id
        return v

    @staticmethod
    def _aplicar(v, estados, observacion):
        for requisito_id, estado in estados.items():
            v.establecer_estado(requisito_id, estado)
        v.observacion = (observacion or "").replace("\r\n", "\n").strip()

    def _consultar(self, cedula):
        return consultar_con_limite(self.puerto, cedula)
