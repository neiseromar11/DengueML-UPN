# Auditoría de datos candidatos: casos confirmados

Fecha de preparación: 20 de octubre de 2026.

## Estado

Preparado para revisión, **no aprobado para entrenamiento ni publicación**.
El modelo, el dashboard y el puntero `models/actual.json` permanecen intactos.
La fuente original tampoco se modificó.

## Qué contiene

- `panel_candidato.csv`: 6,412 filas, 14 distritos seleccionados por UBIGEO y
  458 semanas desde 2018-SE01 hasta 2026-SE40.
- `filas_posteriores_al_corte.csv`: 168 filas posteriores al último conteo
  disponible, separadas para no tratarlas como observaciones.
- `cobertura_distrital.csv`: conteos disponibles, ceros explícitos, faltantes,
  rachas de semanas con conteos y disponibilidad del clima por distrito.
- `cobertura_anual.csv`: sumas de valores disponibles, no totales certificados.
  Los años sin valores se mantienen vacíos.
- `cobertura_semanal.csv`: cobertura conjunta de los 14 distritos.
- `metadata.json`: huella del origen, corte inferido, reglas y huellas de salidas.

## Hallazgos

Los 837 conteos informados conservan la etiqueta CONFIRMADO; 28 son ceros
explícitos y 809 son positivos. Hay 5,575 conteos vacíos (86.95 % del panel).
Solo 20 semanas tienen conteos informados para los 14 distritos.

No se detectaron duplicados de distrito-año-semana ni conteos negativos o
fraccionarios. Se contrastó cada conteo y cada vacío con el Excel original.
El calendario exportado hasta el corte tiene continuidad de siete días según
la convención actual del proyecto, incluidas las semanas 53 de 2020 y 2025.
Esta comprobación técnica no sustituye la confirmación del calendario de la fuente.

2018 y 2019 carecen de conteos. No se interpretan como años sin dengue.
El último conteo presente es 2026-SE40: no acredita que esa semana esté
consolidada ni que sea el corte oficial de publicación.

Breña, Magdalena, Pueblo Libre y San Miguel no tienen temperatura ni humedad.
La temperatura y humedad disponibles terminan en 2026-SE39; la precipitación
llega a 2026-SE40. Los campos `*_clima` se conservan como información de origen,
pero no se seleccionan como características: falta documentar su significado
y periodo de referencia.

La columna `Provincia` del Excel identifica agrupaciones como LIMA CENTRO,
no la provincia administrativa que espera el ETL anterior.

## Interpretación y uso

`casos_confirmados` es un conteo agregado semanal. **No contar las filas como
casos ni introducir este archivo en el ETL actual de microdatos.**
Los estados distinguen positivo informado, cero explícito y faltante por aclarar.
La hoja no basta para decidir si un vacío significa cero notificaciones,
omisión en la exportación o ausencia de información.

No rellenar con cero, interpolar el objetivo, ni eliminar vacíos para presentar
semanas separadas como consecutivas. No unir este objetivo directamente con
conteos de notificados del modelo anterior.

## Decisiones pendientes antes de entrenar

1. Obtener la documentación o respuesta de la fuente sobre:
   - ¿Una celda vacía en Casos significa ausencia de notificaciones o dato desconocido?
   - ¿Por qué existen tanto ceros explícitos como celdas vacías?
   - ¿Los conteos se asignan por residencia, lugar de infección o notificación?
   - ¿Qué fecha determina la semana y cuál es el calendario epidemiológico?
   - ¿Qué semanas están consolidadas y cómo se registran revisiones retrospectivas?
2. Con esa evidencia, fijar una política de faltantes documentada. Si no existe,
   mantenerlos como desconocidos y buscar una serie con cobertura acreditada.
3. Definir periodos de desarrollo y evaluación final antes de ajustar modelos.
   2025–2026 son candidatos temporales recientes, pero no se aprueban todavía:
   no conocemos la cobertura real de los vacíos ni la consolidación de semanas.
4. Comparar modelos sin clima primero. Evaluar siempre cero, persistencia,
   promedio reciente y referencia estacional junto a XGBoost.
5. Para incorporar clima, utilizar información disponible al origen del
   pronóstico, con rezagos y política de faltantes ajustada solo en entrenamiento.
   No utilizar clima futuro observado ni normales calculadas con información
   posterior al corte de evaluación.

No se entrenó ni se calculó una nueva precisión. Preparar datos no demuestra
mejora predictiva ni garantiza una precisión cercana al 100 %.

## Reproducibilidad

El script `scripts/preparar_confirmados.py` identifica la versión por la huella
del Excel y evita sobrescribir versiones existentes. Requiere pandas y openpyxl.
Se ejecuta desde cualquier carpeta pasando la ruta del script y, opcionalmente,
`--fuente` con otro archivo compatible. Una nueva descarga con contenido
diferente genera otra carpeta candidata. No publica versiones activas.
