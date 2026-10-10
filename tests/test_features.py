"""
Pruebas unitarias para la ingeniería de características (Feature Engineering).
"""
import pandas as pd
import numpy as np
import pytest
from src.features import generar_features

def test_generar_features():
    """
    Prueba la correcta generación de características temporales:
    lag_1, media_movil_3 (sin filtración de datos) y crecimiento_semanal.
    """
    df = pd.DataFrame({
        'fecha': pd.date_range(start='2023-01-01', periods=5, freq='W'),
        'casos': [10.0, 20.0, 15.0, 30.0, 25.0]
    })

    df_feat = generar_features(df, 'casos')

    # 1. Verificar lag_1
    assert pd.isna(df_feat['lag_1'].iloc[0]), "El primer valor de lag_1 debería ser NaN"
    assert df_feat['lag_1'].iloc[1] == 10.0, "El lag_1 en t=1 debería ser el caso de t=0"

    # 2. Verificar media_movil_3 sin data leakage (shift(1).rolling(3).mean())
    assert 'media_movil_3' in df_feat.columns
    # Para t=2 (índice 2), los lags disponibles son t=0 y t=1, no alcanza a 3 periodos previos completos
    assert pd.isna(df_feat['media_movil_3'].iloc[2]), "Debe requerir 3 periodos previos, t=2 debería ser NaN"
    # Para t=3 (índice 3), los lags disponibles son t=0 (10), t=1 (20), t=2 (15) -> prom: 15.0
    assert df_feat['media_movil_3'].iloc[3] == 15.0, "La media móvil 3 en t=3 debe promediar t=0, t=1, t=2 sin incluir t=3"

    # 3. Verificar crecimiento_semanal (casos_t - casos_t-1)
    # i=1: 20 - 10 = 10
    assert df_feat['crecimiento_semanal'].iloc[1] == 10.0, "El crecimiento semanal en t=1 debe ser 10"
