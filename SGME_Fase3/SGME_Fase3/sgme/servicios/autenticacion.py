"""
Kate Crosthwaite · 8-1009-1386
AutenticacionService (M1, CU-01): inicio de sesión con credenciales institucionales mediante PuertoIdentidad.
"""
from .. import config
from ..dominio.entidades import Usuario
from ..dominio.errores import ErrorNegocio
from ..dominio.estados import ROLES_CON_MODULO


class AutenticacionService:
    def __init__(self, conn, identidad):
        self.conn = conn
        self.identidad = identidad

    def iniciar_sesion(self, correo, contrasena):
        correo = (correo or "").strip().lower()
        if not correo.endswith(config.DOMINIO_INSTITUCIONAL):
            raise ErrorNegocio("Solo se permite el acceso con credenciales institucionales (@utp.ac.pa).")
        if not contrasena:
            raise ErrorNegocio("Ingrese su contraseña.")
        usuario_id = self.identidad.autenticar(correo, contrasena)
        if usuario_id is None:
            raise ErrorNegocio("Credenciales no válidas.")
        usuario = self.cargar_usuario(usuario_id)
        if usuario.rol not in ROLES_CON_MODULO:
            raise ErrorNegocio("Su cuenta no tiene acceso a esta versión del sistema.")
        return usuario

    def cargar_usuario(self, usuario_id):
        f = self.conn.execute("SELECT * FROM usuario WHERE id = ? AND habilitado = 1", [usuario_id]).fetchone()
        if f is None:
            return None
        return Usuario(id=f["id"], cedula=f["cedula"], nombre_completo=f["nombre_completo"],
                       correo_institucional=f["correo_institucional"], telefono=f["telefono"] or "", rol=f["rol"],
                       departamento=f["departamento"], facultad_id=f["facultad_id"],
                       carrera_id=f["carrera_id"], habilitado=True)
