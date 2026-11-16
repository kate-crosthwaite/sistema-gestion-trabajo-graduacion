"""
Kate Crosthwaite · 8-1009-1386
SolicitudRepository, ValidacionRepository y RevisionRepository: acceso a datos y mapeo de filas a entidades.
"""
from dataclasses import fields

from ..dominio.entidades import (ArchivoDocumento, CriterioEvaluado, DocumentoSolicitud, RequisitoValidado,
                                 RevisionAsesor, Solicitud, ValidacionAcademica, ahora)
from ..dominio.errores import ConflictoVersion, ErrorNegocio
from ..dominio.estados import EstadoDocumento, EstadoSolicitud


def filas(conn, sql, params=()):
    return [dict(f) for f in conn.execute(sql, params).fetchall()]


_SELECT = """SELECT s.*, c.departamento AS departamento, c.nombre AS carrera, m.nombre AS modalidad,
    f.nombre AS facultad, a.nombre_completo AS asesor
    FROM solicitud s
    LEFT JOIN carrera c ON c.id = s.carrera_id LEFT JOIN modalidad m ON m.id = s.modalidad_id
    LEFT JOIN facultad f ON f.id = s.facultad_id LEFT JOIN usuario a ON a.id = s.asesor_id"""
_CAMPOS = ("cedula", "nombre_completo", "correo_institucional", "telefono", "facultad_id", "carrera_id",
           "modalidad_id", "titulo", "descripcion", "asesor_id", "estado", "estado_origen_correccion")
_TEXTOS = ("cedula", "nombre_completo", "correo_institucional", "telefono", "titulo", "descripcion",
           "departamento", "carrera", "modalidad", "facultad", "asesor")


class SolicitudRepository:
    def __init__(self, conn):
        self.conn = conn

    def catalogos(self):
        return {
            "facultades": filas(self.conn, "SELECT id, nombre FROM facultad ORDER BY nombre"),
            "carreras": filas(self.conn, "SELECT id, nombre, facultad_id FROM carrera ORDER BY nombre"),
            "modalidades": filas(self.conn, "SELECT id, nombre FROM modalidad WHERE habilitada = 1 ORDER BY id"),
            "documentos": filas(self.conn, "SELECT id, modalidad_id, nombre, descripcion, obligatorio "
                                           "FROM documento_requerido ORDER BY id"),
            "asesores": filas(self.conn, "SELECT id, nombre_completo FROM usuario "
                                         "WHERE rol = 'ASESOR' AND habilitado = 1 ORDER BY nombre_completo"),
        }

    def existe(self, sql, params):
        return self.conn.execute(sql, params).fetchone() is not None

    @staticmethod
    def _mapear(fila):
        d = dict(fila)
        for k in _TEXTOS:
            d[k] = d[k] or ""
        return Solicitud(**{f.name: d[f.name] for f in fields(Solicitud) if f.name != "documentos"})

    def buscar_por_id(self, solicitud_id):
        fila = self.conn.execute(_SELECT + " WHERE s.id = ?", [solicitud_id]).fetchone()
        if fila is None:
            return None
        s = self._mapear(fila)
        s.documentos = self._documentos(s.id)
        return s

    def listar(self, condicion, params=(), orden="DESC", limite=200):
        orden = "ASC" if orden == "ASC" else "DESC"
        consulta = f"{_SELECT} WHERE {condicion} ORDER BY s.id {orden} LIMIT {int(limite)}"
        return [self._mapear(f) for f in self.conn.execute(consulta, params).fetchall()]

    def _documentos(self, solicitud_id):
        consulta = """SELECT ds.id AS ds_id, ds.documento_requerido_id AS requerido_id, ds.estado,
            dr.nombre, dr.descripcion, dr.obligatorio, a.id AS a_id, a.nombre_original, a.formato,
            a.tamano_bytes, a.hash_sha256, a.ruta, a.version, a.vigente, a.fecha_carga
            FROM documento_solicitud ds JOIN documento_requerido dr ON dr.id = ds.documento_requerido_id
            LEFT JOIN archivo_documento a ON a.documento_solicitud_id = ds.id AND a.vigente = 1
            WHERE ds.solicitud_id = ? ORDER BY dr.id"""
        docs = []
        for f in self.conn.execute(consulta, [solicitud_id]):
            archivo = None
            if f["a_id"] is not None:
                archivo = ArchivoDocumento(
                    id=f["a_id"], nombre_original=f["nombre_original"], formato=f["formato"],
                    tamano_bytes=f["tamano_bytes"], hash_sha256=f["hash_sha256"], ruta=f["ruta"],
                    version=f["version"], vigente=bool(f["vigente"]), fecha_carga=f["fecha_carga"])
            docs.append(DocumentoSolicitud(
                id=f["ds_id"], requerido_id=f["requerido_id"], nombre=f["nombre"],
                descripcion=f["descripcion"] or "", obligatorio=bool(f["obligatorio"]),
                estado=f["estado"], archivo=archivo))
        return docs

    def guardar(self, s):
        valores = [getattr(s, c) for c in _CAMPOS]
        if s.id is None:
            s.fecha_registro = ahora()
            n = self.conn.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM solicitud").fetchone()[0]
            s.numero = f"SOL-{s.fecha_registro[:4]}-{n:04d}"
            cur = self.conn.execute(
                "INSERT INTO solicitud (numero, estudiante_id, fecha_registro, version, " + ", ".join(_CAMPOS) +
                ") VALUES (?, ?, ?, 1, " + ", ".join("?" * len(_CAMPOS)) + ")",
                [s.numero, s.estudiante_id, s.fecha_registro] + valores)
            s.id, s.version = cur.lastrowid, 1
            return
        cur = self.conn.execute(
            "UPDATE solicitud SET " + ", ".join(f"{c} = ?" for c in _CAMPOS) +
            ", version = version + 1 WHERE id = ? AND version = ?", valores + [s.id, s.version])
        if cur.rowcount == 0:
            raise ConflictoVersion("La solicitud fue modificada por otro usuario. Recargue la página e intente nuevamente.")
        s.version += 1

    def sincronizar_documentos(self, s):
        """Crea las filas de documentos de la modalidad elegida; devuelve las rutas de archivos que dejan de aplicar."""
        requeridos = filas(self.conn, "SELECT id, obligatorio FROM documento_requerido WHERE modalidad_id = ?",
                           [s.modalidad_id]) if s.modalidad_id else []
        ids = {r["id"] for r in requeridos}
        existentes = {f["documento_requerido_id"]: f["id"] for f in self.conn.execute(
            "SELECT id, documento_requerido_id FROM documento_solicitud WHERE solicitud_id = ?", [s.id])}
        for r in requeridos:
            if r["id"] not in existentes:
                estado = EstadoDocumento.PENDIENTE if r["obligatorio"] else EstadoDocumento.OPCIONAL
                self.conn.execute("INSERT INTO documento_solicitud (solicitud_id, documento_requerido_id, estado) "
                                  "VALUES (?, ?, ?)", [s.id, r["id"], estado])
        sobrantes = []
        for requerido_id, ds_id in existentes.items():
            if requerido_id not in ids:
                sobrantes += [f["ruta"] for f in self.conn.execute(
                    "SELECT ruta FROM archivo_documento WHERE documento_solicitud_id = ?", [ds_id])]
                self.conn.execute("DELETE FROM documento_solicitud WHERE id = ?", [ds_id])
        return sobrantes

    def registrar_archivo(self, solicitud_id, requerido_id, a):
        ds = self.conn.execute("SELECT id FROM documento_solicitud WHERE solicitud_id = ? AND documento_requerido_id = ?",
                               [solicitud_id, requerido_id]).fetchone()
        if ds is None:
            raise ErrorNegocio("El documento no corresponde a la modalidad seleccionada.")
        a.version = self.conn.execute("SELECT COALESCE(MAX(version), 0) + 1 FROM archivo_documento "
                                      "WHERE documento_solicitud_id = ?", [ds["id"]]).fetchone()[0]
        a.fecha_carga = ahora()
        self.conn.execute("UPDATE archivo_documento SET vigente = 0 WHERE documento_solicitud_id = ?", [ds["id"]])
        cur = self.conn.execute(
            "INSERT INTO archivo_documento (documento_solicitud_id, nombre_original, formato, tamano_bytes, "
            "hash_sha256, ruta, version, vigente, fecha_carga) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)",
            [ds["id"], a.nombre_original, a.formato, a.tamano_bytes, a.hash_sha256, a.ruta, a.version, a.fecha_carga])
        a.id = cur.lastrowid
        self.conn.execute("UPDATE documento_solicitud SET estado = ? WHERE id = ?", [EstadoDocumento.CARGADO, ds["id"]])

    def buscar_archivo(self, archivo_id):
        f = self.conn.execute(
            "SELECT a.*, ds.solicitud_id FROM archivo_documento a "
            "JOIN documento_solicitud ds ON ds.id = a.documento_solicitud_id WHERE a.id = ?", [archivo_id]).fetchone()
        if f is None:
            return None, None
        return ArchivoDocumento(
            id=f["id"], nombre_original=f["nombre_original"], formato=f["formato"], tamano_bytes=f["tamano_bytes"],
            hash_sha256=f["hash_sha256"], ruta=f["ruta"], version=f["version"], vigente=bool(f["vigente"]),
            fecha_carga=f["fecha_carga"]), f["solicitud_id"]


class ValidacionRepository:
    def __init__(self, conn, solicitudes):
        self.conn = conn
        self.solicitudes = solicitudes

    def listar_pendientes(self):
        return self.solicitudes.listar("s.estado = ?", [EstadoSolicitud.PENDIENTE_VALIDACION], orden="ASC")

    def nueva(self, solicitud_id, secretaria_id):
        requisitos = [RequisitoValidado(item_id=r["id"], nombre=r["nombre"])
                      for r in filas(self.conn, "SELECT id, nombre FROM requisito_academico ORDER BY id")]
        return ValidacionAcademica(solicitud_id, secretaria_id, requisitos)

    def buscar_por_solicitud(self, solicitud_id):
        f = self.conn.execute("SELECT * FROM validacion_academica WHERE solicitud_id = ? ORDER BY id DESC LIMIT 1",
                              [solicitud_id]).fetchone()
        if f is None:
            return None
        requisitos = [RequisitoValidado(item_id=r["requisito_id"], nombre=r["nombre"], estado=r["estado"])
                      for r in self.conn.execute(
                          "SELECT rv.requisito_id, ra.nombre, rv.estado FROM requisito_validado rv "
                          "JOIN requisito_academico ra ON ra.id = rv.requisito_id "
                          "WHERE rv.validacion_id = ? ORDER BY ra.id", [f["id"]])]
        return ValidacionAcademica(
            solicitud_id=f["solicitud_id"], secretaria_id=f["secretaria_id"], requisitos=requisitos, id=f["id"],
            estado=f["estado"], decision=f["decision"], observacion=f["observacion"] or "",
            codigo_validacion_digital=f["codigo_validacion_digital"] or "", fecha_validacion=f["fecha_validacion"] or "",
            datos_academicos_consultados=f["datos_academicos_consultados"] or "")

    def guardar(self, v):
        valores = [v.secretaria_id, v.estado, v.decision, v.observacion, v.codigo_validacion_digital,
                   v.fecha_validacion, v.datos_academicos_consultados]
        if v.id is None:
            cur = self.conn.execute(
                "INSERT INTO validacion_academica (solicitud_id, secretaria_id, estado, decision, observacion, "
                "codigo_validacion_digital, fecha_validacion, datos_academicos_consultados) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)", [v.solicitud_id] + valores)
            v.id = cur.lastrowid
        else:
            self.conn.execute(
                "UPDATE validacion_academica SET secretaria_id = ?, estado = ?, decision = ?, observacion = ?, "
                "codigo_validacion_digital = ?, fecha_validacion = ?, datos_academicos_consultados = ? WHERE id = ?",
                valores + [v.id])
        self.conn.execute("DELETE FROM requisito_validado WHERE validacion_id = ?", [v.id])
        self.conn.executemany("INSERT INTO requisito_validado (validacion_id, requisito_id, estado) VALUES (?, ?, ?)",
                              [(v.id, r.item_id, r.estado) for r in v.requisitos])


class RevisionRepository:
    def __init__(self, conn, solicitudes):
        self.conn = conn
        self.solicitudes = solicitudes

    def listar_asignadas(self, asesor_id):
        return self.solicitudes.listar("s.asesor_id = ? AND s.estado = ?",
                                       [asesor_id, EstadoSolicitud.REQUISITOS_VALIDADOS], orden="ASC")

    def nueva(self, solicitud_id, asesor_id):
        criterios = [CriterioEvaluado(item_id=c["id"], nombre=c["nombre"])
                     for c in filas(self.conn, "SELECT id, nombre FROM criterio_revision ORDER BY id")]
        return RevisionAsesor(solicitud_id, asesor_id, criterios)

    def buscar_por_solicitud(self, solicitud_id):
        f = self.conn.execute("SELECT * FROM revision_asesor WHERE solicitud_id = ? ORDER BY id DESC LIMIT 1",
                              [solicitud_id]).fetchone()
        if f is None:
            return None
        criterios = [CriterioEvaluado(item_id=c["criterio_id"], nombre=c["nombre"], estado=c["estado"])
                     for c in self.conn.execute(
                         "SELECT ce.criterio_id, cr.nombre, ce.estado FROM criterio_evaluado ce "
                         "JOIN criterio_revision cr ON cr.id = ce.criterio_id WHERE ce.revision_id = ? ORDER BY cr.id",
                         [f["id"]])]
        return RevisionAsesor(
            solicitud_id=f["solicitud_id"], asesor_id=f["asesor_id"], criterios=criterios, id=f["id"],
            estado=f["estado"], decision=f["decision"], observaciones=f["observaciones"] or "",
            fecha_revision=f["fecha_revision"] or "")

    def guardar(self, r):
        valores = [r.asesor_id, r.estado, r.decision, r.observaciones, r.fecha_revision]
        if r.id is None:
            cur = self.conn.execute(
                "INSERT INTO revision_asesor (solicitud_id, asesor_id, estado, decision, observaciones, fecha_revision) "
                "VALUES (?, ?, ?, ?, ?, ?)", [r.solicitud_id] + valores)
            r.id = cur.lastrowid
        else:
            self.conn.execute("UPDATE revision_asesor SET asesor_id = ?, estado = ?, decision = ?, observaciones = ?, "
                              "fecha_revision = ? WHERE id = ?", valores + [r.id])
        self.conn.execute("DELETE FROM criterio_evaluado WHERE revision_id = ?", [r.id])
        self.conn.executemany("INSERT INTO criterio_evaluado (revision_id, criterio_id, estado) VALUES (?, ?, ?)",
                              [(r.id, c.item_id, c.estado) for c in r.criterios])
