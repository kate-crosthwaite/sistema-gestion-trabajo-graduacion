"""
Kate Crosthwaite · 8-1009-1386
SolicitudService (M2, CU-02): arma, guarda como borrador, envía y consulta solicitudes de modalidad de egreso.
"""
from ..dominio.entidades import Solicitud
from ..dominio.errores import ConsultaNoDisponible, ErrorArchivo, ErrorNegocio, NoEncontrado
from ..dominio.estados import EstadoSolicitud, Rol
from ..infraestructura.db import transaccion
from .academico import consultar_con_limite


class SolicitudService:
    def __init__(self, conn, repo, documentos, historial, autorizacion, puerto_academico):
        self.conn = conn
        self.repo = repo
        self.puerto = puerto_academico
        self.documentos = documentos
        self.historial = historial
        self.autorizacion = autorizacion

    def catalogos(self):
        return self.repo.catalogos()

    @staticmethod
    def campos_de_cuenta(usuario):
        """Datos que el sistema ya conoce por la cuenta institucional; se autocompletan y no se editan."""
        datos = {"cedula": usuario.cedula, "nombre_completo": usuario.nombre_completo,
                 "correo_institucional": usuario.correo_institucional,
                 "facultad_id": usuario.facultad_id, "carrera_id": usuario.carrera_id}
        return {campo: valor for campo, valor in datos.items() if valor}

    def informacion_academica(self, usuario):
        """Información académica de solo lectura para mostrar en el formulario; None si la fuente no responde."""
        try:
            return consultar_con_limite(self.puerto, usuario.cedula)
        except ConsultaNoDisponible:
            return None

    def listar_de_estudiante(self, usuario):
        self.autorizacion.exigir_acceso(usuario, None, "registrar")
        return self.repo.listar("s.estudiante_id = ?", [usuario.id])

    def armar_solicitud(self, usuario, solicitud_id=None, datos=None):
        self.autorizacion.exigir_acceso(usuario, None, "registrar")
        if solicitud_id:
            s = self._cargar(solicitud_id)
            self.autorizacion.exigir_acceso(usuario, s, "editar")
        else:
            s = Solicitud(estudiante_id=usuario.id, telefono=usuario.telefono)
        if datos is not None:
            self._aplicar_datos(s, datos)
        for campo, valor in self.campos_de_cuenta(usuario).items():
            setattr(s, campo, valor)
        return s

    def guardar_borrador(self, usuario, s, archivos):
        """Persiste los datos y adjunta los archivos. Devuelve (solicitud, [(requerido_id, mensaje)])."""
        self.autorizacion.exigir_acceso(usuario, s if s.id else None, "editar" if s.id else "registrar")
        s.validar_campos()
        self._validar_catalogos(s)
        with transaccion(self.conn):
            self.repo.guardar(s)
            sobrantes = self.repo.sincronizar_documentos(s)
        for ruta in sobrantes:
            self.documentos.almacen.eliminar(ruta)
        errores = []
        for requerido_id, archivo in archivos.items():
            try:
                self.documentos.adjuntar(usuario, s.id, requerido_id, archivo)
            except ErrorArchivo as e:
                errores.append((requerido_id, e.mensaje))
        return self.repo.buscar_por_id(s.id), errores

    def enviar(self, usuario, solicitud_id):
        s = self._cargar(solicitud_id)
        self.autorizacion.exigir_acceso(usuario, s, "editar")
        s.validar_campos()
        s.validar_completitud()
        with transaccion(self.conn):
            s.cambiar_estado(EstadoSolicitud.PENDIENTE_VALIDACION, usuario.rol)
            self.repo.guardar(s)
            self.historial.registrar(
                s, usuario, "Solicitud registrada", "Pendiente de validación",
                f"Modalidad: {s.modalidad}. Profesor asesor seleccionado: {s.asesor}.")
        return s

    def detalle(self, usuario, solicitud_id):
        s = self._cargar(solicitud_id)
        self.autorizacion.exigir_acceso(usuario, s, "ver")
        return s, self.historial.listar(s.id)

    def _cargar(self, solicitud_id):
        s = self.repo.buscar_por_id(solicitud_id)
        if s is None:
            raise NoEncontrado("La solicitud no existe.")
        return s

    @staticmethod
    def _aplicar_datos(s, d):
        def texto(clave):
            return (d.get(clave) or "").replace("\r\n", "\n").strip()

        def entero(clave):
            valor = (d.get(clave) or "").strip()
            return int(valor) if valor.isdigit() else None

        s.cedula, s.nombre_completo = texto("cedula"), texto("nombre_completo")
        s.correo_institucional, s.telefono = texto("correo_institucional").lower(), texto("telefono")
        s.facultad_id, s.carrera_id = entero("facultad_id"), entero("carrera_id")
        s.modalidad_id, s.asesor_id = entero("modalidad_id"), entero("asesor_id")
        s.titulo, s.descripcion = texto("titulo"), texto("descripcion")

    def _validar_catalogos(self, s):
        if s.facultad_id and not self.repo.existe("SELECT 1 FROM facultad WHERE id = ?", [s.facultad_id]):
            raise ErrorNegocio("La facultad seleccionada no es válida.", {"facultad_id"})
        if s.carrera_id and not self.repo.existe("SELECT 1 FROM carrera WHERE id = ? AND facultad_id IS ?",
                                                 [s.carrera_id, s.facultad_id]):
            raise ErrorNegocio("La carrera seleccionada no pertenece a la facultad indicada.", {"carrera_id"})
        if s.modalidad_id and not self.repo.existe("SELECT 1 FROM modalidad WHERE id = ? AND habilitada = 1",
                                                   [s.modalidad_id]):
            raise ErrorNegocio("La modalidad seleccionada no está disponible.", {"modalidad_id"})
        if s.asesor_id and not self.repo.existe("SELECT 1 FROM usuario WHERE id = ? AND rol = ? AND habilitado = 1",
                                                [s.asesor_id, Rol.ASESOR]):
            raise ErrorNegocio("El profesor asesor seleccionado no es válido.", {"asesor_id"})
