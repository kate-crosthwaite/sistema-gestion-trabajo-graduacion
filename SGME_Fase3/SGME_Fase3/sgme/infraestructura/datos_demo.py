"""
Kate Crosthwaite · 8-1009-1386
Datos de demostración: catálogos, cuentas por rol y tres solicitudes de ejemplo en distintas etapas del proceso.
Las modalidades, sus documentos requeridos y las cuentas se cargan como datos preconfigurados (Fase 1, sección 8.4).
"""
import io

from werkzeug.security import generate_password_hash

from .db import transaccion

CLAVE_DEMO = "Demo2026*"

CARRERAS = [
    (1, "Licenciatura en Ingeniería de Software", "Ingeniería de Software", 1),
    (2, "Licenciatura en Ingeniería de Sistemas y Computación", "Ingeniería de Sistemas", 1),
    (3, "Licenciatura en Ingeniería en Sistemas de Información Gerencial", "Sistemas de Información", 1),
    (4, "Licenciatura en Ingeniería Industrial", "Ingeniería Industrial", 2),
]
MODALIDADES = [(1, "Tesis"), (2, "Tesis teórico-práctica"), (3, "Práctica profesional"),
               (4, "Opción de dos materias como trabajo de graduación"), (5, "Certificación internacional")]
_ADICIONAL = ("Documento adicional (opcional)", "Cualquier documento adicional de soporte", 0)
DOCUMENTOS = {
    1: [("Anteproyecto del trabajo", "Propuesta inicial del trabajo de investigación", 1),
        ("Carta de aceptación", "Carta de aceptación de la empresa o institución", 1),
        ("Cronograma de actividades", "Plan de actividades y tiempos estimados", 1), _ADICIONAL],
    2: [("Anteproyecto del trabajo", "Propuesta inicial del trabajo de investigación", 1),
        ("Carta de aceptación", "Carta de aceptación de la empresa o institución", 1),
        ("Cronograma de actividades", "Plan de actividades y tiempos estimados", 1), _ADICIONAL],
    3: [("Carta de aceptación de la empresa", "Aceptación de la empresa donde se realizará la práctica", 1),
        ("Plan de práctica profesional", "Objetivos y actividades de la práctica", 1),
        ("Cronograma de actividades", "Plan de actividades y tiempos estimados", 1), _ADICIONAL],
    4: [("Solicitud de las dos materias", "Materias de posgrado o maestría seleccionadas", 1),
        ("Plan de trabajo de graduación", "Plan de las actividades académicas", 1), _ADICIONAL],
    5: [("Constancia de inscripción en la certificación", "Comprobante emitido por la entidad certificadora", 1),
        ("Plan de estudio para la certificación", "Temario y calendario de preparación", 1), _ADICIONAL],
}
REQUISITOS = ["Créditos completos", "Índice académico válido", "Paz y salvo financiero",
              "Paz y salvo bibliotecario", "Servicio social completado", "Documentación institucional completa"]
CRITERIOS = ["Objetivos claramente definidos", "Metodología adecuada", "Alcance del trabajo viable",
             "Fundamentación teórica suficiente", "Cronograma consistente"]

USUARIOS = [  # cédula, nombre, correo, teléfono, rol, departamento, facultad, carrera
    ("8-900-1001", "Juan Pérez Gómez", "juan.perez@utp.ac.pa", "6000-1001", "ESTUDIANTE", None, 1, 1),
    ("8-910-2002", "Ana Rodríguez Castillo", "ana.rodriguez@utp.ac.pa", "6000-2002", "ESTUDIANTE", None, 1, 2),
    ("8-930-4004", "Carlos Mendoza Ortega", "carlos.mendoza@utp.ac.pa", "6000-4004", "ESTUDIANTE", None, 1, 3),
    ("8-940-5005", "Sofía Vega Araúz", "sofia.vega@utp.ac.pa", "6000-5005", "ESTUDIANTE", None, 1, 1),
    ("8-800-0001", "María González", "maria.gonzalez@utp.ac.pa", "523-0001", "SECRETARIA", None, 1, None),
    ("8-800-0002", "Ing. Laura Martínez", "laura.martinez@utp.ac.pa", "523-0002", "ASESOR", "Ingeniería de Software", 1, None),
    ("8-800-0003", "Ing. Roberto Sánchez", "roberto.sanchez@utp.ac.pa", "523-0003", "ASESOR", "Sistemas de Información", 1, None),
]


def _pdf(texto):
    flujo = f"BT /F1 20 Tf 72 700 Td ({texto}) Tj ET".encode("cp1252", "replace")
    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(flujo) + flujo + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    ]
    salida, posiciones = bytearray(b"%PDF-1.4\n"), []
    for i, objeto in enumerate(objetos, 1):
        posiciones.append(len(salida))
        salida += b"%d 0 obj\n" % i + objeto + b"\nendobj\n"
    inicio = len(salida)
    salida += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objetos) + 1)
    for p in posiciones:
        salida += b"%010d 00000 n \n" % p
    salida += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objetos) + 1, inicio)
    return bytes(salida)


def cargar(conn, almacen):
    with transaccion(conn):
        conn.executemany("INSERT INTO facultad (id, nombre) VALUES (?, ?)", [
            (1, "Facultad de Ingeniería de Sistemas Computacionales"), (2, "Facultad de Ingeniería Industrial")])
        conn.executemany("INSERT INTO carrera (id, nombre, departamento, facultad_id) VALUES (?, ?, ?, ?)", CARRERAS)
        conn.executemany("INSERT INTO modalidad (id, nombre) VALUES (?, ?)", MODALIDADES)
        for modalidad_id, docs in DOCUMENTOS.items():
            conn.executemany("INSERT INTO documento_requerido (modalidad_id, nombre, descripcion, obligatorio) "
                             "VALUES (?, ?, ?, ?)", [(modalidad_id,) + d for d in docs])
        conn.executemany("INSERT INTO requisito_academico (nombre) VALUES (?)", [(r,) for r in REQUISITOS])
        conn.executemany("INSERT INTO criterio_revision (nombre) VALUES (?)", [(c,) for c in CRITERIOS])
        for cedula, nombre, correo, tel, rol, depto, facultad, carrera in USUARIOS:
            conn.execute("INSERT INTO usuario (cedula, nombre_completo, correo_institucional, telefono, rol, "
                         "departamento, facultad_id, carrera_id, password_hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                         [cedula, nombre, correo, tel, rol, depto, facultad, carrera,
                          generate_password_hash(CLAVE_DEMO, method="pbkdf2:sha256")])
        ids = {f["correo_institucional"]: f["id"] for f in conn.execute("SELECT id, correo_institucional FROM usuario")}
        secretaria = ids["maria.gonzalez@utp.ac.pa"]
        _solicitud(conn, almacen, ids["juan.perez@utp.ac.pa"], "PENDIENTE_VALIDACION", 1, 1, ids["laura.martinez@utp.ac.pa"],
                   "Sistema web para la gestión académica en la Universidad Tecnológica de Panamá",
                   "Desarrollar un sistema web que permita gestionar la información académica de la universidad, "
                   "optimizando la administración de la información y mejorando la experiencia de los usuarios.",
                   "2026-10-20 09:15:00")
        ana = _solicitud(conn, almacen, ids["ana.rodriguez@utp.ac.pa"], "REQUISITOS_VALIDADOS", 2, 2,
                         ids["laura.martinez@utp.ac.pa"], "Modelo de analítica predictiva para la deserción estudiantil",
                         "Construir y validar un modelo predictivo que identifique de forma temprana a los estudiantes "
                         "con riesgo de abandonar la carrera, usando datos académicos históricos.", "2026-10-22 14:40:00")
        _solicitud(conn, almacen, ids["carlos.mendoza@utp.ac.pa"], "PENDIENTE_VALIDACION", 3, 3,
                   ids["roberto.sanchez@utp.ac.pa"], "Automatización de procesos de inventario en una empresa logística",
                   "Práctica profesional orientada a automatizar el control de inventario y reducir errores de registro.",
                   "2026-10-25 11:05:00")
        codigo = f"VD-{ana:05d}-DEMO0001"
        cur = conn.execute("INSERT INTO validacion_academica (solicitud_id, secretaria_id, estado, decision, observacion, "
                           "codigo_validacion_digital, fecha_validacion, datos_academicos_consultados) "
                           "VALUES (?, ?, 'FINALIZADA', 'VALIDADA', '', ?, '2026-10-23 10:00:00', '{}')",
                           [ana, secretaria, codigo])
        conn.executemany("INSERT INTO requisito_validado (validacion_id, requisito_id, estado) VALUES (?, ?, 'CUMPLE')",
                         [(cur.lastrowid, i) for i in range(1, len(REQUISITOS) + 1)])
        conn.execute("INSERT INTO historial_evento (solicitud_id, usuario_id, usuario_nombre, rol, accion, resultado, detalle, fecha) "
                     "VALUES (?, ?, 'María González', 'SECRETARIA', 'Requisitos académicos validados', "
                     "'Requisitos validados', ?, '2026-10-23 10:00:00')", [ana, secretaria, f"Validación digital {codigo}"])


def _solicitud(conn, almacen, estudiante_id, estado, modalidad_id, carrera_id, asesor_id, titulo, descripcion, fecha):
    u = conn.execute("SELECT * FROM usuario WHERE id = ?", [estudiante_id]).fetchone()
    carrera = conn.execute("SELECT facultad_id FROM carrera WHERE id = ?", [carrera_id]).fetchone()
    n = conn.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM solicitud").fetchone()[0]
    cur = conn.execute(
        "INSERT INTO solicitud (numero, estudiante_id, cedula, nombre_completo, correo_institucional, telefono, "
        "facultad_id, carrera_id, modalidad_id, titulo, descripcion, asesor_id, estado, fecha_registro) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDIENTE_VALIDACION', ?)",
        [f"SOL-2026-{n:04d}", estudiante_id, u["cedula"], u["nombre_completo"], u["correo_institucional"], u["telefono"],
         carrera["facultad_id"], carrera_id, modalidad_id, titulo, descripcion, asesor_id, fecha])
    sid = cur.lastrowid
    for dr in conn.execute("SELECT * FROM documento_requerido WHERE modalidad_id = ? ORDER BY id", [modalidad_id]).fetchall():
        ds = conn.execute("INSERT INTO documento_solicitud (solicitud_id, documento_requerido_id, estado) VALUES (?, ?, ?)",
                          [sid, dr["id"], "CARGADO" if dr["obligatorio"] else "OPCIONAL"]).lastrowid
        if dr["obligatorio"]:
            contenido = _pdf(dr["nombre"])
            ruta, huella = almacen.guardar(io.BytesIO(contenido), sid, "pdf")
            conn.execute("INSERT INTO archivo_documento (documento_solicitud_id, nombre_original, formato, tamano_bytes, "
                         "hash_sha256, ruta, version, vigente, fecha_carga) VALUES (?, ?, 'pdf', ?, ?, ?, 1, 1, ?)",
                         [ds, dr["nombre"].replace(" ", "_") + ".pdf", len(contenido), huella, ruta, fecha])
    detalle = f"Modalidad: {conn.execute('SELECT nombre FROM modalidad WHERE id = ?', [modalidad_id]).fetchone()[0]}. "
    detalle += f"Profesor asesor seleccionado: {conn.execute('SELECT nombre_completo FROM usuario WHERE id = ?', [asesor_id]).fetchone()[0]}."
    conn.execute("INSERT INTO historial_evento (solicitud_id, usuario_id, usuario_nombre, rol, accion, resultado, detalle, fecha) "
                 "VALUES (?, ?, ?, 'ESTUDIANTE', 'Solicitud registrada', 'Pendiente de validación', ?, ?)",
                 [sid, estudiante_id, u["nombre_completo"], detalle, fecha])
    if estado != "PENDIENTE_VALIDACION":
        conn.execute("UPDATE solicitud SET estado = ? WHERE id = ?", [estado, sid])
    return sid
