"""
Kate Crosthwaite · 8-1009-1386
HistorialService (M7): registra eventos de solo inserción por solicitud y los intentos de acceso denegados.
"""
from ..dominio.entidades import ahora
from ..infraestructura.repositorios import filas


class HistorialService:
    def __init__(self, conn):
        self.conn = conn

    def registrar(self, solicitud, usuario, accion, resultado, detalle=None):
        self.conn.execute(
            "INSERT INTO historial_evento (solicitud_id, usuario_id, usuario_nombre, rol, accion, resultado, detalle, fecha) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [solicitud.id, usuario.id, usuario.nombre_completo, usuario.rol, accion, resultado, detalle, ahora()])

    def listar(self, solicitud_id):
        return filas(self.conn, "SELECT * FROM historial_evento WHERE solicitud_id = ? ORDER BY id", [solicitud_id])

    def registrar_acceso_denegado(self, usuario, solicitud_id, accion):
        self.conn.execute("INSERT INTO acceso_denegado (usuario_id, solicitud_id, accion, fecha) VALUES (?, ?, ?, ?)",
                          [usuario.id if usuario else 0, solicitud_id, accion, ahora()])
