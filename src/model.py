import numpy as np
import xgboost as xgb

def entrenar_modelo_base(df):
    X = df[['temperatura_media']]
    y = df['casos_notificados']
    modelo = xgb.XGBRegressor(objective='reg:squarederror', n_estimators=10)
    modelo.fit(X, y)
    return modelo

def generar_prediccion(modelo, temperatura_actual):
    X_nuevo = np.array([[temperatura_actual]])
    prediccion = modelo.predict(X_nuevo)
    return max(0, int(prediccion[0]))
