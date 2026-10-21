# Protocolo v2: predicción directa y modelo de dos etapas

Estado: **diseñado, no ejecutado**. Fecha: 20 de octubre de 2026.
No autoriza reemplazar el modelo del dashboard.

## 1. Pregunta y objetivo

¿Puede un modelo directo por horizonte reducir el error de conteos y mejorar
la identificación de semanas con casos, frente a referencias simples y al
comparador con reglas actuales?

Objetivo: número de casos **confirmados registrados** por distrito a 2, 3 y 4
semanas. Ámbito: los 14 distritos de DIRIS Lima Centro.
La presencia de uno o más casos NO equivale a un brote ni a riesgo sanitario alto.

## 2. Datos y supuesto explícito

Fuente candidata: `data/candidates/confirmados-3c5551eb8fa2/panel_candidato.csv`.
Usar 2020-SE01 a 2026-SE40. Excluir 2018–2019 por ausencia de conteos informados.
No usar filas posteriores a SE40.

Escenario principal provisional: vacíos del objetivo dentro del periodo
se interpretan como cero registros. Conservar la columna indicadora de imputación
y la versión sin imputar; nunca sobrescribir el Excel o panel candidato.

Escenario de sensibilidad: calcular también errores sobre objetivos explícitamente
informados y sobre objetivos positivos. Esta sensibilidad no valida la hipótesis:
los predictores pueden seguir dependiendo de ceros imputados y el subconjunto
informado sobrerrepresenta presencia de casos.

El último conteo disponible no demuestra que el periodo esté consolidado.
Las conclusiones quedan condicionadas a la exportación disponible, susceptible
de revisiones posteriores. No entrenar un modelo operativo con esta aprobación.

## 3. Información disponible en cada origen

En el origen t, usar exclusivamente casos hasta t:

- Caso en t y rezagos de 1, 2, 3, 7, 11, 25 y 51 semanas respecto de t.
- Promedios de las últimas 4, 8 y 12 semanas hasta t.
- Número de ceros e indicador de valores imputados en las últimas 12 semanas.
- Distrito codificado en columnas binarias, sin codificación basada en el objetivo.
- Seno y coseno de la semana epidemiológica objetivo t+h, conocida de antemano.

No usar el conteo de t+1 para pronosticar t+2. No utilizar observaciones climáticas
futuras ni agregar los casos futuros de distritos vecinos.
No incluir clima ni normales `*_clima` en esta comparación inicial.

Para cada horizonte h, una fila de entrenamiento tiene características calculadas
en su origen s y objetivo en s+h. Solo se admite si s+h <= t. Este límite se
aplica también a cualquier selección interna. No basta con filtrar s <= t.

## 4. Comparadores y candidatos fijados

Referencias, con la misma información de origen:

1. Siempre cero.
2. Persistencia: repetir el conteo de t.
3. Media de las cuatro semanas hasta t.
4. Estacional: conteo en t+h−52, aclarando el desfase en años de 53 semanas.
5. XGBoost con las reglas actuales, reentrenado con casos confirmados hasta t.
   Es un comparador experimental, no el archivo del modelo publicado.

Candidatos nuevos (cuatro configuraciones completas):

- Directo Poisson: un XGBRegressor por horizonte, profundidad 2.
- Directo Poisson: un XGBRegressor por horizonte, profundidad 3.
- Dos etapas: un XGBClassifier para P(Y>0) y un XGBRegressor Poisson entrenado
  solo en objetivos positivos, por horizonte; profundidad 2.
- Dos etapas: la misma estructura, profundidad 3.

Parámetros restantes fijos: 150 árboles, learning_rate=0.05, min_child_weight=5,
reg_lambda=10, subsample=0.8, colsample_bytree=0.8, random_state=42, n_jobs=1.
Clasificador: binary:logistic; sin balanceo de clases automático.
No seleccionar parámetros adicionales tras observar la evaluación externa.

En dos etapas, el conteo esperado será P(Y>0) multiplicado por la cantidad
condicional estimada, limitada inferiormente a 1 por coherencia con Y>0.
No forzar todo el pronóstico a cero porque P(Y>0) sea inferior a 0.5.
Si en un ajuste hay una sola clase, usar probabilidad constante igual a esa clase;
si no hay positivos, cantidad condicional 1 y probabilidad 0. Registrar el caso.
Los conteos esperados se conservan sin redondear para MAE/RMSE.

## 5. Separación temporal y selección anidada

La evaluación es retrospectiva y exploratoria. Ya se inspeccionaron resultados
de 2025–2026 en v1; no se presenta ese periodo como una prueba nueva o ciega.

Orígenes externos: bloques sucesivos de cuatro semanas cuyo primer objetivo
es 2023-SE01, hasta el último bloque completo antes o en 2026-SE40.
Los objetivos finales llegan a 2026-SE39. No se fuerza un bloque incompleto.

Para cada origen externo t:

1. Reservar sus objetivos t+1...t+4, sin usarlos para seleccionar.
2. Usar los últimos ocho orígenes internos separados por cuatro semanas, cada
   uno con al menos 52 semanas previas y con todos sus objetivos <= t.
3. Reentrenar cada candidato en cada origen interno con sus etiquetas disponibles.
4. Seleccionar una configuración conjunta para los tres horizontes por menor
   MAE medio interno en pasos 2–4. En empate a seis decimales: menor MAE en
   objetivos positivos; después menor profundidad; después modelo directo.
5. Reentrenar la configuración seleccionada hasta t y pronosticar t+2, t+3, t+4.
6. Guardar todas las predicciones externas sin cambiar la regla de selección.

También se elige la referencia simple de menor MAE en los orígenes internos,
sin utilizar sus resultados externos. Reportar por separado cada referencia.
Se reutilizan observaciones pasadas cuando avanza el tiempo: esto evalúa una
estrategia de actualización, no un único modelo congelado durante años.

El archivo `cortes.json` enumera los orígenes antes de ejecutar el experimento.
No informar un único corte elegido después de ver cuál produce mejores métricas.

## 6. Métricas

Sobre los mismos pares distrito-semana-horizonte para todos los métodos:

- MAE principal, media balanceada de los pasos 2, 3 y 4.
- MAE y RMSE por horizonte, distrito y año.
- MAE sobre objetivos positivos y sobre objetivos explícitamente informados.
- Fracción de objetivos imputados en cada resumen.
- Número de semanas positivas pronosticadas por debajo de 0.5 casos.

Diagnóstico de presencia de casos: real positivo si Y>=1; predicción positiva
si conteo esperado>=0.5, para TODOS los métodos. El umbral es un criterio técnico
de comparación, no una alerta sanitaria. Informar TP, FP, TN, FN, sensibilidad,
precisión positiva y tasa de falsos positivos. Métricas con denominador cero:
no disponibles, nunca convertidas a cero.

Para el clasificador de dos etapas, reportar adicionalmente Brier score sobre
su probabilidad de presencia. No confundir probabilidad con cantidad esperada.
No convertir MAE en “porcentaje de precisión”.

## 7. Criterios de aceptación fijados

Son criterios de ingeniería exploratorios, no umbrales sanitarios validados.

Para considerar al procedimiento candidato prometedor debe cumplir TODOS:

1. MAE global al menos 2 % menor que cada referencia simple y que el comparador
   reentrenado con reglas actuales.
2. No empeorar el MAE en ninguno de los pasos 2, 3 y 4 frente al comparador con
   reglas actuales ni frente a la referencia seleccionada internamente.
3. No empeorar el MAE en objetivos positivos frente a esos dos comparadores.
4. Aumentar la sensibilidad de presencia de casos al menos 5 puntos porcentuales
   frente al comparador con reglas, sin aumentar su tasa de falsos positivos
   más de 2 puntos porcentuales.
5. Informar todos los distritos y años, incluidos aquellos donde empeora.

Si una referencia tiene MAE cero, no puede acreditarse una reducción relativa
del 2 %: informar empate o deterioro, no dividir entre cero.
Si una métrica necesaria es indefinida, el criterio queda inconcluso.

Estimar incertidumbre de las diferencias de MAE con remuestreo pareado de
bloques de cuatro orígenes externos consecutivos, preservando juntos distritos
y horizontes; 2,000 réplicas, semilla 42. Si el intervalo del 95 % de la diferencia
incluye cero, describir la mejora como no concluyente. No asumir que este
intervalo cubre el sesgo por imputación o cambios en la vigilancia.

Superar estos criterios NO autoriza publicación: seguiría pendiente confirmar
la semántica de vacíos y obtener evidencia en un periodo nuevo.

## 8. Entregables de la futura ejecución

- Predicciones internas y externas, configuraciones seleccionadas y tiempos.
- Métricas completas y diferencias frente a comparadores.
- Desglose entre objetivos explícitos e imputados.
- Resultado “cumple”, “no cumple” o “inconcluso” para cada criterio.
- Limitaciones y cambios de cobertura, sin prometer precisión cercana al 100 %.
- Huellas de entrada y del puntero activo antes y después.

## 9. Estado actual y siguiente acción

Este documento fija el experimento. No contiene nuevos resultados ni modifica
los de v1. El paso siguiente es implementar y ejecutar exactamente este protocolo
en una carpeta experimental nueva, sin sustituir el modelo actual.
