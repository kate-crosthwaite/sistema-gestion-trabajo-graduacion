"""
Kate Crosthwaite · 8-1009-1386
Entidades y objetos de valor del dominio del SGME, con las reglas de negocio de CU-02, CU-03 y CU-05.
"""
import json
import re
import secrets
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Optional

from .. import config
from .errores import ErrorNegocio
from .estados import EstadoDocumento, EstadoRequisito, EstadoSolicitud, FlujoSolicitud

MSG_INCOMPLETO = "Debe completar todos los campos obligatorios y cargar los documentos requeridos."
MSG_OBSERVACIONES = "Las observaciones exceden el límite máximo de 1000 caracteres."
EVALUACIONES = (EstadoRequisito.CUMPLE, EstadoRequisito.PENDIENTE, EstadoRequisito.NO_CUMPLE)
CAMPOS_OBLIGATORIOS = ("cedula", "nombre_completo", "correo_institucional", "telefono", "facultad_id",
                       "carrera_id", "modalidad_id", "titulo", "asesor_id", "descripcion")


def ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class Usuario:
    id: int
    cedula: str
    nombre_completo: str
    correo_institucional: str
    telefono: str
    rol: str
    departamento: Optional[str] = None
    facultad_id: Optional[int] = None
    carrera_id: Optional[int] = None
    habilitado: bool = True


@dataclass
class ArchivoDocumento:
    nombre_original: str
    formato: str
    tamano_bytes: int
    hash_sha256: str = ""
    ruta: str = ""
    version: int = 1
    vigente: bool = True
    fecha_carga: str = ""
    id: Optional[int] = None

    def validar_formato(self):
        return self.formato.lower() in config.FORMATOS_PERMITIDOS

    def validar_tamano(self):
        return self.tamano_bytes <= config.TAMANO_MAX_BYTES


@dataclass
class DocumentoSolicitud:
    requerido_id: int
    nombre: str
    descripcion: str
    obligatorio: bool
    estado: str = EstadoDocumento.PENDIENTE
    archivo: Optional[ArchivoDocumento] = None
    id: Optional[int] = None

    def marcar_cargado(self):
        self.estado = EstadoDocumento.CARGADO

    def marcar_pendiente(self):
        self.estado = EstadoDocumento.PENDIENTE if self.obligatorio else EstadoDocumento.OPCIONAL


@dataclass
class Solicitud:
    estudiante_id: int
    id: Optional[int] = None
    numero: str = ""
    cedula: str = ""
    nombre_completo: str = ""
    correo_institucional: str = ""
    telefono: str = ""
    facultad_id: Optional[int] = None
    carrera_id: Optional[int] = None
    modalidad_id: Optional[int] = None
    titulo: str = ""
    descripcion: str = ""
    asesor_id: Optional[int] = None
    estado: str = EstadoSolicitud.BORRADOR
    estado_origen_correccion: Optional[str] = None
    fecha_registro: str = ""
    version: int = 1
    departamento: str = ""
    modalidad: str = ""
    carrera: str = ""
    facultad: str = ""
    asesor: str = ""
    documentos: list = field(default_factory=list)

    def es_propietario(self, usuario):
        return self.estudiante_id == usuario.id

    def validar_campos(self):
        if len(self.descripcion) > config.MAX_CARACTERES:
            raise ErrorNegocio("La descripción del trabajo no puede superar los 1000 caracteres.", {"descripcion"})
        if self.correo_institucional and not self.correo_institucional.lower().endswith(config.DOMINIO_INSTITUCIONAL):
            raise ErrorNegocio("Ingrese un correo institucional (@utp.ac.pa).", {"correo_institucional"})
        if self.telefono and not re.fullmatch(r"[0-9+\-\s()]{7,20}", self.telefono):
            raise ErrorNegocio("Ingrese un número de teléfono válido.", {"telefono"})

    def validar_completitud(self):
        faltantes = {c for c in CAMPOS_OBLIGATORIOS if not str(getattr(self, c) or "").strip()}
        faltantes |= {f"doc_{d.requerido_id}" for d in self.documentos if d.obligatorio and d.archivo is None}
        if faltantes:
            raise ErrorNegocio(MSG_INCOMPLETO, faltantes)

    def cambiar_estado(self, destino, rol):
        """Única vía para cambiar el estado (ADR-005)."""
        if not FlujoSolicitud.puede_transicionar(self.estado, destino, rol, self.estado_origen_correccion):
            raise ErrorNegocio("La transición de estado no está permitida para este rol.")
        if destino == EstadoSolicitud.CORRECCIONES_SOLICITADAS:
            self.estado_origen_correccion = self.estado
        elif self.estado == EstadoSolicitud.CORRECCIONES_SOLICITADAS:
            self.estado_origen_correccion = None
        self.estado = destino


@dataclass(frozen=True)
class InformacionAcademica:
    anio_que_cursa: str
    semestre_actual: str
    indice_academico: float
    ultimo_semestre_cursado: str
    residencia: str
    asignaturas_pendientes: tuple = ()
    asignaturas_matriculadas: tuple = ()

    def a_json(self):
        return json.dumps(asdict(self), ensure_ascii=False)


@dataclass
class ItemEvaluado:
    item_id: int
    nombre: str
    estado: Optional[str] = None


class RequisitoValidado(ItemEvaluado):
    pass


class CriterioEvaluado(ItemEvaluado):
    pass


def _asignar(items, item_id, estado):
    estado = estado or None
    if estado is not None and estado not in EVALUACIONES:
        raise ErrorNegocio("El estado de evaluación seleccionado no es válido.")
    for item in items:
        if item.item_id == item_id:
            item.estado = estado
            return
    raise ErrorNegocio("El elemento a evaluar no existe.")


@dataclass
class ValidacionAcademica:
    solicitud_id: int
    secretaria_id: int
    requisitos: list = field(default_factory=list)
    id: Optional[int] = None
    estado: str = "BORRADOR"
    decision: Optional[str] = None
    observacion: str = ""
    codigo_validacion_digital: str = ""
    fecha_validacion: str = ""
    datos_academicos_consultados: str = ""

    def establecer_estado(self, requisito_id, estado):
        _asignar(self.requisitos, requisito_id, estado)

    def todos_evaluados(self):
        return all(r.estado for r in self.requisitos)

    def todos_cumplen(self):
        return bool(self.requisitos) and all(r.estado == EstadoRequisito.CUMPLE for r in self.requisitos)

    def finalizar(self, decision, datos_academicos=""):
        self.estado, self.decision = "FINALIZADA", decision
        self.fecha_validacion = ahora()
        self.datos_academicos_consultados = datos_academicos
        if decision == "VALIDADA":
            self.codigo_validacion_digital = f"VD-{self.solicitud_id:05d}-{secrets.token_hex(4).upper()}"


@dataclass
class RevisionAsesor:
    solicitud_id: int
    asesor_id: int
    criterios: list = field(default_factory=list)
    id: Optional[int] = None
    estado: str = "BORRADOR"
    decision: Optional[str] = None
    observaciones: str = ""
    fecha_revision: str = ""

    def evaluar_criterio(self, criterio_id, estado):
        _asignar(self.criterios, criterio_id, estado)

    def criterios_evaluados(self):
        return all(c.estado for c in self.criterios)

    def todos_cumplen(self):
        return bool(self.criterios) and all(c.estado == EstadoRequisito.CUMPLE for c in self.criterios)

    def hay_incumplimientos(self):
        return any(c.estado in (EstadoRequisito.PENDIENTE, EstadoRequisito.NO_CUMPLE) for c in self.criterios)

    def validar_observaciones(self):
        if len(self.observaciones) > config.MAX_CARACTERES:
            raise ErrorNegocio(MSG_OBSERVACIONES, {"observaciones"})

    def finalizar(self, decision):
        self.estado, self.decision = "FINALIZADA", decision
        self.fecha_revision = ahora()
