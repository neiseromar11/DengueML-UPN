# Contraste de vacíos y ceros

Revisión: 20 de octubre de 2026. No se modificaron los datos candidatos,
el modelo ni la interfaz. No se imputaron valores ni se entrenó un modelo.

## Evidencia comprobada en los archivos

Se unieron las hojas Distrito de las exportaciones TOTAL y CONFIRMADO
por UBIGEO, año y semana, verificando correspondencia uno a uno.
Para los 14 distritos de Lima Centro:

- Las ubicaciones de los valores vacíos en Casos coinciden exactamente.
- Los 28 ceros explícitos de CONFIRMADO tienen un valor positivo en TOTAL.
- En las 197 semanas con valores comparables, la suma de los conteos
  distritales informados coincide con el valor de LIMA CENTRO en la hoja
  Provincia del archivo CONFIRMADO. Esto es consistencia interna, no una
  verificación independiente de cobertura.
- En el solapamiento 2018–2024 no se encontró una combinación UBIGEO-año-semana
  con TOTAL vacío y registros presentes en el CSV histórico aportado.
  La ausencia de registros en ambas fuentes no certifica notificación negativa.

## Interpretación

El patrón es compatible con una tabla construida a partir de combinaciones
territorio-semana que tienen registros de casos: una combinación con total
positivo podría conservarse aun cuando su número de confirmados sea cero.
Al unir esos conteos con un calendario climático completo, las combinaciones
sin registros podrían quedar vacías.

Esta es una inferencia sobre la exportación, NO una regla documentada por el CDC.
Por tanto, 86.95 % de celdas vacías no significa necesariamente que se haya
perdido 86.95 % de la información de vigilancia. Tampoco demuestra que todas
esas celdas sean ceros epidemiológicos.

## Documentación consultada y límite

La información pública consultada del Observatorio describe filtros, descarga,
frecuencia semanal y procedencia de las variables, pero no se encontró una
definición explícita para las celdas vacías del archivo exportado.

Fuente:
https://app7.dge.gob.pe/maps/clima-salud/

No se dispone de confirmación de que cada distrito haya completado su
notificación durante todas las semanas ni de la regla de unión del exportador.

## Decisión

Mantener los vacíos como desconocidos en la versión candidata.
No presentar esta decisión provisional como una demostración de datos faltantes
en el sistema de vigilancia. No seleccionar exclusivamente semanas positivas:
eso sesgaría el objetivo y eliminaría periodos de baja actividad.

El calendario exportado pasó la comprobación de continuidad con la convención
actual del proyecto. Falta confirmar qué fecha del caso determina la semana,
la asignación territorial y las revisiones posteriores.

Los periodos para entrenamiento y evaluación final siguen pendientes de esta
aclaración. No se publica una precisión ni se aprueba una actualización del modelo.

## Consulta preparada para el responsable de los datos (no enviada)

Asunto: Significado de celdas vacías en exportación semanal de dengue confirmado

Estimado equipo del Observatorio de Clima y Salud / CDC Perú:

Estamos desarrollando un proyecto académico con los conteos semanales de dengue
confirmado de los 14 distritos de DIRIS Lima Centro. Descargamos la base del
Observatorio con las selecciones TOTAL y CONFIRMADO.

En la hoja Distrito observamos que ambas exportaciones tienen celdas vacías
en las mismas combinaciones UBIGEO-año-semana. También existen ceros explícitos
en CONFIRMADO cuando TOTAL es positivo.

Solicitamos precisar:

1. ¿Una celda vacía en Casos significa que no existen registros para esa
   combinación, falta de notificación o ausencia de información disponible?
2. ¿Es correcto tratar esos vacíos como cero casos registrados dentro de un
   periodo consolidado? ¿Qué condiciones o indicadores de cobertura se requieren?
3. ¿Cuál es el último periodo consolidado de esta exportación y cómo se identifican
   las semanas pendientes de actualización?
4. ¿La semana corresponde al inicio de síntomas, notificación u otra fecha?
   ¿El distrito corresponde a residencia, lugar probable de infección u otro criterio?
5. ¿Existe un diccionario de datos y documentación de las columnas climáticas,
   especialmente el periodo de referencia de los campos terminados en _clima?

No requerimos datos personales, únicamente definiciones y conteos agregados.
La aclaración permitirá evitar imputaciones incorrectas y documentar la metodología.

Gracias.
