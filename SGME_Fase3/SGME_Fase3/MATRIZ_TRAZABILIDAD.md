# Matriz de trazabilidad · Fase 3

Rutas relativas a `sgme/`. Estado: **Implementado**, **Parcial** o **No implementado**.

## 1. Requisitos funcionales

| RF | CU | Componente | Archivo → clase / función | Estado |
|---|---|---|---|---|
| RF-01 | CU-09 | M2 (datos) | `infraestructura/datos_demo.py` (modalidades y documentos requeridos precargados) | No implementado (datos de demostración) |
| RF-02 | CU-02 | M2 | `web/solicitud_controller.py` → `registrar`; `servicios/solicitudes.py` → `SolicitudService.armar_solicitud`, `campos_de_cuenta` (autocompletado), `informacion_academica`, `guardar_borrador`, `enviar`; `dominio/entidades.py` → `Solicitud.validar_campos`, `validar_completitud`; `infraestructura/repositorios.py` → `SolicitudRepository.guardar`, `sincronizar_documentos`; `templates/solicitud_form.html` | Implementado |
| RF-03 | CU-02, CU-03, CU-05 | M3 | `servicios/documentos.py` → `DocumentoService.adjuntar`, `obtener_archivo`; `dominio/entidades.py` → `ArchivoDocumento.validar_formato`, `validar_tamano`; `infraestructura/almacen_archivos.py` → `AlmacenArchivos.guardar`, `leer`, `calcular_hash`; `repositorios.py` → `SolicitudRepository.registrar_archivo`, `buscar_archivo`; `web/solicitud_controller.py` → `documento`; `templates/_macros.html` → `documentos` | Implementado en CU-02 (carga), CU-03 y CU-05 (visualización). CU-04, CU-06, CU-07 y CU-08 no implementados |
| RF-04 | CU-03 | M4 | `web/validacion_controller.py` → `listar`, `validar`; `servicios/validacion.py` → `ValidacionAcademicaService.abrir_validacion`, `guardar_borrador`, `validar`, `rechazar`; `dominio/entidades.py` → `ValidacionAcademica.establecer_estado`, `todos_evaluados`, `todos_cumplen`, `finalizar`; `repositorios.py` → `ValidacionRepository`; `templates/validar.html` | Implementado |
| RF-05 | CU-05 | M5 | `web/revision_controller.py` → `listar`, `revisar`; `servicios/revision.py` → `RevisionAsesorService.abrir_revision`, `guardar_borrador`, `aprobar`, `solicitar_correcciones`; `dominio/entidades.py` → `RevisionAsesor.evaluar_criterio`, `criterios_evaluados`, `todos_cumplen`, `hay_incumplimientos`, `validar_observaciones`; `repositorios.py` → `RevisionRepository`; `templates/revisar.html` | Implementado |
| RF-06 | CU-06 | M5 (previsto) | `dominio/estados.py` → `FlujoSolicitud` (transiciones del jefe); `servicios/autorizacion.py` → permisos del rol JEFE (sin módulo ni cuentas) | No implementado |
| RF-07 | CU-07 | M5 (previsto) | `dominio/estados.py` → `FlujoSolicitud` (transiciones de la autoridad); `servicios/autorizacion.py` → permisos del rol AUTORIDAD (sin módulo ni cuentas) | No implementado |
| RF-08 | CU-04 | M2, M7 | `web/solicitud_controller.py` → `inicio`, `detalle`; `servicios/solicitudes.py` → `listar_de_estudiante`, `detalle` | Parcial (estado, datos e historial; sin línea de tiempo con progreso) |
| RF-09 | CU-01 | M1 | `servicios/autenticacion.py` → `AutenticacionService.iniciar_sesion`, `cargar_usuario`; `infraestructura/puertos.py` → `PuertoIdentidad`, `AdaptadorIdentidadInstitucional`; `web/auth_controller.py` → `login`, `inicio`, `salir`, `recuperar` | Implementado (recuperación de contraseña simulada) |
| RF-10 | CU-02, CU-03, CU-05 | M6, M7 | `servicios/historial.py` → `HistorialService.registrar`, `listar`; tabla `historial_evento` con disparadores de solo inserción (`infraestructura/db.py`); invocado en `SolicitudService.enviar`, `ValidacionAcademicaService.validar`, `rechazar`, `RevisionAsesorService.aprobar`, `solicitar_correcciones` | Implementado (CU-06 a CU-08 no implementados) |
| RF-11 | CU-04 / CU-08 | M2, M3, M6, M7 | `Solicitud.estado_origen_correccion` y `FlujoSolicitud.puede_transicionar` ya contemplan el retorno a la etapa que pidió las correcciones | No implementado |
| RF-12 | CU-09 | M1 (datos) | `infraestructura/datos_demo.py` (cuentas y roles precargados) | No implementado (datos de demostración) |

## 2. Requisitos no funcionales

| RNF | Dónde se aplica | Estado |
|---|---|---|
| RNF-01 | `web/__init__.py` → `requiere_rol`; `servicios/autorizacion.py` → `AutorizacionService.verificar_rol`, `exigir_acceso` | Implementado (`tests/test_flujo.py::test_02_autorizacion`) |
| RNF-02 | `AutorizacionService.verificar_acceso` por solicitud y por documento (`DocumentoService.obtener_archivo`); intentos denegados en `acceso_denegado` | Implementado |
| RNF-03 | `AutenticacionService.iniciar_sesion` (dominio `@utp.ac.pa`), hash con sal en `datos_demo.py`, campo de contraseña oculto en `login.html`, expiración por inactividad en `sgme/__init__.py` | Implementado |
| RNF-04 | `solicitud_form.html` y `static/js/sgme.js` (datos precargados, estado por documento, contador, errores junto al campo, borrador) | Implementado en la interfaz; prueba con 5 estudiantes pendiente |
| RNF-05 | Infraestructura de despliegue | No implementado |
| RNF-06 | HTML, CSS y JavaScript estándar | Revisado en Chromium; falta registrar Edge y Firefox |
| RNF-07 | `infraestructura/db.py` → `transaccion` (una por caso de uso), restricciones del esquema, `AlmacenArchivos` con hash SHA-256 y versiones, `SolicitudRepository.guardar` con bloqueo optimista | Implementado |
| RNF-08 | Índices en `db.py`; listados acotados | Implementado; prueba de carga pendiente |
| RNF-09 | `PuertoInformacionAcademica` + `AdaptadorAcademicoSimulado`; solo `contenedor.py` conoce el adaptador | Implementado |

## 3. Clases del diseño (Fase 2) y su código

| Clase del diseño | Archivo |
|---|---|
| `PantallaRegistrarSolicitud`, `PantallaValidarRequisitos`, `PantallaRevisarModalidad` | `templates/solicitud_form.html`, `validar.html`, `revisar.html` + `static/js/sgme.js` |
| `SolicitudController`, `ValidacionController`, `RevisionController` | `web/solicitud_controller.py`, `validacion_controller.py`, `revision_controller.py` |
| `SolicitudService`, `DocumentoService`, `ValidacionAcademicaService`, `RevisionAsesorService`, `HistorialService`, `AutorizacionService` | `servicios/` |
| `SolicitudRepository`, `ValidacionRepository`, `RevisionRepository`, `AlmacenArchivos` | `infraestructura/repositorios.py`, `almacen_archivos.py` |
| `Solicitud`, `DocumentoSolicitud`, `ArchivoDocumento`, `ValidacionAcademica`, `RequisitoValidado`, `RevisionAsesor`, `CriterioEvaluado`, `Usuario`, `InformacionAcademica` | `dominio/entidades.py` |
| `FlujoSolicitud` | `dominio/estados.py` |
| `PuertoInformacionAcademica`, `AdaptadorAcademicoSimulado`, `PuertoIdentidad` | `infraestructura/puertos.py` |

## 4. Flujos alternos y de excepción implementados

| Flujo | Dónde |
|---|---|
| CU-02 FA-1 borrador, FA-2 cancelar (confirmación) | `SolicitudService.guardar_borrador`; `data-confirmar` en `solicitud_form.html` |
| CU-02 FE-1 incompleto, FE-2 formato, FE-3 tamaño | `Solicitud.validar_completitud`; `DocumentoService.adjuntar` |
| CU-03 FA-1 borrador, FA-2 cancelar, FA-3 rechazar | `ValidacionAcademicaService.guardar_borrador`, `rechazar` |
| CU-03 FE-1 sin estado, FE-2 pendientes o no cumplidos, FE-3 consulta académica | `ValidacionAcademicaService.validar`, `_consultar` |
| CU-05 FA-1 borrador, FA-2 cancelar, FA-3 correcciones | `RevisionAsesorService.guardar_borrador`, `solicitar_correcciones` |
| CU-05 FE-1 sin asignadas, FE-2 criterios sin evaluar, FE-3 observaciones, FE-4 criterios pendientes | `revision_lista.html`; `RevisionAsesorService.aprobar`; `RevisionAsesor.validar_observaciones` |
