# SGME · Fase 3: Implementación

Sistema de Gestión de Modalidades de Egreso (UTP · Ingeniería de Software II · Grupo 1SG-131).
Versión ejecutable de los tres casos de uso seleccionados, con CU-01 como soporte de acceso:

| Caso de uso | Actor | Qué hace |
|---|---|---|
| CU-01 Iniciar sesión (soporte) | Todos | Acceso con correo institucional y redirección según el rol |
| CU-02 Registrar modalidad de egreso | Estudiante | Registra la solicitud, adjunta documentos, guarda borrador y envía a validación |
| CU-03 Validar requisitos académicos | Secretaría Académica | Evalúa seis requisitos, valida o rechaza y genera la validación digital |
| CU-05 Revisar la modalidad de egreso | Profesor Asesor | Evalúa cinco criterios, aprueba la revisión o solicita correcciones |

Los tres forman un proceso continuo: lo que produce un caso de uso es la precondición del siguiente
(`Pendiente de validación` → `Requisitos validados` → `Revisión del asesor aprobada` o `Correcciones solicitadas`).

## Cuentas de demostración

Para facilitar la revisión y demostración del Sistema de Gestión de Modalidades de Egreso (SGME), se proporcionan las siguientes cuentas de acceso.

**Contraseña única para todas las cuentas:** `Demo2026*`

| Rol | Nombre | Correo institucional | Funcionalidad de prueba |
|---|---|---|---|
| Estudiante | Sofia Vega | `sofia.vega@utp.ac.pa` | Registrar una solicitud desde cero (CU-02). |
| Estudiante | Juan Pérez | `juan.perez@utp.ac.pa` | Solicitud pendiente de validación. |
| Estudiante | Ana Rodríguez | `ana.rodriguez@utp.ac.pa` | Solicitud ya validada. |
| Estudiante | Carlos Mendoza | `carlos.mendoza@utp.ac.pa` | Comprobar error de consulta académica (FE-3). |
| Secretaría Académica | María González | `maria.gonzalez@utp.ac.pa` | Validar requisitos académicos (CU-03). |
| Profesor Asesor | Ing. Laura Martínez | `laura.martinez@utp.ac.pa` | Revisar solicitudes asignadas (CU-05). |
| Profesor Asesor | Ing. Roberto Sánchez | `roberto.sanchez@utp.ac.pa` | Segundo asesor para comprobar la separación de solicitudes. |

### Instrucciones de acceso

1. Ejecutar el proyecto siguiendo las instrucciones de instalación.
2. Abrir el navegador en `http://127.0.0.1:8000`.
3. Introducir el correo institucional de cualquiera de las cuentas anteriores.
4. Ingresar la contraseña común: `Demo2026*`.
5. El sistema identificará automáticamente el rol y mostrará el módulo correspondiente.

### Consideraciones

- Todas las cuentas son de demostración.
- La información académica utilizada es simulada.
- Las cuentas permiten probar los casos de uso implementados en esta fase.
- Los roles de Jefe de Departamento y Autoridad Académica no cuentan con acceso en esta versión.

## Requisitos y ejecución

Python 3.10 o superior.

```
pip install -r requirements.txt
python run.py
```

`run.py` crea la base de datos SQLite con los datos de demostración en la carpeta `datos/` y abre el navegador en
`http://127.0.0.1:8000`. Para restaurar los datos de demostración: `python run.py --reiniciar`.

Pruebas del flujo completo (usa una base de datos temporal, no toca `datos/`):

```
python -m unittest discover -s tests -t .
```

## Cuentas

Las cuentas de los tres roles con módulo (estudiante, Secretaría Académica y profesor asesor) se cargan con los datos iniciales desde
`sgme/infraestructura/datos_demo.py`, donde también se define la contraseña inicial. Los roles de Jefe de Departamento y Autoridad Académica
no tienen módulo ni cuentas en esta versión: una cuenta con esos roles no puede iniciar sesión.

## Guion de demostración

1. **CU-02.** Entrar como estudiante (`sofia.vega`, sin solicitudes). «Registrar Modalidad de Egreso»: elegir facultad, carrera, modalidad (la tabla de
   documentos cambia según la modalidad), asesor `Ing. Laura Martínez`, título y descripción. Probar «Guardar borrador»;
   adjuntar un `.exe` (formato no permitido, FE-2) y un PDF válido; probar «Enviar solicitud» con documentos faltantes (FE-1) y luego completa.
2. **CU-03.** Entrar como `maria.gonzalez`. Abrir la solicitud de Sofía: se consulta la información académica (solo lectura).
   Probar validar con requisitos sin estado (FE-1) o con alguno pendiente (FE-2), guardar borrador, rechazar sin observación y,
   finalmente, validar con los seis en «Cumple» (se genera la validación digital). Abrir la solicitud de `carlos.mendoza`
   para ver el error de consulta académica (FE-3). La solicitud de `juan.perez` sirve para probar el rechazo (FA-3).
3. **CU-05.** Entrar como `laura.martinez`. Abrir la solicitud validada (la de Ana o la de Sofía): visualizar documentos,
   probar aprobar con criterios sin evaluar (FE-2), con alguno pendiente (FE-4), observaciones de más de 1000 caracteres (FE-3);
   solicitar correcciones y aprobar la revisión.
4. **Seguridad (RNF-01, RNF-02).** Con `juan.perez`, abrir `/secretaria` o `/solicitud/2` (solicitud de Ana): acceso
   denegado y registrado en la tabla `acceso_denegado`.

## Estructura y relación con el diseño (Fase 2)

| Carpeta o archivo | Módulo / elemento del diseño |
|---|---|
| `sgme/web/*_controller.py` | Capa de controladores (`SolicitudController`, `ValidacionController`, `RevisionController`, acceso) |
| `sgme/servicios/autenticacion.py`, `autorizacion.py` | M1 Seguridad y acceso (`AutorizacionService.verificar_acceso`) |
| `sgme/servicios/solicitudes.py` | M2 `SolicitudService` |
| `sgme/servicios/documentos.py`, `infraestructura/almacen_archivos.py` | M3 `DocumentoService`, `AlmacenArchivos` |
| `sgme/servicios/validacion.py` | M4 `ValidacionAcademicaService` |
| `sgme/servicios/revision.py` | M5 `RevisionAsesorService` |
| `sgme/dominio/estados.py` (`FlujoSolicitud`) | M6 Flujo del proceso |
| `sgme/servicios/historial.py` | M7 `HistorialService` |
| `sgme/dominio/entidades.py` | Entidades y reglas de negocio |
| `sgme/infraestructura/puertos.py` | `PuertoInformacionAcademica` + `AdaptadorAcademicoSimulado`, `PuertoIdentidad` |
| `sgme/infraestructura/repositorios.py`, `db.py` | Repositorios y esquema relacional |
| `sgme/contenedor.py` | Único lugar que conoce los adaptadores concretos |
| `sgme/templates/`, `sgme/static/` | Capa de presentación (HTML, CSS y JavaScript estándar) |

La trazabilidad completa RF → CU → archivo/clase/función está en `MATRIZ_TRAZABILIDAD.md`.

## Interfaz y autocompletado

- La interfaz sigue los prototipos de la Fase 1 (figuras 2, 3 y 4): franja y menú lateral índigo, encabezado con menú plegable, ruta de navegación,
  tarjetas numeradas, campos de solo lectura, selectores de color Cumple/Pendiente/No cumple, resumen de evaluación, línea de tiempo
  «Historial del proceso» por etapas y barra fija de acciones.
- Identidad visual institucional: menú lateral con degradado índigo-violeta y acento dorado del escudo, encabezado de página con degradado, indicadores
  (solicitudes, borradores, en proceso) en el inicio y en los listados, barra de progreso del formulario de registro y pantalla de acceso con panel institucional.
  La tipografía Plus Jakarta Sans (licencia SIL OFL) se incluye en `sgme/static/fonts`, por lo que se ve igual sin conexión a Internet.
- Los desplegables son un componente propio (panel redondeado, opción activa resaltada, íconos de color en Cumple/Pendiente/No cumple) que se maneja con ratón y teclado
  (flechas, Enter, Escape y escritura para buscar). El `<select>` original se conserva oculto, de modo que el formulario funciona igual sin JavaScript.
- Siguiendo la decisión H-11 de la Fase 1, se omiten los elementos fuera de alcance de los prototipos: notificaciones, «Mis Documentos», «Mi Perfil»,
  «Seguimiento», «Ayuda» y «Contactar Secretaría», y la sección del asesor en CU-03.
- **Autocompletado (CU-02).** Al iniciar sesión, el sistema conoce la cuenta del estudiante: cédula, nombre completo, correo institucional, facultad y carrera
  se completan solos, se muestran en gris con un candado para indicar que no se pueden editar, el teléfono se precarga y es editable. El índice académico y el año que cursa se consultan, también en gris y de solo lectura,
  al sistema académico simulado (`PuertoInformacionAcademica`); si no responde, se muestra «No disponible». La identidad de la solicitud siempre sale
  de la cuenta, aunque se manipule el formulario.

## Ajustes respecto al diseño y supuestos

- **Controladores como funciones de Flask.** Las clases `SolicitudController`, `ValidacionController` y `RevisionController` del diseño son módulos con funciones (`registrar`, `validar`, `revisar`).
- `SolicitudService.armar_solicitud` se agregó para reconstruir la solicitud desde el formulario sin guardarla, y `guardar_borrador` recibe esa solicitud.
- `FlujoSolicitud.puede_transicionar` recibe además el estado de origen de las correcciones; `Solicitud.cambiar_estado(destino, rol)` lo calcula internamente.
- No existe `DocumentoRepository`: el SQL de archivos está en `SolicitudRepository` (`registrar_archivo`, `buscar_archivo`).
- **Número del anteproyecto** (pantalla de CU-03): la especificación no define una numeración propia; se muestra el número de la solicitud y su fecha de registro.
- **Conflictos de versión** (bloqueo optimista): se detectan y se informa al usuario para que recargue; no hay reintento automático.
- **Listados** limitados a 200 filas, sin controles de paginación.
- **Recuperación de contraseña**: simulada, no modifica credenciales.
- Los criterios de «solicitar correcciones» exigen que los cinco criterios estén evaluados, al menos uno Pendiente o No cumple, y observaciones.
- El rechazo en CU-03 no consulta el sistema académico; solo la validación guarda la copia (JSON) de los datos consultados (ADR-003).

## Alcance

Implementado: CU-01 (soporte), CU-02, CU-03 y CU-05, con validaciones, reglas de negocio, persistencia, historial y flujos alternos y de excepción.
No implementado (se declara como tal en la matriz): CU-04 completo (solo existen el listado de solicitudes y el detalle con historial), CU-06, CU-07, CU-08 y CU-09.
Modalidades, documentos requeridos y cuentas se cargan como datos de demostración (`sgme/infraestructura/datos_demo.py`).

## Declaración de uso de IA (borrador)

Se utilizó Claude (Anthropic) como apoyo para estructurar la implementación según el diseño de la Fase 2, generar el código base y las
pruebas del flujo. El equipo debe revisar el código, ejecutarlo, y poder explicar cada módulo y cada regla de negocio.
