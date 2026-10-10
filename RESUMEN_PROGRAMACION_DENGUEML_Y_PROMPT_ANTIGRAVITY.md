# DengueML-UPN — Resumen del avance de programación y trabajo pendiente

**Fecha de revisión:** 10/10/2026  
**Repositorio revisado:** `https://github.com/neiseromar11/DengueML-UPN`  
**Estado general:** prototipo funcional con dashboard, ETL inicial, seguridad y trazabilidad básica. El núcleo predictivo XGBoost todavía no está integrado de forma válida al flujo completo.

---

## 1. Resumen ejecutivo

Hasta el momento el proyecto ya tiene una base técnica real y demostrable:

- Repositorio GitHub público y versionado.
- Flujo de ramas `feature/* -> develop -> main` utilizado en el primer incremento.
- Dashboard en Streamlit con diseño responsive.
- Filtros de periodo, distrito, horizonte y semana epidemiológica.
- Visualización histórica de casos.
- Descarga de reporte CSV.
- Pipeline ETL inicial.
- Control de duplicados y reporte de calidad.
- Dataset procesado agregado por distrito, año y semana.
- Auditoría mediante logs.
- Configuración por variables de entorno.
- `.gitignore`, `.env.example` y `SECURITY.md`.
- Validaciones básicas de entradas y manejo seguro de errores.
- Código base para XGBoost.

Sin embargo, el sistema todavía **no debe presentarse como un sistema predictivo terminado**, porque el modelo actual no está conectado correctamente con los datos procesados y el dashboard todavía muestra varias partes demostrativas.

**Estimación cualitativa del software completo:** alrededor de **45–50 %**.  
El avance del primer incremento es mayor, pero todavía falta el componente central de Machine Learning.

---

# 2. Lo que ya está implementado

## 2.1. Repositorio y control de versiones

El repositorio contiene actualmente:

```text
data/processed/
docs/
logs/
reports/
src/
.env.example
.gitignore
DengueML_UPN_dashboard.html
SECURITY.md
requirements.txt
```

Ya se trabajó anteriormente con ramas:

```text
main
develop
feature/dashboard
feature/seguridad
feature/etl-calidad
```

y se integraron cambios mediante Pull Requests.

### Estado

**Implementado.**

---

## 2.2. Dashboard Streamlit

Archivo principal:

```text
src/app_avance.py
```

Actualmente incluye:

- diseño oscuro verde/celeste;
- responsive para 1200 px, 992 px, 768 px y 480 px;
- sidebar;
- selector de periodo;
- selector de distrito;
- horizonte de predicción de 2, 3 o 4 semanas;
- selector de semana límite;
- tarjeta de casos reales;
- tarjeta de predicción marcada como **En desarrollo**;
- tarjeta de riesgo preliminar;
- tarjeta de calidad de datos;
- serie histórica;
- panel de riesgo por distrito;
- distribución de riesgo;
- panel de métricas;
- auditoría y trazabilidad;
- estado del incremento;
- descarga de reporte CSV;
- mensajes de error controlados.

### Estado

**Dashboard visual: avanzado / funcional.**

---

## 2.3. Pipeline ETL y control de calidad

Archivo:

```text
src/data_pipeline.py
```

El ETL actual:

1. carga el archivo epidemiológico;
2. normaliza nombres de columnas;
3. valida columnas mínimas;
4. filtra registros de Lima;
5. calcula faltantes;
6. calcula duplicados exactos;
7. genera un reporte de calidad;
8. elimina duplicados exactos;
9. agrupa por distrito, año y semana;
10. genera `semana_epidemiologica`;
11. controla duplicados lógicos;
12. guarda `data/processed/dengue_processed.csv`;
13. genera `reports/calidad_datos.txt`.

### Último reporte disponible

```text
Registros evaluados de Lima: 122854
Duplicados exactos detectados: 25654
Faltantes en localidad: 39.25 %
Faltantes en localcod: 31.60 %
```

Las columnas epidemiológicas principales como distrito, año y semana no presentan faltantes en ese reporte.

### Estado

**ETL inicial implementado, pero todavía requiere correcciones de alcance y preparación para modelado.**

---

## 2.4. Auditoría

Archivo:

```text
src/audit.py
```

Eventos soportados:

```text
APP_INICIO
FILTROS_ACTUALIZADOS
CARGA_DATOS
PROCESAMIENTO_ETL
PREPARACION_MODELADO
EXPORTACION_REPORTE
ERROR
```

Los eventos se escriben en:

```text
logs/audit.log
```

El código evita registrar contraseñas, tokens, DNI u otros datos sensibles.

### Estado

**Implementado de forma inicial.**

---

## 2.5. Configuración y seguridad

Archivo:

```text
src/config.py
```

Se utilizan variables de entorno para configuración.

Existen:

```text
.env.example
.gitignore
SECURITY.md
```

El proyecto ya define:

- gestión de secretos;
- logs;
- manejo seguro de errores;
- respaldo;
- validación de entradas;
- separación entre datos y código.

### Pendiente de seguridad

Todavía no existe:

- login real;
- autenticación;
- RBAC;
- gestión de usuarios;
- despliegue público endurecido.

### Estado

**Seguridad básica implementada; autenticación pendiente.**

---

# 3. Problemas técnicos que deben corregirse

## PRIORIDAD 1 — El selector de distrito no controla los datos del gráfico

El dashboard muestra un selector:

```python
distrito = st.sidebar.selectbox("Distrito", DISTRITOS_VALIDOS)
```

pero la función de carga filtra internamente siempre:

```python
df_sjl = df[
    (df['departamento'] == 'LIMA') &
    (df['distrito'] == 'SAN JUAN DE LURIGANCHO')
]
```

Por eso, aunque el usuario cambie de distrito, el histórico sigue correspondiendo a San Juan de Lurigancho.

### Corrección necesaria

La función debe recibir `distrito` como argumento o cargar el dataset completo y filtrar después de la selección.

También debe funcionar la opción:

```text
Todos los distritos (DIRIS Lima Centro)
```

---

## PRIORIDAD 2 — El ETL todavía procesa todo Lima y no solo DIRIS Lima Centro

En `data_pipeline.py` actualmente se usa:

```python
df_lima = df[df['departamento'] == 'LIMA'].copy()
```

Eso incluye distritos fuera del alcance del proyecto.

En cambio, `src/config.py` ya posee el catálogo de los 14 distritos de DIRIS Lima Centro.

### Corrección necesaria

El ETL debe filtrar únicamente los 14 distritos definidos para el proyecto.

El valor:

```text
Todos los distritos (DIRIS Lima Centro)
```

es una opción del dashboard y **no debe tratarse como distrito real en los datos**.

---

## PRIORIDAD 3 — La tarjeta de calidad tiene valores fijos

Actualmente el dashboard muestra:

```text
Completitud: 96 %
Duplicados: 0
Valores faltantes: 4 %
```

Estos números están escritos directamente en el código.

El reporte ETL real muestra otra situación, incluyendo:

```text
25654 duplicados exactos detectados antes de depuración
39.25 % de faltantes en localidad
31.60 % de faltantes en localcod
```

### Corrección necesaria

La tarjeta debe calcular o leer métricas reales del ETL.

Debe diferenciar claramente:

- duplicados detectados antes de limpieza;
- duplicados finales;
- faltantes de variables críticas;
- registros procesados;
- fecha real de procesamiento.

---

## PRIORIDAD 4 — `model.py` todavía no es utilizable con el dataset actual

Actualmente:

```python
X = df[['temperatura_media']]
```

pero el dataset procesado actual genera principalmente:

```text
distrito
ano
semana
casos_notificados
semana_epidemiologica
```

Por tanto, el modelo espera una variable que el pipeline actual no produce.

### Consecuencia

El modelo XGBoost actual **no está integrado funcionalmente** al sistema.

### Corrección necesaria

Crear un modelo V1 basado en variables que realmente existan:

```text
lag_1
lag_2
lag_3
lag_4
media_movil_3
media_movil_4
tendencia / crecimiento
variables estacionales
```

Las variables SENAMHI deben incorporarse únicamente cuando existan datos reales.

**No fabricar `temperatura_media`, humedad ni precipitación.**

---

## PRIORIDAD 5 — Ingeniería de características incompleta

El dashboard genera solamente:

```text
casos_semana_anterior
casos_hace_2_semanas
```

Falta completar:

```text
lag_1
lag_2
lag_3
lag_4
media_movil_3
media_movil_4
crecimiento_semanal
tendencia
mes
trimestre
```

Las medias móviles deben usar datos anteriores y no incluir el valor objetivo de la misma semana.

Ejemplo conceptual:

```python
shift(1).rolling(...)
```

para evitar **data leakage**.

---

## PRIORIDAD 6 — Falta entrenamiento y validación temporal real

Todavía falta:

- definir conjunto de entrenamiento;
- definir conjunto de validación;
- respetar orden cronológico;
- evitar mezcla aleatoria de semanas;
- comparar contra una línea base;
- calcular métricas reales.

Métricas principales:

```text
R²
MAE
RMSE
```

También debe compararse XGBoost contra una referencia simple, por ejemplo:

```text
predicción = casos de la semana anterior
```

---

## PRIORIDAD 7 — Recall y Precisión no corresponden directamente al modelo de regresión

El dashboard actualmente incluye:

```text
Recall
Precisión
```

pero el objetivo principal es predecir **cantidad de casos**, es decir, una regresión.

### Recomendación

Para el modelo de casos mostrar:

```text
R²
MAE
RMSE
MAE de línea base
```

Solo usar Recall/Precisión si posteriormente se construye y evalúa formalmente una tarea de clasificación de riesgo.

---

## PRIORIDAD 8 — El riesgo del dashboard todavía es demostrativo

El mapa contiene valores fijos por distrito y la distribución `7 bajo / 5 medio / 2 alto` también es demostrativa.

### Corrección necesaria

Mientras el modelo no esté validado, mantener claramente:

```text
Riesgo preliminar / demostrativo
```

Después del entrenamiento se puede calcular el riesgo a partir de la predicción y una regla documentada.

No presentar ese riesgo como alerta epidemiológica oficial.

---

# 4. Qué falta para tener una primera versión predictiva funcional

## Fase 1 — Corregir datos y dashboard

- [ ] Filtrar correctamente los 14 distritos de DIRIS Lima Centro.
- [ ] Hacer funcional el filtro de distrito.
- [ ] Implementar “Todos los distritos”.
- [ ] Leer el dataset procesado desde `data/processed`.
- [ ] Mostrar métricas reales de calidad.
- [ ] Eliminar números simulados que puedan confundirse con resultados reales.
- [ ] Mantener señalización de “demostrativo” donde todavía corresponda.

## Fase 2 — Ingeniería de características

Crear un módulo como:

```text
src/features.py
```

Debe generar por distrito:

```text
lag_1
lag_2
lag_3
lag_4
media_movil_3
media_movil_4
crecimiento_semanal
mes
trimestre
```

Todas las features deben construirse sin usar información futura.

## Fase 3 — Modelo XGBoost V1

Reemplazar el `model.py` provisional por un pipeline real.

Debe:

- usar features epidemiológicas existentes;
- entrenar `XGBRegressor`;
- aplicar separación temporal;
- calcular R², MAE y RMSE;
- comparar contra línea base;
- guardar modelo y metadatos;
- registrar entrenamiento mediante auditoría.

Posibles archivos:

```text
src/model.py
src/train_model.py
models/xgboost_dengue.json
reports/metricas_modelo.json
```

## Fase 4 — Predicción de 2, 3 y 4 semanas

Implementar predicción multi-step para los horizontes existentes.

Si se usa un modelo autoregresivo, cada predicción futura puede utilizarse cuidadosamente para construir los lags de la siguiente semana.

El método debe quedar documentado.

## Fase 5 — Integrar modelo con Streamlit

Cuando el modelo esté validado:

- [ ] botón `Actualizar Predicción` ejecuta inferencia real;
- [ ] tarjeta “Predicción de casos” muestra resultado real;
- [ ] gráfico diferencia histórico y pronóstico;
- [ ] métricas se cargan desde archivo de evaluación;
- [ ] riesgo por distrito se calcula, no se escribe manualmente;
- [ ] exportación incluye predicción real;
- [ ] auditoría registra la inferencia.

## Fase 6 — Pruebas

Crear:

```text
tests/
```

Pruebas mínimas:

```text
test_data_pipeline.py
test_features.py
test_model.py
```

Validar esquema, distritos, semanas, duplicados, lags, ausencia de fuga temporal, entrenamiento, predicciones no negativas y métricas.

## Fase 7 — Documentación

Actualmente falta un README principal completo.

Crear:

```text
README.md
```

Debe contener problema, alcance, arquitectura, instalación, ETL, entrenamiento, Streamlit, tests, estructura del repositorio, Kanban, limitaciones y aviso académico.

---

# 5. Orden recomendado de trabajo

No intentar hacer todo al mismo tiempo.

## Bloque A — Correcciones obligatorias

```text
1. Alcance DIRIS
2. Filtro de distrito
3. Métricas reales de calidad
4. Lectura consistente del dataset procesado
```

## Bloque B — Machine Learning

```text
5. features.py
6. XGBoost V1
7. validación temporal
8. R² / MAE / RMSE
9. baseline
```

## Bloque C — Integración

```text
10. Predicción 2–4 semanas
11. conectar modelo al dashboard
12. riesgo calculado
13. exportación real
```

## Bloque D — Calidad final

```text
14. pytest
15. README
16. despliegue
```

---

# 6. Rama recomendada para continuar

Crear desde `develop`:

```text
feature/modelo-integracion-v1
```

Flujo:

```text
develop
  └── feature/modelo-integracion-v1
        └── Pull Request -> develop
              └── validación
                    └── develop -> main
```

No trabajar directamente sobre `main`.

---

# 7. Prompt maestro para Antigravity

Copiar y pegar el siguiente prompt completo en Antigravity.

---

## PROMPT

Estoy trabajando en el repositorio público:

`https://github.com/neiseromar11/DengueML-UPN.git`

Proyecto: **DengueML-UPN — Sistema web para predicción semanal de casos de dengue mediante Machine Learning**.

La metodología de gestión es **Kanban**, no Scrum.

Necesito continuar el desarrollo real del software. No quiero datos simulados presentados como resultados finales y no quiero que se inventen variables epidemiológicas o climáticas.

### REGLA PRINCIPAL

Antes de modificar código:

1. inspecciona TODO el repositorio;
2. revisa `main` y `develop`;
3. revisa especialmente `src/app_avance.py`, `src/data_pipeline.py`, `src/model.py`, `src/config.py`, `src/audit.py`, `reports/calidad_datos.txt`, `data/processed/dengue_processed.csv`, `requirements.txt` y `SECURITY.md`;
4. no modifiques `main` directamente;
5. no inventes resultados;
6. no falsifiques métricas;
7. no elimines funcionalidades existentes del dashboard.

### GIT

Ejecuta primero:

```bash
git fetch origin
git checkout develop
git pull origin develop
git checkout -b feature/modelo-integracion-v1
```

Si la rama ya existe:

```bash
git checkout feature/modelo-integracion-v1
git pull origin feature/modelo-integracion-v1
```

No hagas merge automático a `develop` ni a `main`.

### FASE 1 — CORREGIR EL ALCANCE TERRITORIAL

El proyecto trabaja únicamente con los 14 distritos de DIRIS Lima Centro definidos en `src/config.py`.

Corrige `src/data_pipeline.py`. Actualmente filtra solo `departamento == "LIMA"`, lo que incluye distritos fuera del alcance.

Implementa una normalización robusta de nombres y filtra exclusivamente los 14 distritos válidos.

La opción `Todos los distritos (DIRIS Lima Centro)` es una opción de interfaz y NO es un distrito real.

No pierdas trazabilidad del número de registros descartados por estar fuera del alcance. Agrega esta información al reporte de calidad.

### FASE 2 — CORREGIR EL FILTRO DE DISTRITO DEL DASHBOARD

Actualmente `app_avance.py` muestra un selector de distrito pero la función de datos está fijada a `SAN JUAN DE LURIGANCHO`.

Reestructura la carga para que el distrito seleccionado controle realmente los datos mostrados.

`Todos los distritos (DIRIS Lima Centro)` debe mostrar la agregación del conjunto válido.

Preferir leer `data/processed/dengue_processed.csv` en lugar de volver a procesar innecesariamente el raw en cada ejecución del dashboard.

Si el procesado no existe, mostrar un mensaje controlado indicando que primero debe ejecutarse el ETL.

### FASE 3 — CALIDAD DE DATOS REAL

Eliminar del dashboard los valores escritos manualmente `96 %`, `0 duplicados` y `4 % faltantes`.

La tarjeta debe mostrar información real derivada del pipeline:

```text
Registros raw evaluados
Duplicados detectados antes de limpieza
Registros procesados finales
Faltantes en variables críticas
Fecha de última ejecución ETL
```

Puedes crear `reports/calidad_datos.json` para facilitar la integración.

No mostrar como “0 duplicados” simplemente porque ya fueron eliminados. Diferenciar duplicados detectados y duplicados restantes.

### FASE 4 — INGENIERÍA DE CARACTERÍSTICAS

Crear `src/features.py`.

Implementar feature engineering por distrito y respetando el orden temporal.

Crear al menos:

```text
lag_1
lag_2
lag_3
lag_4
media_movil_3
media_movil_4
crecimiento_semanal
mes
trimestre
```

REGLA DE DATA LEAKAGE: las medias móviles y variables derivadas usadas para predecir una semana NO pueden utilizar los casos de esa misma semana. Usar `shift(1)` antes de `rolling()` cuando corresponda.

No inventar temperatura, humedad o precipitación. Si no existen datos SENAMHI reales, el modelo V1 debe trabajar solamente con features epidemiológicas.

Dejar la arquitectura preparada para integrar clima posteriormente.

### FASE 5 — REEMPLAZAR EL MODELO PROVISIONAL

El `src/model.py` actual utiliza solamente `temperatura_media`, pero esa columna no existe en el dataset procesado.

Reescribir el módulo para construir un **XGBoost V1 epidemiológico** con las features reales producidas en `features.py`.

Usar `xgboost.XGBRegressor` con hiperparámetros razonables y explícitos. No hacer optimización extensa todavía.

### FASE 6 — VALIDACIÓN TEMPORAL

NO utilizar `train_test_split(..., shuffle=True)`.

Ordenar cronológicamente y separar entrenamiento/evaluación usando un corte temporal. Idealmente implementar un holdout temporal final y, opcionalmente, walk-forward/TimeSeriesSplit.

Calcular:

```text
R²
MAE
RMSE
```

Crear también una línea base sencilla: `predicción baseline = casos de la semana anterior`.

Comparar XGBoost contra esa línea base.

Guardar resultados en `reports/metricas_modelo.json` con valores provenientes de una ejecución real.

### FASE 7 — GUARDAR MODELO

Crear `models/` y guardar el modelo en un formato compatible con XGBoost, por ejemplo:

```text
models/xgboost_dengue.json
```

Guardar metadatos suficientes para reproducir el entrenamiento.

### FASE 8 — PREDICCIÓN DE 2, 3 Y 4 SEMANAS

Implementar una predicción multi-step coherente para los horizontes del dashboard.

Si el modelo utiliza lags, realizar predicción autoregresiva: predecir t+1, actualizar lags, predecir t+2 y repetir hasta el horizonte elegido.

Documentar esta decisión. No afirmar que es alerta oficial.

### FASE 9 — INTEGRAR EL MODELO AL DASHBOARD

Cuando exista un modelo válido, el botón `Actualizar Predicción` debe ejecutar inferencia real.

Actualizar:

- tarjeta Predicción de casos;
- gráfico histórico + pronóstico;
- panel de Calidad del modelo con `R²`, `MAE`, `RMSE` y `Baseline MAE`;
- exportación con predicción real;
- auditoría de inferencia.

Eliminar `Recall` y `Precisión` del panel de regresión. Solo usar esas métricas si posteriormente se crea y valida un clasificador independiente.

### FASE 10 — RIESGO PRELIMINAR

Actualmente el mapa y la distribución de riesgo son demostrativos.

No inventar valores.

Crear una función separada y documentada como `clasificar_riesgo(prediccion, referencia)` usando una referencia histórica reproducible.

Mientras la lógica no esté validada, mostrar claramente `Riesgo preliminar` y `Uso académico, no constituye alerta epidemiológica oficial`.

No hardcodear `7 bajo / 5 medio / 2 alto` cuando ya exista cálculo real.

### FASE 11 — AUDITORÍA

Registrar eventos adicionales:

```text
ENTRENAMIENTO_MODELO
EVALUACION_MODELO
PREDICCION_GENERADA
```

No registrar datos personales ni secretos.

### FASE 12 — PRUEBAS

Crear:

```text
tests/test_data_pipeline.py
tests/test_features.py
tests/test_model.py
```

Usar `pytest`.

Pruebas mínimas:

1. columnas obligatorias;
2. filtro de distritos DIRIS;
3. semanas válidas;
4. ausencia de duplicados lógicos finales;
5. generación correcta de lags;
6. rolling sin fuga del objetivo;
7. entrenamiento exitoso;
8. predicciones finitas y no negativas;
9. cálculo correcto de métricas;
10. modelo cargable después de guardarlo.

### FASE 13 — README

Crear un `README.md` completo que explique objetivo, alcance, arquitectura, estructura, instalación, variables de entorno, ETL, entrenamiento, dashboard, tests, flujo Git, limitaciones, seguridad y aviso académico.

Dejar explícito qué partes están implementadas y cuáles siguen pendientes.

### FASE 14 — NO ROMPER EL DISEÑO

Conservar negro / verde / celeste y el responsive actual. No rehacer el dashboard desde cero.

### FASE 15 — EJECUCIÓN Y VALIDACIÓN

Ejecutar:

```bash
python src/data_pipeline.py
```

Luego ejecutar entrenamiento, después:

```bash
streamlit run src/app_avance.py
pytest -q
```

Comprobar que no existan errores.

### FASE 16 — COMMITS

No hacer un único commit gigante. Usar commits descriptivos, por ejemplo:

```text
fix: alinear ETL con distritos DIRIS Lima Centro
fix: conectar filtro distrital con datos procesados
feat: generar variables temporales sin data leakage
feat: implementar entrenamiento XGBoost con validación temporal
feat: integrar predicciones reales al dashboard
test: agregar pruebas del pipeline y modelo
docs: agregar README del proyecto
```

Finalmente:

```bash
git status
git log --oneline -10
git push origin feature/modelo-integracion-v1
```

NO realizar merge.

### ENTREGA FINAL DE ANTIGRAVITY

Al terminar, reportarme:

1. rama utilizada;
2. archivos creados;
3. archivos modificados;
4. problemas encontrados en el código anterior;
5. correcciones realizadas;
6. número de registros procesados;
7. features finales utilizadas;
8. criterio exacto de separación temporal;
9. métricas XGBoost reales;
10. métricas de la línea base;
11. si XGBoost supera o no la línea base;
12. funcionamiento de predicción 2/3/4 semanas;
13. resultado de `pytest`;
14. resultado de Streamlit;
15. hashes de commits;
16. pendientes que aún quedan;
17. confirmación de que NO se modificó `main`;
18. confirmación de que NO se inventaron variables ni métricas.

Si alguna fase no puede completarse por falta de datos reales, DETENER esa fase, documentar claramente la limitación y continuar únicamente con lo que pueda implementarse correctamente.

---

# 8. Criterio para considerar terminada la siguiente etapa

- [ ] distrito seleccionado cambia realmente los datos;
- [ ] ETL restringido a DIRIS Lima Centro;
- [ ] calidad mostrada con datos reales;
- [ ] features temporales creadas sin leakage;
- [ ] XGBoost entrena con datos reales existentes;
- [ ] evaluación temporal completada;
- [ ] R², MAE y RMSE reales guardados;
- [ ] línea base calculada;
- [ ] predicción de 2–4 semanas funcionando;
- [ ] dashboard conectado al modelo;
- [ ] valores demostrativos claramente separados o eliminados;
- [ ] pruebas automáticas principales aprobadas;
- [ ] README actualizado;
- [ ] cambios subidos a `feature/modelo-integracion-v1`;
- [ ] Pull Request preparado hacia `develop`.

---

## Nota final

La prioridad ya no debe ser seguir agregando diseño visual. El siguiente salto importante del proyecto es convertir el prototipo actual en un flujo reproducible:

```text
DATOS REALES
    ↓
ETL
    ↓
FEATURE ENGINEERING
    ↓
VALIDACIÓN TEMPORAL
    ↓
XGBOOST
    ↓
MÉTRICAS
    ↓
PREDICCIÓN 2–4 SEMANAS
    ↓
DASHBOARD
```

Hasta que ese flujo esté conectado, el dashboard debe seguir señalando que la predicción está **En desarrollo**.
