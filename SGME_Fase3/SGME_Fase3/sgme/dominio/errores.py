"""
Kate Crosthwaite · 8-1009-1386
Excepciones del dominio del SGME; el mensaje de cada una se muestra al usuario tal cual.
"""


class ErrorNegocio(Exception):
    def __init__(self, mensaje, campos=None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.campos = set(campos or ())


class AccesoDenegado(ErrorNegocio):
    pass


class NoEncontrado(ErrorNegocio):
    pass


class ConflictoVersion(ErrorNegocio):
    pass


class ConsultaNoDisponible(ErrorNegocio):
    pass


class ErrorArchivo(ErrorNegocio):
    pass
