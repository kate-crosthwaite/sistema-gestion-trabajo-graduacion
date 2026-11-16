"""
Kate Crosthwaite · 8-1009-1386
RevisionAsesorService (M5, CU-05): evalúa cinco criterios académicos y aprueba la revisión o solicita correcciones.
"""
from ..dominio.errores import ErrorNegocio, NoEncontrado
from ..dominio.estados import EstadoSolicitud
from ..infraestructura.db import transaccion

MSG_FE2 = "Debe evaluar todos los criterios antes de aprobar la revisión."
MSG_FE2_CORRECCIONES = "Debe evaluar todos los criterios antes de solicitar correcciones."
MSG_FE4 = "No es posible aprobar la revisión mientras existan criterios pendientes o no cumplidos. Solicite correcciones."
MSG_SIN_INCUMPLIMIENTO = "Para solicitar correcciones debe existir al menos un criterio Pendiente o No cumple."
MSG_SIN_OBSERVACION = "Debe registrar las observaciones que justifican las correcciones solicitadas."


class RevisionAsesorService:
    def __init__(self, conn, repo, solicitudes, historial, autorizacion):
        self.conn = conn
        self.repo = repo
        self.solicitudes = solicitudes
        self.historial = historial
        self.autorizacion = autorizacion

    def listar_asignadas(self, usuario):
        self.autorizacion.exigir_acceso(usuario, None, "listar_revision")
        return self.repo.listar_asignadas(usuario.id)

    def abrir_revision(self, usuario, solicitud_id):
        s = self._solicitud_revisable(usuario, solicitud_id)
        return s, self._revision_vigente(s, usuario)

    def guardar_borrador(self, usuario, solicitud_id, estados, observaciones):
        s = self._solicitud_revisable(usuario, solicitud_id)
        r = self._preparar(s, usuario, estados, observaciones)
        with transaccion(self.conn):
            self.repo.guardar(r)
        return r

    def aprobar(self, usuario, solicitud_id, estados, observaciones):
        s = self._solicitud_revisable(usuario, solicitud_id)
        r = self._preparar(s, usuario, estados, observaciones)
        if not r.criterios_evaluados():
            raise ErrorNegocio(MSG_FE2, {f"crit_{c.item_id}" for c in r.criterios if not c.estado})
        if not r.todos_cumplen():
            raise ErrorNegocio(MSG_FE4, {f"crit_{c.item_id}" for c in r.criterios if c.estado != "CUMPLE"})
        with transaccion(self.conn):
            r.finalizar("APROBADA")
            self.repo.guardar(r)
            s.cambiar_estado(EstadoSolicitud.REVISION_ASESOR_APROBADA, usuario.rol)
            self.solicitudes.guardar(s)
            self.historial.registrar(s, usuario, "Revisión del asesor aprobada", "Revisión del asesor aprobada",
                                     r.observaciones or None)
        return r

    def solicitar_correcciones(self, usuario, solicitud_id, estados, observaciones):
        s = self._solicitud_revisable(usuario, solicitud_id)
        r = self._preparar(s, usuario, estados, observaciones)
        if not r.criterios_evaluados():
            raise ErrorNegocio(MSG_FE2_CORRECCIONES, {f"crit_{c.item_id}" for c in r.criterios if not c.estado})
        if not r.hay_incumplimientos():
            raise ErrorNegocio(MSG_SIN_INCUMPLIMIENTO)
        if not r.observaciones:
            raise ErrorNegocio(MSG_SIN_OBSERVACION, {"observaciones"})
        with transaccion(self.conn):
            r.finalizar("CORRECCIONES")
            self.repo.guardar(r)
            s.cambiar_estado(EstadoSolicitud.CORRECCIONES_SOLICITADAS, usuario.rol)
            self.solicitudes.guardar(s)
            self.historial.registrar(s, usuario, "Correcciones solicitadas por el asesor", "Correcciones solicitadas",
                                     r.observaciones)
        return r

    def _solicitud_revisable(self, usuario, solicitud_id):
        s = self.solicitudes.buscar_por_id(solicitud_id)
        if s is None:
            raise NoEncontrado("La solicitud no existe.")
        self.autorizacion.exigir_acceso(usuario, s, "revisar")
        if s.estado != EstadoSolicitud.REQUISITOS_VALIDADOS:
            raise ErrorNegocio("La solicitud no está disponible para revisión.")
        return s

    def _revision_vigente(self, s, usuario):
        r = self.repo.buscar_por_solicitud(s.id)
        if r is None or r.estado == "FINALIZADA":
            return self.repo.nueva(s.id, usuario.id)
        return r

    def _preparar(self, s, usuario, estados, observaciones):
        r = self._revision_vigente(s, usuario)
        for criterio_id, estado in estados.items():
            r.evaluar_criterio(criterio_id, estado)
        r.observaciones = (observaciones or "").replace("\r\n", "\n").strip()
        r.validar_observaciones()
        return r
