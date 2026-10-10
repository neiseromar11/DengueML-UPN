import os, sys, json
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from features import obtener_feature_columns, TARGET

def separar_temporal(df, ratio_test=0.2):
    """
    Separa el dataset en train y test de forma temporal, sin mezclar datos.
    """
    df = df.sort_values(['ano', 'semana']).copy()
    n_test = int(len(df) * ratio_test)
    n_train = len(df) - n_test
    
    df_train = df.iloc[:n_train].copy()
    df_test = df.iloc[n_train:].copy()
    
    cutoff_semana = df_test['semana_epidemiologica'].iloc[0] if not df_test.empty else None
    cutoff_info = {'semana_epidemiologica': cutoff_semana}
    
    return df_train, df_test, cutoff_info

def entrenar_xgboost(df_train, feature_cols=None):
    """
    Entrena un modelo XGBoost con los datos de entrenamiento.
    """
    if feature_cols is None:
        feature_cols = obtener_feature_columns()
        
    X_train = df_train[feature_cols]
    y_train = df_train[TARGET]
    
    modelo = xgb.XGBRegressor(
        n_estimators=200, 
        max_depth=5, 
        learning_rate=0.05, 
        subsample=0.8, 
        colsample_bytree=0.8, 
        objective='reg:squarederror', 
        random_state=42
    )
    
    modelo.fit(X_train, y_train)
    return modelo

def evaluar_modelo(modelo, df_test, feature_cols=None):
    """
    Evalúa el modelo usando R2, MAE y RMSE.
    Corta las predicciones para que no sean negativas.
    """
    if feature_cols is None:
        feature_cols = obtener_feature_columns()
        
    X_test = df_test[feature_cols]
    y_test = df_test[TARGET]
    
    y_pred = modelo.predict(X_test)
    y_pred = np.clip(y_pred, 0, None)
    
    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    
    return {
        'metricas': {'r2': r2, 'mae': mae, 'rmse': rmse},
        'y_pred': y_pred
    }

def calcular_baseline(df_test):
    """
    Calcula el MAE y RMSE usando el valor de la semana anterior como predicción.
    """
    y_test = df_test[TARGET]
    y_pred_baseline = df_test['lag_1']
    
    mae = mean_absolute_error(y_test, y_pred_baseline)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred_baseline))
    
    return {'mae': mae, 'rmse': rmse}

def guardar_modelo(modelo, ruta):
    """
    Guarda el modelo entrenado en la ruta especificada.
    """
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    modelo.save_model(ruta)

def cargar_modelo(ruta):
    """
    Carga un modelo guardado desde la ruta especificada.
    """
    modelo = xgb.XGBRegressor()
    modelo.load_model(ruta)
    return modelo

def predecir_multistep(modelo, ultimo_registro, horizonte=4, feature_cols=None):
    """
    Predicción autorregresiva a varios pasos.
    """
    if feature_cols is None:
        feature_cols = obtener_feature_columns()
        
    predicciones = []
    current_state = ultimo_registro.copy() if isinstance(ultimo_registro, pd.Series) else pd.Series(ultimo_registro)
    
    for _ in range(horizonte):
        X = pd.DataFrame([current_state[feature_cols]])
        pred = modelo.predict(X)[0]
        pred = max(0, pred)
        predicciones.append(pred)
        
        # Actualizar lags y otras features para el siguiente paso
        current_state['lag_4'] = current_state['lag_3']
        current_state['lag_3'] = current_state['lag_2']
        current_state['lag_2'] = current_state['lag_1']
        current_state['lag_1'] = pred
        
        # Actualizar medias móviles aproximadamente
        current_state['media_movil_3'] = (pred + current_state['lag_1'] + current_state['lag_2']) / 3
        current_state['media_movil_4'] = (pred + current_state['lag_1'] + current_state['lag_2'] + current_state['lag_3']) / 4
        
        # Actualizar semana
        semana_actual = current_state.get('semana', 1)
        nueva_semana = (semana_actual % 52) + 1
        current_state['semana'] = nueva_semana
        current_state['mes'] = (nueva_semana - 1) // 4 + 1
        current_state['trimestre'] = (current_state['mes'] - 1) // 3 + 1
        
    return predicciones

def clasificar_riesgo(prediccion, referencia_historica):
    """
    Clasifica el riesgo basado en la predicción comparada con un valor histórico de referencia.
    Nota: Esta es una clasificación académica preliminar.
    """
    if prediccion > referencia_historica * 1.5:
        return 'ALTO'
    elif prediccion > referencia_historica * 0.8:
        return 'MEDIO'
    else:
        return 'BAJO'
