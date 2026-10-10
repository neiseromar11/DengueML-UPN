"""
Pruebas unitarias para el modelado y predicción.
"""
import pandas as pd
import numpy as np
import pytest
from src.model import separar_temporal, entrenar_xgboost, predecir_multistep

def test_separar_temporal():
    """
    Prueba la separación de datos en train/test asegurando el orden temporal
    sin mezclar aleatoriamente (shuffle=False).
    """
    df = pd.DataFrame({
        'fecha': pd.date_range(start='2023-01-01', periods=10, freq='W'),
        'feature_1': range(10),
        'target': range(10)
    })

    X_train, X_test, y_train, y_test = separar_temporal(df, target_col='target', test_size=0.2)

    assert len(X_train) == 8, "El conjunto de entrenamiento debe tener 8 registros"
    assert len(X_test) == 2, "El conjunto de prueba debe tener 2 registros"

    # Validar que no hay data leakage temporal
    assert X_train['feature_1'].iloc[-1] == 7, "El último registro de train debe ser anterior al primero de test"
    assert X_test['feature_1'].iloc[0] == 8, "El primer registro de test debe ser consecutivo al final de train"

def test_entrenar_xgboost():
    """
    Prueba el entrenamiento del modelo XGBoost con datos sintéticos pequeños.
    """
    X_train = pd.DataFrame({'f1': [1, 2, 3, 4], 'f2': [4, 3, 2, 1]})
    y_train = pd.Series([10, 20, 30, 40])

    modelo = entrenar_xgboost(X_train, y_train)
    
    assert modelo is not None, "El modelo entrenado no debe ser nulo"
    assert hasattr(modelo, 'predict'), "El modelo debe implementar el método predict"

def test_predecir_multistep():
    """
    Prueba la predicción iterativa a varios pasos.
    Asegura que el número de predicciones coincida con el horizonte y sean no negativas.
    """
    class DummyModel:
        def predict(self, X):
            # Predicción constante para la prueba
            return np.array([5.0] * len(X))

    modelo = DummyModel()
    horizonte = 4
    X_last = pd.DataFrame({'f1': [4], 'f2': [1]})

    predicciones = predecir_multistep(modelo, X_last, steps=horizonte)

    assert len(predicciones) == horizonte, f"Debe generar {horizonte} predicciones"
    assert all(p >= 0 for p in predicciones), "Las predicciones de casos no deben ser negativas"
