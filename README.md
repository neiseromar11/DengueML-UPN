# DengueML-UPN: Predicción de Casos de Dengue

## Objetivo y Alcance
Este proyecto tiene como objetivo desarrollar un modelo de Machine Learning para la predicción de casos de dengue, enfocado específicamente en la jurisdicción de **DIRIS Lima Centro**. La herramienta busca apoyar la toma de decisiones epidemiológicas y la gestión de recursos de salud pública mediante la estimación anticipada de brotes y tendencias.

## Arquitectura
El sistema está diseñado en un flujo de datos modular:

1. **Data Pipeline (`src/data_pipeline.py`)**: Extracción, transformación y carga (ETL). Se encarga de la limpieza de datos, normalización de nombres de distritos y filtrado de la información para la zona de interés (DIRIS Lima Centro).
2. **Feature Engineering (`src/feature_engineering.py`)**: Creación de características para mejorar la capacidad predictiva del modelo. Incluye variables de rezago temporal (`lag_1`), promedios móviles (asegurando el uso de `shift(1)` antes de `rolling` para evitar fuga de información o *data leakage*) y métricas de crecimiento semanal.
3. **Modelado (`src/model.py` y `src/train_model.py`)**: Entrenamiento y evaluación utilizando el algoritmo XGBoost. Se implementa una división temporal (`time-series split`) que preserva la cronología de los eventos sin mezclar los datos de manera aleatoria (`shuffle=False`).
4. **Dashboard y Visualización (`src/app_avance.py`)**: Aplicación web interactiva desarrollada con **Streamlit**. Permite monitorear la evolución histórica de la enfermedad, identificar alertas y visualizar las predicciones multicapa.

## Instalación

1. Clona el repositorio y navega a la carpeta principal del proyecto:
   ```bash
   cd capstone_dengue
   ```

2. Se recomienda crear y activar un entorno virtual. Luego, instala las dependencias necesarias:
   ```bash
   pip install -r requirements.txt
   ```

## Uso

El sistema puede ejecutarse en tres pasos secuenciales:

1. **Ejecutar ETL (Data Pipeline)**: 
   Genera el conjunto de datos procesado a partir de las fuentes en crudo.
   ```bash
   python src/data_pipeline.py
   ```

2. **Entrenar el Modelo**: 
   Ejecuta la ingeniería de características, entrena el modelo XGBoost y guarda el modelo entrenado.
   ```bash
   python src/train_model.py
   ```

3. **Ejecutar el Dashboard**: 
   Despliega la interfaz de usuario en el navegador local.
   ```bash
   streamlit run src/app_avance.py
   ```

## Seguridad, Consideraciones y Limitaciones
- **Prototipo Académico**: Este sistema es un prototipo desarrollado con fines académicos. Sus predicciones no deben considerarse como diagnósticos médicos ni utilizarse como única fuente de verdad para la formulación de políticas públicas de salud sin previa validación oficial.
- **Calidad de Datos**: Las predicciones dependen en gran medida de la exactitud de los datos notificados; retrasos en los reportes o subregistro pueden impactar la eficacia del modelo.
- **Seguridad**: No se manejan datos personalmente identificables (PII). Todos los análisis se basan en conteos epidemiológicos agregados.
