"""
Kate Crosthwaite · 8-1009-1386
DocumentoService (M3): carga con validación de formato y tamaño, versiones con hash y lectura autorizada.
"""
import os

from ..dominio.entidades import ArchivoDocumento
from ..dominio.errores import ErrorArchivo, ErrorNegocio, NoEncontrado
from ..infraestructura.db import transaccion

MSG_FORMATO = "El formato del archivo no es permitido. Solo se aceptan archivos PDF y DOCX."
MSG_TAMANO = "El archivo excede el tamaño máximo permitido de 20 MB."


def _firma_valida(extension, cabecera):
    if extension == "pdf":
        return b"%PDF" in cabecera
    return cabecera.startswith(b"PK")


class DocumentoService:
    def __init__(self, conn, repo, almacen, autorizacion):
        self.conn = conn
        self.repo = repo
        self.almacen = almacen
        self.autorizacion = autorizacion

    def adjuntar(self, usuario, solicitud_id, requerido_id, archivo):
        s = self.repo.buscar_por_id(solicitud_id)
        if s is None:
            raise NoEncontrado("La solicitud no existe.")
        self.autorizacion.exigir_acceso(usuario, s, "editar")
        nombre = os.path.basename(archivo.filename or "")
        extension = nombre.rsplit(".", 1)[-1].lower() if "." in nombre else ""
        archivo.stream.seek(0, os.SEEK_END)
        tamano = archivo.stream.tell()
        archivo.stream.seek(0)
        meta = ArchivoDocumento(nombre_original=nombre, formato=extension, tamano_bytes=tamano)
        if not meta.validar_formato():
            raise ErrorArchivo(MSG_FORMATO)
        if not meta.validar_tamano():
            raise ErrorArchivo(MSG_TAMANO)
        cabecera = archivo.stream.read(1024)
        archivo.stream.seek(0)
        if not _firma_valida(extension, cabecera):
            raise ErrorArchivo(MSG_FORMATO)
        meta.ruta, meta.hash_sha256 = self.almacen.guardar(archivo.stream, solicitud_id, extension)
        try:
            with transaccion(self.conn):
                self.repo.registrar_archivo(solicitud_id, requerido_id, meta)
        except BaseException:
            self.almacen.eliminar(meta.ruta)
            raise
        return meta

    def obtener_archivo(self, usuario, archivo_id):
        archivo, solicitud_id = self.repo.buscar_archivo(archivo_id)
        if archivo is None:
            raise NoEncontrado("El documento no existe.")
        self.autorizacion.exigir_acceso(usuario, self.repo.buscar_por_id(solicitud_id), "ver_documento")
        ruta = self.almacen.leer(archivo.ruta)
        if self.almacen.calcular_hash(ruta) != archivo.hash_sha256:
            raise ErrorNegocio("No fue posible verificar la integridad del documento: el archivo fue alterado.")
        return archivo, ruta
