# Dos escenarios para los vacíos de Casos

Se completaron ambos escenarios con 49 cortes, 14 distritos y horizontes de 2, 3 y 4 semanas. Solo se rellenaron celdas ausentes; se conservaron los valores informados, incluidos ceros explícitos. No se modificaron el Excel ni el dashboard.

## Comparación principal sobre objetivos informados

Las mismas 567 observaciones con un valor explícito en ambos escenarios. MAE en casos, menor es mejor.

| Modelo | Vacíos = 0 | Vacíos = 1 |
|---|---:|---:|
| XGBoost con clima | 15,9034 | 15,6473 |
| XGBoost sin clima | 19,8529 | 19,4784 |
| Última semana | 17,5256 | 17,2610 |
| Promedio de cuatro semanas | 22,7778 | 22,5044 |

Con clima, el escenario 1 redujo el MAE aproximadamente 1,61% frente al escenario 0 en este subconjunto. El RMSE pasó de 66,6068 a 62,8237. No se calculó significación estadística de esta diferencia y no se declara superioridad concluyente. El subconjunto informado está sesgado hacia semanas con casos; no permite caracterizar todas las semanas ausentes.

## Evaluación con objetivos supuestos

Sobre las 2.058 filas por modelo, incluyendo objetivos rellenados, el MAE con clima fue 4,7808 para relleno 0 y 4,7610 para relleno 1. Estas cifras usan objetivos diferentes y NO permiten decidir cuál relleno representa la realidad. Las métricas de presencia de casos sobre objetivos imputados tampoco validan presencia real ni riesgo sanitario.

## Decisión

El supuesto de un caso en cada vacío produjo una pequeña mejora descriptiva en los datos informados. Eso NO demuestra que los vacíos equivalgan a un caso ni justifica cambiar la fuente. Conservar los vacíos originales y ambos escenarios como análisis de sensibilidad; no publicar un modelo por elegir el supuesto con menor error. No se promete exactitud cercana al 100%.

## Verificación y archivos

Ambos escenarios reentrenaron XGBoost con iguales parámetros y cortes, con y sin clima rezagado. Los controles simples se recalcularon según el historial de cada escenario. La comparación principal conservó exactamente los mismos objetivos informados. El escenario 0 reprodujo las predicciones del experimento climático v3. Las huellas de los archivos protegidos coincidieron antes y después en ambas ejecuciones. No se publicaron modelos.

`comparacion.csv` contiene las métricas globales. Cada carpeta `vacios_0` y `vacios_1` contiene predicciones, métricas por horizonte/distrito/año, auditoría de imputación, sustituciones climáticas y huellas de integridad. Código reproducible: `scripts/experimento_vacios_0_1.py`. No sobrescribe ejecuciones existentes.
