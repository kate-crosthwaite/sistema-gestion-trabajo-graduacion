"""
Kate Crosthwaite · 8-1009-1386
Pruebas del flujo extremo a extremo de CU-02, CU-03 y CU-05 con el cliente de pruebas de Flask y datos de demostración.
Ejecución: python -m unittest discover -s tests -t .
"""
import io
import re
import shutil
import sqlite3
import tempfile
import unittest

from sgme import create_app
from sgme.infraestructura.db import conectar

CLAVE = "Demo2026*"
PDF = b"%PDF-1.4\n1 0 obj\n<< >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n"


class FlujoSGME(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp()
        cls.app = create_app({"DB_PATH": f"{cls.dir}/t.db", "ARCHIVOS_DIR": f"{cls.dir}/archivos", "TESTING": True})

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.dir, ignore_errors=True)

    def conn(self):
        return conectar(self.app.config["DB_PATH"])

    def sesion(self, correo):
        cliente = self.app.test_client()
        self.post(cliente, "/login", {"correo": correo, "contrasena": CLAVE})
        return cliente

    def post(self, cliente, url, datos=None, **kw):
        with cliente.session_transaction() as s:
            s["csrf"] = "token"
        return cliente.post(url, data=dict(datos or {}, csrf="token"), follow_redirects=kw.pop("seguir", True), **kw)

    def sol_id(self, numero):
        return self.conn().execute("SELECT id FROM solicitud WHERE numero = ?", [numero]).fetchone()[0]

    def estado(self, numero):
        return self.conn().execute("SELECT estado FROM solicitud WHERE numero = ?", [numero]).fetchone()[0]

    # ---- CU-01 ----
    def test_01_acceso(self):
        c = self.app.test_client()
        r = self.post(c, "/login", {"correo": "alguien@gmail.com", "contrasena": CLAVE})
        self.assertIn("credenciales institucionales", r.get_data(as_text=True))
        r = self.post(c, "/login", {"correo": "juan.perez@utp.ac.pa", "contrasena": "mala"})
        self.assertIn("Credenciales no válidas", r.get_data(as_text=True))
        self.assertIn('type="password"', c.get("/login").get_data(as_text=True))
        r = self.post(c, "/login", {"correo": "juan.perez@utp.ac.pa", "contrasena": CLAVE})
        self.assertIn("Mis solicitudes", r.get_data(as_text=True))

    def test_02_autorizacion(self):
        juan = self.sesion("juan.perez@utp.ac.pa")
        self.assertEqual(juan.get("/secretaria").status_code, 403)
        self.assertEqual(juan.get("/asesor").status_code, 403)
        self.assertEqual(juan.get(f"/solicitud/{self.sol_id('SOL-2026-0002')}").status_code, 403)
        ana_doc = self.conn().execute("SELECT a.id FROM archivo_documento a JOIN documento_solicitud d ON d.id = a.documento_solicitud_id "
                                      "WHERE d.solicitud_id = ?", [self.sol_id("SOL-2026-0002")]).fetchone()[0]
        self.assertEqual(juan.get(f"/documento/{ana_doc}").status_code, 403)
        roberto = self.sesion("roberto.sanchez@utp.ac.pa")
        self.assertEqual(roberto.get(f"/asesor/revisar/{self.sol_id('SOL-2026-0002')}").status_code, 403)
        self.assertGreaterEqual(self.conn().execute("SELECT COUNT(*) FROM acceso_denegado").fetchone()[0], 5)
        self.assertEqual(self.app.test_client().get("/estudiante", follow_redirects=False).status_code, 302)

    # ---- CU-02 ----
    def test_03_registro_borrador_y_envio(self):
        sofia = self.sesion("sofia.vega@utp.ac.pa")
        r = self.post(sofia, "/estudiante/solicitud/nueva", {"accion": "borrador", "titulo": "Plataforma de telemedicina rural", "modalidad_id": "1"})
        self.assertIn("El borrador se guardó correctamente.", r.get_data(as_text=True))
        self.assertEqual(self.estado("SOL-2026-0004"), "BORRADOR")
        sid = self.sol_id("SOL-2026-0004")
        # FE-1: incompleta
        r = self.post(sofia, f"/estudiante/solicitud/{sid}/editar", {"accion": "enviar", "titulo": "Plataforma de telemedicina rural", "modalidad_id": "1"})
        self.assertIn("Debe completar todos los campos obligatorios y cargar los documentos requeridos.", r.get_data(as_text=True))
        self.assertEqual(self.estado("SOL-2026-0004"), "BORRADOR")
        datos = {"cedula": "8-940-5005", "nombre_completo": "Sofía Vega Araúz", "correo_institucional": "sofia.vega@utp.ac.pa",
                 "telefono": "6000-5005", "facultad_id": "1", "carrera_id": "1", "modalidad_id": "1", "asesor_id": "6",
                 "titulo": "Plataforma de telemedicina rural", "descripcion": "Sistema para consultas médicas remotas."}
        # FE-2: formato no permitido
        r = self.post(sofia, f"/estudiante/solicitud/{sid}/editar", dict(datos, accion="enviar", doc_1=(io.BytesIO(b"MZ..."), "virus.exe")),
                      content_type="multipart/form-data")
        self.assertIn("El formato del archivo no es permitido. Solo se aceptan archivos PDF y DOCX.", r.get_data(as_text=True))
        # FE-3: tamaño excedido
        grande = io.BytesIO(PDF + b"0" * (20 * 1024 * 1024))
        r = self.post(sofia, f"/estudiante/solicitud/{sid}/editar", dict(datos, accion="enviar", doc_1=(grande, "grande.pdf")),
                      content_type="multipart/form-data")
        self.assertIn("El archivo excede el tamaño máximo permitido de 20 MB.", r.get_data(as_text=True))
        self.assertEqual(self.estado("SOL-2026-0004"), "BORRADOR")
        # Envío correcto, con dos versiones del mismo documento
        self.post(sofia, f"/estudiante/solicitud/{sid}/editar", dict(datos, accion="borrador", doc_1=(io.BytesIO(PDF), "anteproyecto_v1.pdf")),
                  content_type="multipart/form-data")
        r = self.post(sofia, f"/estudiante/solicitud/{sid}/editar",
                      dict(datos, accion="enviar", doc_1=(io.BytesIO(PDF + b"v2"), "anteproyecto_v2.pdf"),
                           doc_2=(io.BytesIO(PDF), "carta.pdf"), doc_3=(io.BytesIO(PDF), "cronograma.pdf")),
                      content_type="multipart/form-data")
        self.assertIn("quedó en estado «Pendiente de validación»", r.get_data(as_text=True))
        self.assertEqual(self.estado("SOL-2026-0004"), "PENDIENTE_VALIDACION")
        c = self.conn()
        self.assertEqual(c.execute("SELECT COUNT(*), SUM(vigente) FROM archivo_documento a JOIN documento_solicitud d ON d.id = a.documento_solicitud_id "
                                   "WHERE d.solicitud_id = ? AND d.documento_requerido_id = 1", [sid]).fetchone()[:], (2, 1))
        self.assertEqual(c.execute("SELECT COUNT(*) FROM historial_evento WHERE solicitud_id = ?", [sid]).fetchone()[0], 1)
        self.assertEqual(sofia.get(f"/estudiante/solicitud/{sid}/editar").status_code, 403)

    def test_04_historial_solo_insercion(self):
        c = self.conn()
        with self.assertRaises(sqlite3.DatabaseError):
            c.execute("UPDATE historial_evento SET accion = 'x'")
        with self.assertRaises(sqlite3.DatabaseError):
            c.execute("DELETE FROM historial_evento")

    # ---- CU-03 ----
    def test_05_validacion_academica(self):
        maria = self.sesion("maria.gonzalez@utp.ac.pa")
        self.assertIn("SOL-2026-0004", maria.get("/secretaria").get_data(as_text=True))
        # FE-3: sin datos en el sistema académico
        r = maria.get(f"/secretaria/validar/{self.sol_id('SOL-2026-0003')}", follow_redirects=True)
        self.assertIn("No fue posible consultar los sistemas institucionales.", r.get_data(as_text=True))
        sid = self.sol_id("SOL-2026-0004")
        url = f"/secretaria/validar/{sid}"
        self.assertIn("Índice académico", maria.get(url).get_data(as_text=True))
        # FE-1: requisitos sin estado
        r = self.post(maria, url, {"accion": "validar", "req_1": "CUMPLE"})
        self.assertIn("Debe seleccionar un estado para todos los requisitos.", r.get_data(as_text=True))
        # FE-2: pendientes o no cumplidos
        estados = {f"req_{i}": "CUMPLE" for i in range(1, 7)}
        r = self.post(maria, url, dict(estados, req_3="PENDIENTE", accion="validar"))
        self.assertIn("No es posible validar la solicitud mientras existan requisitos pendientes o no cumplidos.", r.get_data(as_text=True))
        self.assertEqual(self.estado("SOL-2026-0004"), "PENDIENTE_VALIDACION")
        # Borrador conserva lo evaluado
        r = self.post(maria, url, dict(estados, req_3="PENDIENTE", accion="borrador", observacion="Falta paz y salvo"))
        self.assertIn("El borrador se guardó correctamente.", r.get_data(as_text=True))
        self.assertIn("Falta paz y salvo", r.get_data(as_text=True))
        # Rechazo exige observación (FA-3)
        r = self.post(maria, f"/secretaria/validar/{self.sol_id('SOL-2026-0001')}", {"accion": "rechazar", "observacion": ""})
        self.assertIn("Debe registrar una observación que justifique el rechazo.", r.get_data(as_text=True))
        r = self.post(maria, f"/secretaria/validar/{self.sol_id('SOL-2026-0001')}", {"accion": "rechazar", "observacion": "Índice insuficiente"})
        self.assertIn("La solicitud ha sido rechazada correctamente.", r.get_data(as_text=True))
        self.assertEqual(self.estado("SOL-2026-0001"), "RECHAZADA")
        # Validación exitosa
        r = self.post(maria, url, dict(estados, accion="validar"))
        self.assertIn("La validación de requisitos académicos ha sido registrada correctamente.", r.get_data(as_text=True))
        self.assertEqual(self.estado("SOL-2026-0004"), "REQUISITOS_VALIDADOS")
        fila = self.conn().execute("SELECT codigo_validacion_digital, datos_academicos_consultados FROM validacion_academica "
                                   "WHERE solicitud_id = ? AND decision = 'VALIDADA'", [sid]).fetchone()
        self.assertTrue(re.fullmatch(r"VD-\d{5}-[0-9A-F]{8}", fila[0]))
        self.assertIn("indice_academico", fila[1])
        self.assertEqual(maria.get(url, follow_redirects=True).status_code, 200)
        self.assertIn("ya no está pendiente", maria.get(url, follow_redirects=True).get_data(as_text=True))

    # ---- CU-05 ----
    def test_06_revision_del_asesor(self):
        laura = self.sesion("laura.martinez@utp.ac.pa")
        listado = laura.get("/asesor").get_data(as_text=True)
        self.assertIn("SOL-2026-0002", listado)
        self.assertIn("SOL-2026-0004", listado)
        self.assertNotIn("SOL-2026-0001", listado)
        sid = self.sol_id("SOL-2026-0004")
        url = f"/asesor/revisar/{sid}"
        todos = {f"crit_{i}": "CUMPLE" for i in range(1, 6)}
        r = self.post(laura, url, {"accion": "aprobar", "crit_1": "CUMPLE"})
        self.assertIn("Debe evaluar todos los criterios antes de aprobar la revisión.", r.get_data(as_text=True))
        r = self.post(laura, url, dict(todos, crit_4="PENDIENTE", accion="aprobar"))
        self.assertIn("No es posible aprobar la revisión mientras existan criterios pendientes o no cumplidos.", r.get_data(as_text=True))
        r = self.post(laura, url, dict(todos, accion="aprobar", observaciones="x" * 1001))
        self.assertIn("Las observaciones exceden el límite máximo de 1000 caracteres.", r.get_data(as_text=True))
        r = self.post(laura, url, dict(todos, crit_4="NO_CUMPLE", accion="correcciones", observaciones=""))
        self.assertIn("Debe registrar las observaciones", r.get_data(as_text=True))
        r = self.post(laura, url, dict(todos, accion="correcciones", observaciones="Todo cumple"))
        self.assertIn("al menos un criterio Pendiente o No cumple", r.get_data(as_text=True))
        self.assertEqual(self.estado("SOL-2026-0004"), "REQUISITOS_VALIDADOS")
        r = self.post(laura, url, dict(todos, crit_4="PENDIENTE", accion="correcciones", observaciones="Ampliar el marco teórico."))
        self.assertIn("Las correcciones fueron solicitadas correctamente.", r.get_data(as_text=True))
        fila = self.conn().execute("SELECT estado, estado_origen_correccion FROM solicitud WHERE numero = 'SOL-2026-0004'").fetchone()
        self.assertEqual(tuple(fila), ("CORRECCIONES_SOLICITADAS", "REQUISITOS_VALIDADOS"))
        # Aprobación sobre la solicitud validada de demostración
        sid2 = self.sol_id("SOL-2026-0002")
        r = self.post(laura, f"/asesor/revisar/{sid2}", dict(todos, accion="aprobar", observaciones="Trabajo viable."))
        self.assertIn("La revisión de la modalidad de egreso fue registrada correctamente.", r.get_data(as_text=True))
        self.assertEqual(self.estado("SOL-2026-0002"), "REVISION_ASESOR_APROBADA")
        self.assertIn("No existen modalidades de egreso asignadas para revisar.", laura.get("/asesor").get_data(as_text=True))
        self.assertEqual(laura.get(f"/asesor/revisar/{sid2}", follow_redirects=True).status_code, 200)

    def test_07_visualizar_y_verificar_integridad(self):
        juan = self.sesion("juan.perez@utp.ac.pa")
        archivo = self.conn().execute(
            "SELECT a.id, a.ruta FROM archivo_documento a JOIN documento_solicitud d ON d.id = a.documento_solicitud_id "
            "WHERE d.solicitud_id = ? LIMIT 1", [self.sol_id("SOL-2026-0001")]).fetchone()
        r = juan.get(f"/documento/{archivo[0]}")
        self.assertEqual((r.status_code, r.mimetype), (200, "application/pdf"))
        r.close()
        with open(f"{self.dir}/archivos/{archivo[1]}", "ab") as f:
            f.write(b"alterado")
        r = juan.get(f"/documento/{archivo[0]}")
        self.assertEqual(r.status_code, 400)
        self.assertIn("el archivo fue alterado", r.get_data(as_text=True))

    def test_08_pantallas_de_consulta(self):
        juan = self.sesion("juan.perez@utp.ac.pa")
        r = juan.get(f"/solicitud/{self.sol_id('SOL-2026-0001')}")
        self.assertIn("Historial del proceso", r.get_data(as_text=True))
        self.assertIn("Solicitud registrada", r.get_data(as_text=True))
        self.assertEqual(juan.get("/solicitud/9999").status_code, 404)
        self.assertEqual(self.app.test_client().get("/recuperar").status_code, 200)
        self.assertEqual(self.app.test_client().get("/modulo-previsto").status_code, 404)
        self.assertNotIn("Cuentas de demostración", self.app.test_client().get("/login").get_data(as_text=True))
        for correo in ("eduardo.rios@utp.ac.pa", "patricia.nunez@utp.ac.pa"):
            self.assertIn("Credenciales no válidas", self.post(self.app.test_client(), "/login", {"correo": correo, "contrasena": CLAVE}).get_data(as_text=True))
        sofia = self.sesion("sofia.vega@utp.ac.pa")
        self.assertIn("datos-docs", sofia.get("/estudiante/solicitud/nueva").get_data(as_text=True))
        asesora = self.sesion("laura.martinez@utp.ac.pa")
        self.assertIn("Historial del proceso", asesora.get(f"/solicitud/{self.sol_id('SOL-2026-0002')}").get_data(as_text=True))
        r = self.app.test_client().post("/login", data={"correo": "a@utp.ac.pa", "contrasena": "x"})
        self.assertEqual(r.status_code, 400)

    def test_10_rol_sin_modulo_no_ingresa(self):
        from werkzeug.security import generate_password_hash
        c = self.conn()
        c.execute("INSERT INTO usuario (cedula, nombre_completo, correo_institucional, rol, departamento, facultad_id, password_hash) "
                  "VALUES ('8-801-0001', 'Jefe de prueba', 'jefe.prueba@utp.ac.pa', 'JEFE', 'Ingeniería de Software', 1, ?)",
                  [generate_password_hash(CLAVE, method="pbkdf2:sha256")])
        r = self.post(self.app.test_client(), "/login", {"correo": "jefe.prueba@utp.ac.pa", "contrasena": CLAVE})
        self.assertIn("no tiene acceso a esta versión", r.get_data(as_text=True))

    def test_09_autocompletado_desde_la_cuenta(self):
        sofia = self.sesion("sofia.vega@utp.ac.pa")
        html = sofia.get("/estudiante/solicitud/nueva").get_data(as_text=True)
        for esperado in ("8-940-5005", "Sofía Vega Araúz", "sofia.vega@utp.ac.pa", "Facultad de Ingeniería de Sistemas Computacionales",
                         "Licenciatura en Ingeniería de Software", "2.15", "4.º año"):
            self.assertIn(esperado, html)
        self.assertNotIn('name="cedula"', html)
        self.assertEqual(html.count('campo-bloqueado'), 7)
        self.assertEqual(html.count('aria-readonly="true"'), 7)
        # Aunque se manipule el formulario, la identidad siempre sale de la cuenta
        self.post(sofia, "/estudiante/solicitud/nueva", {"accion": "borrador", "cedula": "0-000-0000", "nombre_completo": "Otra Persona",
                                                          "facultad_id": "2", "carrera_id": "4", "telefono": "6000-5005"})
        fila = self.conn().execute("SELECT cedula, nombre_completo, facultad_id, carrera_id FROM solicitud "
                                   "WHERE estudiante_id = (SELECT id FROM usuario WHERE correo_institucional = 'sofia.vega@utp.ac.pa') "
                                   "ORDER BY id DESC LIMIT 1").fetchone()
        self.assertEqual(tuple(fila), ("8-940-5005", "Sofía Vega Araúz", 1, 1))
        # Sin datos en el sistema académico el formulario sigue funcionando
        carlos = self.sesion("carlos.mendoza@utp.ac.pa")
        self.assertIn("No disponible", carlos.get("/estudiante/solicitud/nueva").get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
