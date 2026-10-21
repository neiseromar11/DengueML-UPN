# Piloto provincial v1
Fijado antes del ajuste. Objetivo: conteo semanal de registros del CSV, no confirmados ni incidencia por población.
Entrenar desde 2015, evaluar 2023 y 2024: orígenes SE04,08,...,48 de cada año; horizontes 2,3,4.
Territorios: códigos provinciales con registros antes de 2023. Provincias que aparecen después se documentan pero no se evalúan.
Una fila equivale a un registro; no eliminar filas idénticas sin identificador de caso. No se certifica que cada fila represente un paciente único.
Completar combinaciones sin filas con cero registros, no afirmar ausencia de transmisión o vigilancia completa.
Mismo modelo fijo XGBoost Poisson directo por horizonte: 100 árboles, profundidad3, eta0.05, min_child_weight5, lambda10, subsample0.8, colsample0.8, seed42, hist, n_jobs2.
Rezagos 0,1,2,3,7,11,25,51; medias4,8,12; ceros12; estacionalidad objetivo; provincia one-hot. Sin clima ni búsqueda de parámetros.
Entrenamiento expansivo: toda etiqueta debe ser <= corte. Controles persistencia, promedio4, estacional52 y cero.
Reportar MAE/RMSE por horizonte/año/provincia, error positivo, promedio macro provincial y porcentaje de provincias donde mejora.
Bootstrap pareado de diferencias MAE por origen, bloques móviles4, 2000 remuestreos seed42.
Criterio exploratorio: >=2% mejor MAE que cada control, sin empeorar ningún horizonte frente a persistencia. No publicar aunque cumpla.
No comparar MAE absoluto con los experimentos distritales: cambian escala, población, objetivo y periodo. No garantiza cobertura de todas las provincias del Perú.
La convención temporal se valida para 2015 en adelante; discrepancias anteriores se registran y no se corrigen silenciosamente.
