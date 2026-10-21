# Resultado del experimento climático v3

Fecha: 20 de octubre de 2026. Experimento separado; no se publicó ni sustituyó ningún modelo.

## Conclusión

El Excel permite investigar una señal climática útil para estimar cantidades: añadir clima rezagado redujo el MAE un 19,89% respecto al MISMO XGBoost sin clima. No cumplió todos los criterios fijados: la sensibilidad bajó del 82,40% al 80,58%. Por tanto, no se recomienda incorporar esta configuración al dashboard todavía.

La mejora global frente a las reglas actuales reentrenadas fue del 2,54%, pero su intervalo de incertidumbre incluye ausencia de mejora. No es evidencia suficiente de superioridad sobre el sistema vigente. Esta comparación reentrena las reglas sobre casos confirmados; no compara directamente contra el modelo publicado, cuyo objetivo son casos notificados.

## Diseño realizado

- 49 cortes temporales, 14 distritos y horizontes de 2, 3 y 4 semanas: 2.058 predicciones por alternativa.
- Entrenamiento expansivo con objetivos conocidos hasta cada corte; igual arquitectura, parámetros y filas en ambas alternativas.
- Clima observado con rezagos de 2, 3 y 5 semanas. Sin datos climáticos futuros ni columnas de normales climáticas.
- 5.632 sustituciones de celdas de temperatura/humedad en cuatro distritos por el grupo LIMA CENTRO, misma semana. Detalle en `sustituciones_territoriales.csv`.
- Los cinco controles del experimento v2 se reutilizaron después de comprobar exactamente claves, objetivos e imputación; se verificó la huella del panel fuente.
- Parámetros fijados previamente; no se ajustaron después de conocer el resultado.

## Resultados globales

MAE y RMSE expresados en casos por distrito-semana, no porcentajes de exactitud.

| Alternativa | MAE | RMSE | MAE cuando hubo casos | Sensibilidad* | Falsos positivos* |
|---|---:|---:|---:|---:|---:|
| XGBoost sin clima | 5,9681 | 37,0656 | 20,4139 | 82,40% | 34,51% |
| XGBoost con clima | 4,7808 | 34,9762 | 16,3511 | 80,58% | 29,13% |
| Reglas actuales reentrenadas | 4,9054 | 32,8440 | 17,8582 | 63,34% | 4,78% |
| Repetir última semana | 5,0214 | 31,9801 | 18,0236 | 70,78% | 12,14% |
| Promedio de cuatro semanas | 6,5508 | 43,1463 | 23,4360 | 74,77% | 14,27% |
| Siempre cero | 7,4261 | 53,8161 | 27,7368 | 0,00% | 0,00% |
| Estacional de 52 semanas | 11,3226 | 63,1773 | 34,2559 | 32,85% | 20,04% |

*Presencia de casos: real >=1 y predicción esperada >=0,5. No es clasificación de brotes ni validación de los niveles de riesgo. Falsos positivos = FP/(FP+TN). El clima produjo 444 verdaderos positivos, 107 falsos negativos, 439 falsos positivos y 1.068 verdaderos negativos. Su precisión positiva fue 50,28%.

## MAE por horizonte

| Horizonte | Sin clima | Con clima | Reglas actuales | Última semana |
|---|---:|---:|---:|---:|
| 2 semanas | 4,9143 | 4,1485 | 3,8140 | 3,7070 |
| 3 semanas | 6,1637 | 4,8800 | 4,8021 | 4,8397 |
| 4 semanas | 6,8263 | 5,3139 | 6,1000 | 6,5175 |

El clima mejoró los tres horizontes frente al mismo modelo sin clima, pero frente a las reglas actuales y persistencia la ventaja se concentró en cuatro semanas. El RMSE global fue peor que el de ambos controles: persisten errores grandes.

## Criterios preestablecidos e incertidumbre

Cumplió cuatro de cinco criterios de aporte climático: mejora MAE >=2%, ningún horizonte empeora, MAE positivo no empeora y aumento de falsos positivos <=2 puntos porcentuales. Incumplió sensibilidad no inferior: hubo 10 falsos negativos adicionales frente a sin clima.

Bootstrap pareado con bloques móviles de cuatro orígenes, 2.000 remuestreos, semilla 42. Diferencia = MAE con clima menos referencia; negativo favorece al clima:

- Frente a sin clima: -1,1873; intervalo percentil 95% [-2,7137; -0,2322].
- Frente a reglas actuales: -0,1246; intervalo percentil 95% [-1,6594; 0,9105].

No se modifican los criterios para declarar éxito después de observar resultados.

## Límites de interpretación

1. Los cortes ya se analizaron en v2: evaluación exploratoria retrospectiva, no validación prospectiva independiente.
2. 1.491 de 2.058 objetivos fueron imputados como cero bajo hipótesis provisional. No se ha confirmado documentalmente el significado de todos los vacíos. Las métricas de positivos y objetivos informados también se guardaron para facilitar el examen de esta limitación.
3. Clima territorial sustituto no equivale a medición distrital. Los rezagos no garantizan disponibilidad histórica en tiempo real; pueden existir revisiones de la fuente.
4. Las métricas no equivalen a una predicción cercana al 100% ni validan alertas sanitarias.

## Decisión y siguiente paso

Conservar el Excel y este experimento como evidencia de aporte climático potencial. Mantener el dashboard original. Congelar esta configuración para una evaluación futura sobre semanas nuevas y consolidadas, con definición de vacíos y registro de disponibilidad de las variables. No seguir ajustándola contra estos mismos resultados para forzar una victoria.

Si se prioriza estimación de cantidades frente a presencia de casos, esa decisión y sus criterios deben establecerse antes de la siguiente evaluación, sin reinterpretar esta como aprobada.

## Reproducibilidad e integridad

Script: `scripts/experimento_confirmados_clima_v3.py`. Protocolo: `PROTOCOLO.md`. Predicciones, métricas por distrito/año/horizonte, tiempos, sustituciones e intervalos quedan en esta carpeta. La ejecución se protege contra sobrescritura accidental.

Se compararon las huellas SHA-256 de 24 archivos protegidos antes y después: código de src, referencia activa, modelo publicado, datos activos, fuente Excel, panel candidato y fuentes experimentales. Todas coincidieron. El entrenamiento quedó en memoria y no se publicaron archivos de modelo.
