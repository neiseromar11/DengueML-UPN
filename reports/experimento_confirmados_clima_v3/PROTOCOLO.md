# Experimento v3: aporte del clima

Fijado antes de ejecutar, 20 de octubre de 2026. Evaluación exploratoria, no publicación.

## Comparación

Modelo fijo: tres XGBRegressor Poisson directos (horizontes 2, 3 y 4), profundidad 2,
150 árboles, learning_rate 0.05, min_child_weight 5, reg_lambda 10, subsample 0.8,
colsample_bytree 0.8, semilla 42 y un hilo. Sin búsqueda de hiperparámetros.

Se ajustan dos versiones idénticas salvo las características:
- Sin clima: casos y rezagos 0,1,2,3,7,11,25,51 desde el origen; medias 4,8,12;
  ceros e imputados de últimas 12 semanas; distrito binario y estacionalidad del objetivo.
- Con clima: las mismas más tmean, tmax, tmin, humr y ptot en t−2, t−3 y t−5.
  Se añaden indicadores que identifican los valores sustituidos territorialmente.

No se usan columnas *_clima ni mediciones del periodo futuro. Se adopta un retraso
conservador de dos semanas, pero la exportación no permite certificar la fecha
real de disponibilidad histórica ni descartar revisiones de los reanálisis.

## Cobertura territorial

Para Breña, Magdalena del Mar, Pueblo Libre y San Miguel, las temperaturas y
humedad faltantes pueden sustituirse por la fila LIMA CENTRO de la hoja Provincia
en la MISMA semana. Este grupo territorial no se presenta como medición distrital.
La precipitación conserva su valor distrital. Otros faltantes permanecen NaN,
tratados de forma nativa por XGBoost. No se interpola con semanas posteriores.
Toda sustitución se registra con distrito, semana, variable y valor utilizado.
La alternativa territorial es una aproximación experimental, no una medida equivalente.

## Datos y evaluación

Casos confirmados del panel candidato 2020–2026-SE40. Vacíos tratados como cero
registros SOLO como hipótesis provisional, con su indicador conservado. No se
modifican las fuentes originales. Los 49 orígenes externos del protocolo v2 se
reutilizan únicamente para comparación retrospectiva; sus resultados ya son conocidos.
Los objetivos evaluados llegan a 2026-SE39. No se afirma independencia prospectiva.

Cada fila de entrenamiento con origen s y objetivo s+h solo entra si s+h<=t.
Ambas versiones tienen las mismas filas y objetivos. Se reentrenan en cada origen.
Como controles se reutilizan las predicciones externas v2 de cero, persistencia,
promedio de cuatro semanas, estacional 52 y reglas actuales reentrenadas. Se comprueba
la coincidencia exacta de claves, valores reales, imputación y origen de datos.

## Métricas y decisión

Reportar MAE/RMSE globales y por horizonte, año y distrito; error positivo y sobre
objetivos informados; TP, FP, TN, FN, sensibilidad y tasa de falsos positivos con
umbral común de conteo esperado >=0.5. No son métricas de detección de brotes.

Aporte del clima: MAE al menos 2% menor que sin clima, sin empeorar ningún horizonte
ni el MAE positivo; sensibilidad no inferior y tasa de falsos positivos no mayor
en más de 2 puntos porcentuales. Si no cumple, no se recomienda incorporar clima
con esta configuración. Comparación pareada de diferencias MAE con bloques de
cuatro orígenes, 2,000 remuestreos y semilla 42. Intervalo que cruza cero implica
evidencia no concluyente. No cubre incertidumbre de los datos ni del supuesto de ceros.

Además, contrastar mejora global >=2% frente a CADA referencia simple y reglas
actuales. Cumplir la comparación contra sin clima por sí sola no justifica reemplazo.
Aunque cumpla, no publicar: quedan pendientes semántica de vacíos, disponibilidad
del clima en tiempo real y evidencia en un periodo nuevo.

No cambiar configuración ni repetir buscando una mejora sobre estos resultados.
No escribir en src, models, datos activos ni el dashboard. Verificar huellas al terminar.
