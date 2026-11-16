"""
Kate Crosthwaite · 8-1009-1386
AlmacenArchivos: guarda los documentos fuera de la raíz web con hash SHA-256 y sin sobrescribir versiones.
"""
import hashlib
import os
import uuid

from ..dominio.errores import ErrorNegocio


class AlmacenArchivos:
    def __init__(self, raiz):
        self.raiz = os.path.realpath(raiz)

    def guardar(self, flujo, solicitud_id, extension):
        os.makedirs(os.path.join(self.raiz, str(solicitud_id)), exist_ok=True)
        ruta = f"{solicitud_id}/{uuid.uuid4().hex}.{extension}"
        resumen = hashlib.sha256()
        with open(os.path.join(self.raiz, ruta), "wb") as destino:
            while True:
                bloque = flujo.read(1024 * 1024)
                if not bloque:
                    break
                resumen.update(bloque)
                destino.write(bloque)
        return ruta, resumen.hexdigest()

    def leer(self, ruta):
        absoluta = os.path.realpath(os.path.join(self.raiz, ruta))
        if not absoluta.startswith(self.raiz + os.sep) or not os.path.isfile(absoluta):
            raise ErrorNegocio("El archivo solicitado no está disponible.")
        return absoluta

    @staticmethod
    def calcular_hash(absoluta):
        resumen = hashlib.sha256()
        with open(absoluta, "rb") as origen:
            for bloque in iter(lambda: origen.read(1024 * 1024), b""):
                resumen.update(bloque)
        return resumen.hexdigest()

    def eliminar(self, ruta):
        try:
            os.remove(os.path.join(self.raiz, ruta))
        except FileNotFoundError:
            pass
