# Piloto de predicción provincial

## Conclusión

El CSV permite construir series provinciales de registros de dengue. En este piloto, XGBoost no superó la persistencia (repetir la última semana). No se recomienda ampliar el alcance del proyecto basándose en una supuesta mejora predictiva automática. El resultado no demuestra que todo modelo provincial sea inviable: corresponde a una configuración fija y sin clima.

## Fuente y alcance real

Se leyeron 1.029.421 filas de 2000–2024, con registros correspondientes a 124 códigos provinciales. Esto no certifica cobertura de todas las provincias ni vigilancia completa. El archivo contiene diagnósticos A97.0/A97.1/A97.2, pero no un campo de confirmación; se predice el conteo de registros, no exclusivamente casos confirmados. Tampoco se estima incidencia por población.

Se agruparon filas por los primeros cuatro dígitos del UBIGEO y semana. No se eliminaron filas idénticas: sin identificador de caso no se puede determinar que sean duplicados. Por ello no se certifica que cada registro represente una persona única. Las combinaciones sin filas se completaron con cero registros, sin interpretar eso como ausencia demostrada de enfermedad.

Se fijaron 110 provincias presentes antes de 2023; las otras 14 se documentan en el catálogo, pero quedan fuera de la evaluación. Es un piloto multirregional provincial, no un sistema validado para todo el Perú. No se armonizaron posibles cambios históricos de límites administrativos con un catálogo externo.

Se auditó todo el archivo y se entrenó desde 2015. Se detectaron 81 registros de 2009-SE53 incompatibles con la convención temporal actual del proyecto: se documentaron y no entraron al entrenamiento; no se corrigieron silenciosamente.

## Diseño

24 cortes temporales: SE04,08,...,48 de 2023 y 2024. Horizontes de 2, 3 y 4 semanas, 110 provincias: 7.920 predicciones por alternativa. Entrenamiento expansivo, con etiquetas limitadas al corte. XGBoost Poisson directo, 100 árboles y profundidad 3; características de casos anteriores, estacionalidad y provincia. Sin búsqueda posterior de parámetros. Protocolo guardado antes del ajuste.

## Resultados

MAE y RMSE en registros por provincia-semana; no representan porcentajes de exactitud.

| Alternativa | MAE | RMSE |
|---|---:|---:|
| Repetir última semana | **27,1227** | **169,9832** |
| XGBoost | 31,8534 | 246,4396 |
| Promedio de cuatro semanas | 33,9449 | 209,4447 |
| Siempre cero | 48,0845 | 280,4068 |
| Referencia de 52 semanas | 54,3466 | 270,6691 |

El MAE de XGBoost fue aproximadamente 17,44% mayor que persistencia. Superó a persistencia en 22 de 110 provincias (20%), sin empates. No pasó los criterios preestablecidos. Las métricas macro por provincia se incluyen; como todas tienen igual número de observaciones, el MAE macro coincide con el global.

| Horizonte | MAE XGBoost | MAE última semana |
|---|---:|---:|
| 2 semanas | 28,4080 | 19,4375 |
| 3 semanas | 31,6542 | 27,1750 |
| 4 semanas | 35,4981 | 34,7557 |

El error también fue mayor en los tres horizontes. En semanas con registros positivos, el MAE fue 53,0410 para XGBoost y 45,9585 para persistencia.

La diferencia MAE XGBoost menos persistencia fue +4,7307, con intervalo bootstrap por bloques del 95% [-2,8123; 13,9095]. Incluye cero: no se afirma una diferencia estadística concluyente, pero tampoco existe evidencia para declarar superior al candidato. La ventaja media frente al promedio de cuatro semanas tampoco fue concluyente según ese intervalo. Los intervalos no resuelven problemas de calidad o cobertura de la fuente.

## Qué significa para el proyecto

Más registros y una escala territorial más amplia no garantizan mayor capacidad predictiva. Estos errores no deben compararse directamente con el MAE distrital anterior: cambian objetivo, escala, territorios y periodos.

Si se debe cerrar el avance pronto, conservar el dashboard actual y adjuntar este piloto como evidencia de evaluación de alternativas. Una migración provincial requeriría un objetivo de alcance propio, validación de cobertura territorial y selección de modelos con cortes internos separados; este piloto por sí solo no la justifica.

## Integridad y reproducibilidad

Código: `scripts/experimento_provincias.py`. Esta carpeta incluye protocolo, auditoría, catálogo, panel agregado, predicciones, métricas por año/horizonte/provincia, métricas macro e intervalos. Se verificaron 20 archivos protegidos antes y después y todas las huellas coincidieron. No se modificaron la fuente, el código del dashboard, los datos activos ni el modelo publicado.
