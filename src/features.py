import pandas as pd
import numpy as np

TARGET = 'casos_notificados'

def obtener_feature_columns() -> list:
    """
    Retorna la lista de características (features) utilizadas para el entrenamiento del modelo.
    """
    return [
        'lag_1', 
        'lag_2', 
        'lag_3', 
        'lag_4', 
        'media_movil_3', 
        'media_movil_4', 
        'crecimiento_semanal', 
        'mes', 
        'trimestre'
    ]

def generar_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica ingeniería de características para la predicción de dengue.
    
    Agrupa por distrito y genera variables temporales (rezagos, medias móviles).
    Asegura que no exista fuga de datos (data leakage) aplicando shift(1) antes de
    las ventanas móviles.
    
    Args:
        df: DataFrame con columnas ['distrito', 'ano', 'semana', 'casos_notificados', ...]
        
    Returns:
        DataFrame enriquecido con las nuevas características, sin valores nulos generados por el lag.
    """
    df = df.copy()
    
    # 1. Ordenar por distrito y tiempo
    df = df.sort_values(by=['distrito', 'ano', 'semana'])
    
    # 2. Generar características por distrito
    def calcular_features_distrito(grupo):
        # Rezagos (lags)
        grupo['lag_1'] = grupo['casos_notificados'].shift(1)
        grupo['lag_2'] = grupo['casos_notificados'].shift(2)
        grupo['lag_3'] = grupo['casos_notificados'].shift(3)
        grupo['lag_4'] = grupo['casos_notificados'].shift(4)
        
        # Medias móviles aplicadas al shift(1) para evitar fuga de datos
        casos_shift = grupo['casos_notificados'].shift(1)
        grupo['media_movil_3'] = casos_shift.rolling(window=3).mean()
        grupo['media_movil_4'] = casos_shift.rolling(window=4).mean()
        
        # Crecimiento semanal: (lag_1 - lag_2) / lag_2
        # División segura: evitar división por cero y manejar NaN o inf
        denominador = grupo['lag_2']
        crecimiento = np.where(
            denominador == 0, 
            0, 
            (grupo['lag_1'] - denominador) / denominador
        )
        grupo['crecimiento_semanal'] = crecimiento
        
        return grupo

    # Aplicar transformación por grupo
    df = df.groupby('distrito', group_keys=False).apply(calcular_features_distrito)
    
    # Limpieza de valores nulos o infinitos en el crecimiento semanal
    df['crecimiento_semanal'] = df['crecimiento_semanal'].replace([np.inf, -np.inf], 0).fillna(0)
    
    # Derivar variables de tiempo (mes aproximado y trimestre)
    df['mes'] = np.ceil(df['semana'] * 7 / 30.0).clip(1, 12).astype(int)
    df['trimestre'] = np.ceil(df['mes'] / 3.0).astype(int)
    
    # NOTA ARQUITECTURA: 
    # Espacio reservado para futura integración con variables climáticas.
    # NO INVENTAR DATOS. Cuando los datos reales de clima estén disponibles,
    # realizar merge por ['distrito', 'ano', 'semana'] aquí.
    
    # 3. Eliminar filas con NaN generadas por los shifts (primeras semanas de cada distrito)
    # Evaluamos solo las columnas de lag/media móvil para evitar borrar por otras razones
    columnas_rezagos = ['lag_1', 'lag_2', 'lag_3', 'lag_4', 'media_movil_3', 'media_movil_4']
    df = df.dropna(subset=columnas_rezagos)
    
    return df
