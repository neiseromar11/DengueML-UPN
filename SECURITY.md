# Política de Seguridad – DengueML-UPN

## Alcance

Este documento establece los lineamientos de seguridad del prototipo académico **DengueML-UPN**, desarrollado como parte del proyecto de capstone de la Universidad Privada del Norte (UPN).

## Principios de Seguridad

- **Mínimo privilegio**: cada componente accede únicamente a los recursos que necesita.
- **No almacenar secretos en Git**: las credenciales y claves se gestionan exclusivamente mediante variables de entorno.
- **Trazabilidad**: todas las acciones relevantes del sistema se registran en logs de auditoría.
- **Respaldo**: se mantiene un plan de respaldos para datos y archivos críticos.
- **Separación datos/código**: los datasets no se versionan en el repositorio.
- **Protección de información epidemiológica**: el dashboard trabaja con información agregada por distrito y semana epidemiológica; no se expone información personal de pacientes.

## Gestión de Secretos

| Archivo | Propósito | ¿Se versiona? |
|---|---|---|
| `.env` | Variables de entorno con valores reales | ❌ No (ignorado por `.gitignore`) |
| `.env.example` | Plantilla de referencia sin secretos | ✅ Sí |

**Reglas:**
- Nunca escribir contraseñas, tokens o claves directamente en el código fuente.
- Usar `python-dotenv` o `os.getenv()` para leer configuración.
- Revisar cada commit antes de hacer push para evitar exposición accidental.

## Auditoría y Trazabilidad

El módulo `src/audit.py` registra los siguientes eventos:

| Evento | Descripción |
|---|---|
| `APP_INICIO` | Inicio de la aplicación |
| `FILTROS_ACTUALIZADOS` | Actualización de filtros del dashboard |
| `CARGA_DATOS` | Carga del dataset epidemiológico |
| `PROCESAMIENTO_ETL` | Ejecución del pipeline de procesamiento |
| `PREPARACION_MODELADO` | Preparación de datos para modelado |
| `EXPORTACION_REPORTE` | Descarga o exportación de reporte |
| `ERROR` | Error relevante del sistema |

**Los logs no deben contener:** contraseñas, tokens, claves secretas, DNI, datos personales ni información sensible.

Los archivos de log se almacenan en `logs/` (directorio ignorado por Git).

## Protección de Datos

- El dashboard presenta únicamente información **agregada** por distrito y semana epidemiológica.
- No se almacenan ni exponen datos personales de pacientes.
- El dataset fuente (`datos_abiertos_vigilancia_dengue.csv`) no se versiona en el repositorio.

## Dependencias

- Las dependencias del proyecto se especifican en `requirements.txt`.
- Se recomienda revisarlas periódicamente para identificar vulnerabilidades conocidas.
- Comando de revisión sugerido: `pip audit` o `safety check`.

## Autenticación y Control de Acceso

> **Estado actual:** Autenticación basada en roles planificada para una versión posterior.

El prototipo actual no implementa un sistema de autenticación real. Este control se encuentra documentado como pendiente en el backlog del proyecto.

## Manejo de Errores

- Los mensajes de error mostrados al usuario son genéricos y comprensibles.
- No se exponen al usuario: rutas internas, stack traces, secretos ni información del sistema operativo.
- Los detalles técnicos se registran únicamente en los logs locales.

## Procedimiento de Respuesta a Incidentes

1. **Identificar** el incidente y su alcance.
2. **Contener** el impacto (aislar componentes afectados).
3. **Registrar** evidencia (logs, capturas, descripción).
4. **Corregir** la causa raíz.
5. **Restaurar** el servicio desde respaldos si es necesario.
6. **Documentar** lecciones aprendidas.

---

*Documento mantenido por el equipo DengueML-UPN · Universidad Privada del Norte*
