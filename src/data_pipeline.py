import pandas as pd
import numpy as np

def cargar_y_limpiar_datos(filepath):
    try:
        df = pd.read_csv(filepath)
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo en {filepath}")
        return None
    
    df['semana_epidemiologica'] = df['semana_epidemiologica'].astype(str)
    df['casos_notificados'] = df['casos_notificados'].fillna(0)
    
    np.random.seed(42)
    df['temperatura_media'] = np.random.uniform(18.0, 28.0, size=len(df))
    
    df = df.sort_values(by='semana_epidemiologica').reset_index(drop=True)
    return df
