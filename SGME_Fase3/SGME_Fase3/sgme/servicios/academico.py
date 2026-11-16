"""
Kate Crosthwaite · 8-1009-1386
Consulta de solo lectura al PuertoInformacionAcademica con tiempo límite y error controlado (ADR-003, RNF-08).
"""
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as TiempoAgotado

from .. import config
from ..dominio.errores import ConsultaNoDisponible

MSG_CONSULTA = "No fue posible consultar los sistemas institucionales. Intente nuevamente más tarde."


def consultar_con_limite(puerto, cedula):
    ejecutor = ThreadPoolExecutor(max_workers=1)
    try:
        return ejecutor.submit(puerto.consultar, cedula).result(timeout=config.TIEMPO_LIMITE_CONSULTA_ACADEMICA)
    except TiempoAgotado:
        raise ConsultaNoDisponible(MSG_CONSULTA)
    finally:
        ejecutor.shutdown(wait=False)
