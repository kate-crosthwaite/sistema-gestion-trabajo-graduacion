"""
Kate Crosthwaite · 8-1009-1386
Catálogos de roles y estados del SGME y política de transiciones FlujoSolicitud (módulo M6).
"""


class Rol:
    ESTUDIANTE = "ESTUDIANTE"
    ASESOR = "ASESOR"
    JEFE = "JEFE"
    SECRETARIA = "SECRETARIA"
    AUTORIDAD = "AUTORIDAD"


class EstadoSolicitud:
    BORRADOR = "BORRADOR"
    PENDIENTE_VALIDACION = "PENDIENTE_VALIDACION"
    REQUISITOS_VALIDADOS = "REQUISITOS_VALIDADOS"
    REVISION_ASESOR_APROBADA = "REVISION_ASESOR_APROBADA"
    APROBADA_DEPARTAMENTO = "APROBADA_DEPARTAMENTO"
    CORRECCIONES_SOLICITADAS = "CORRECCIONES_SOLICITADAS"
    RECHAZADA = "RECHAZADA"
    APROBADA = "APROBADA"


class EstadoRequisito:
    CUMPLE = "CUMPLE"
    PENDIENTE = "PENDIENTE"
    NO_CUMPLE = "NO_CUMPLE"


class EstadoDocumento:
    PENDIENTE = "PENDIENTE"
    CARGADO = "CARGADO"
    OPCIONAL = "OPCIONAL"


ROLES_CON_MODULO = (Rol.ESTUDIANTE, Rol.SECRETARIA, Rol.ASESOR)

ETIQUETA_ROL = {
    Rol.ESTUDIANTE: "Estudiante",
    Rol.ASESOR: "Profesor Asesor",
    Rol.JEFE: "Jefe de Departamento",
    Rol.SECRETARIA: "Secretaría Académica",
    Rol.AUTORIDAD: "Autoridad Académica (Vicedecano)",
}
ETIQUETA_ESTADO = {
    EstadoSolicitud.BORRADOR: "Borrador",
    EstadoSolicitud.PENDIENTE_VALIDACION: "Pendiente de validación",
    EstadoSolicitud.REQUISITOS_VALIDADOS: "Requisitos validados",
    EstadoSolicitud.REVISION_ASESOR_APROBADA: "Revisión del asesor aprobada",
    EstadoSolicitud.APROBADA_DEPARTAMENTO: "Aprobada por departamento",
    EstadoSolicitud.CORRECCIONES_SOLICITADAS: "Correcciones solicitadas",
    EstadoSolicitud.RECHAZADA: "Rechazada",
    EstadoSolicitud.APROBADA: "Aprobada",
}
ETIQUETA_EVALUACION = {
    EstadoRequisito.CUMPLE: "Cumple",
    EstadoRequisito.PENDIENTE: "Pendiente",
    EstadoRequisito.NO_CUMPLE: "No cumple",
}
ETIQUETA_DOCUMENTO = {
    EstadoDocumento.PENDIENTE: "Pendiente",
    EstadoDocumento.CARGADO: "Cargado",
    EstadoDocumento.OPCIONAL: "Opcional",
}

_E, _R = EstadoSolicitud, Rol
_TRANSICIONES = {
    (_E.BORRADOR, _E.PENDIENTE_VALIDACION): (_R.ESTUDIANTE,),
    (_E.PENDIENTE_VALIDACION, _E.REQUISITOS_VALIDADOS): (_R.SECRETARIA,),
    (_E.PENDIENTE_VALIDACION, _E.RECHAZADA): (_R.SECRETARIA,),
    (_E.REQUISITOS_VALIDADOS, _E.REVISION_ASESOR_APROBADA): (_R.ASESOR,),
    (_E.REQUISITOS_VALIDADOS, _E.CORRECCIONES_SOLICITADAS): (_R.ASESOR,),
    (_E.REVISION_ASESOR_APROBADA, _E.APROBADA_DEPARTAMENTO): (_R.JEFE,),
    (_E.REVISION_ASESOR_APROBADA, _E.CORRECCIONES_SOLICITADAS): (_R.JEFE,),
    (_E.APROBADA_DEPARTAMENTO, _E.APROBADA): (_R.AUTORIDAD,),
    (_E.APROBADA_DEPARTAMENTO, _E.RECHAZADA): (_R.AUTORIDAD,),
}


ETAPAS = (("Solicitud registrada", "Estudiante"), ("Validación académica", "Secretaría Académica"),
          ("Revisión del profesor asesor", "Profesor Asesor"), ("Aprobación departamental", "Jefe de Departamento"),
          ("Aprobación final", "Autoridad Académica"))
_ETAPA_ACTUAL = {_E.BORRADOR: 0, _E.PENDIENTE_VALIDACION: 1, _E.REQUISITOS_VALIDADOS: 2,
                 _E.REVISION_ASESOR_APROBADA: 3, _E.APROBADA_DEPARTAMENTO: 4, _E.APROBADA: 5}


def etapas_del_proceso(estado, origen_correccion=None):
    """Progreso por etapa para la línea de tiempo: (nombre, actor, situación).

    Situaciones: completada, actual, pendiente, correcciones, rechazada. Mientras no exista CU-07, el rechazo
    solo ocurre en la validación académica (etapa 2)."""
    if estado == _E.CORRECCIONES_SOLICITADAS:
        indice, final = _ETAPA_ACTUAL.get(origen_correccion, 2), "correcciones"
    elif estado == _E.RECHAZADA:
        indice, final = 1, "rechazada"
    else:
        indice, final = _ETAPA_ACTUAL[estado], "actual"
    etapas = []
    for i, (nombre, actor) in enumerate(ETAPAS):
        situacion = "completada" if i < indice else (final if i == indice else "pendiente")
        etapas.append((nombre, actor, situacion))
    return etapas


class FlujoSolicitud:
    """Política del dominio: transiciones válidas por rol y retorno tras correcciones (H-02, H-07)."""

    @staticmethod
    def puede_transicionar(desde, hacia, rol, origen=None):
        if desde == _E.CORRECCIONES_SOLICITADAS:
            return (rol == _R.ESTUDIANTE and hacia == origen
                    and origen in (_E.REQUISITOS_VALIDADOS, _E.REVISION_ASESOR_APROBADA))
        return rol in _TRANSICIONES.get((desde, hacia), ())
