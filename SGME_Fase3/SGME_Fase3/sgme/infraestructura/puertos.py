"""
Kate Crosthwaite · 8-1009-1386
Puertos de identidad e información académica con sus adaptadores de demostración (ADR-003 y ADR-006, RNF-09).
"""
from abc import ABC, abstractmethod

from werkzeug.security import check_password_hash

from ..dominio.entidades import InformacionAcademica
from ..dominio.errores import ConsultaNoDisponible, ErrorNegocio


class PuertoIdentidad(ABC):
    @abstractmethod
    def autenticar(self, correo, contrasena):
        """Devuelve el id del usuario verificado o None si las credenciales no son válidas."""


class AdaptadorIdentidadInstitucional(PuertoIdentidad):
    """Cuentas de demostración: correo institucional y contraseña con hash y sal."""

    def __init__(self, conn):
        self.conn = conn

    def autenticar(self, correo, contrasena):
        fila = self.conn.execute(
            "SELECT id, habilitado, password_hash FROM usuario WHERE lower(correo_institucional) = ?",
            [correo.strip().lower()]).fetchone()
        if fila is None or not check_password_hash(fila["password_hash"], contrasena):
            return None
        if not fila["habilitado"]:
            raise ErrorNegocio("La cuenta está deshabilitada. Comuníquese con Secretaría Académica.")
        return fila["id"]


class PuertoInformacionAcademica(ABC):
    @abstractmethod
    def consultar(self, cedula):
        """Devuelve la InformacionAcademica del estudiante (solo lectura) o lanza ConsultaNoDisponible."""


class AdaptadorAcademicoSimulado(PuertoInformacionAcademica):
    """Fuente simulada con datos de demostración; sustituible por el sistema académico real."""

    DATOS = {
        "8-900-1001": dict(anio_que_cursa="5.º año", semestre_actual="II Semestre 2026", indice_academico=2.45,
                           ultimo_semestre_cursado="I Semestre 2026", residencia="Ciudad de Panamá",
                           asignaturas_pendientes=(),
                           asignaturas_matriculadas=("Ingeniería de Software II", "Seminario de Graduación")),
        "8-910-2002": dict(anio_que_cursa="5.º año", semestre_actual="II Semestre 2026", indice_academico=2.80,
                           ultimo_semestre_cursado="I Semestre 2026", residencia="San Miguelito",
                           asignaturas_pendientes=(),
                           asignaturas_matriculadas=("Ingeniería de Software II", "Minería de Datos")),
        "8-940-5005": dict(anio_que_cursa="4.º año", semestre_actual="II Semestre 2026", indice_academico=2.15,
                           ultimo_semestre_cursado="I Semestre 2026", residencia="Arraiján",
                           asignaturas_pendientes=("Base de Datos II",),
                           asignaturas_matriculadas=("Ingeniería de Software II", "Redes de Computadoras II")),
    }

    def consultar(self, cedula):
        datos = self.DATOS.get(cedula)
        if datos is None:
            raise ConsultaNoDisponible("No fue posible consultar los sistemas institucionales. Intente nuevamente más tarde.")
        return InformacionAcademica(**datos)
