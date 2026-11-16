"""
Kate Crosthwaite · 8-1009-1386
Contenedor de dependencias por petición: único lugar que conoce los adaptadores concretos (RNF-09).
"""
from .infraestructura.almacen_archivos import AlmacenArchivos
from .infraestructura.puertos import AdaptadorAcademicoSimulado, AdaptadorIdentidadInstitucional
from .infraestructura.repositorios import RevisionRepository, SolicitudRepository, ValidacionRepository
from .servicios.autenticacion import AutenticacionService
from .servicios.autorizacion import AutorizacionService
from .servicios.documentos import DocumentoService
from .servicios.historial import HistorialService
from .servicios.revision import RevisionAsesorService
from .servicios.solicitudes import SolicitudService
from .servicios.validacion import ValidacionAcademicaService


class Servicios:
    def __init__(self, conn, raiz_archivos):
        solicitudes = SolicitudRepository(conn)
        puerto_academico = AdaptadorAcademicoSimulado()
        self.historial = HistorialService(conn)
        self.autorizacion = AutorizacionService(conn, self.historial)
        self.autenticacion = AutenticacionService(conn, AdaptadorIdentidadInstitucional(conn))
        self.documentos = DocumentoService(conn, solicitudes, AlmacenArchivos(raiz_archivos), self.autorizacion)
        self.solicitudes = SolicitudService(conn, solicitudes, self.documentos, self.historial, self.autorizacion,
                                         puerto_academico)
        self.validacion = ValidacionAcademicaService(
            conn, ValidacionRepository(conn, solicitudes), solicitudes, puerto_academico,
            self.historial, self.autorizacion)
        self.revision = RevisionAsesorService(
            conn, RevisionRepository(conn, solicitudes), solicitudes, self.historial, self.autorizacion)
