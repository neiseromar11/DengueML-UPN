import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime

# Añadir el path de src para poder importar modules internos si se ejecuta como script
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audit import registrar_evento

def ejecutar_etl_calidad():
    """
    Ejecuta el pipeline ETL para el proyecto DengueML-UPN.
    Carga datos, estandariza, limpia duplicados, evalúa calidad y guarda procesado.
    """
    registrar_evento("APP_INICIO", "Iniciando pipeline ETL y control de calidad")
    
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ruta_raw = os.path.join(BASE_DIR, 'data', 'raw', 'datos_abiertos_vigilancia_dengue.csv')
    ruta_processed = os.path.join(BASE_DIR, 'data', 'processed', 'dengue_processed.csv')
    ruta_reporte = os.path.join(BASE_DIR, 'reports', 'calidad_datos.txt')
    
    # 1. Cargar datos
    if not os.path.exists(ruta_raw):
        # Si no está en raw, intentar en la raíz
        ruta_raw = os.path.join(BASE_DIR, 'datos_abiertos_vigilancia_dengue.csv')
        if not os.path.exists(ruta_raw):
            msg = f"No se encontró el archivo de datos raw."
            print("Error:", msg)
            registrar_evento("ERROR", msg, nivel="ERROR")
            return None

    try:
        try:
            df = pd.read_csv(ruta_raw, sep=';', encoding='utf-8-sig', low_memory=False, on_bad_lines='skip')
        except UnicodeDecodeError:
            df = pd.read_csv(ruta_raw, sep=';', encoding='latin-1', low_memory=False, on_bad_lines='skip')
        registrar_evento("CARGA_DATOS", f"Dataset cargado correctamente. Registros iniciales: {len(df)}")
    except Exception as e:
        registrar_evento("ERROR", "Error inesperado al cargar el dataset", nivel="ERROR")
        print("Error inesperado al cargar el dataset. Consulte los logs.")
        return None

    # 2. Estandarizar columnas
    df.columns = df.columns.str.strip().str.lower()
    df.rename(columns=lambda x: x.replace('ï»¿', '').replace('\ufeff', ''), inplace=True)
    
    # Verificar columnas mínimas esperadas (limitación documentada)
    columnas_requeridas = ['departamento', 'distrito', 'ano', 'semana']
    faltantes = [col for col in columnas_requeridas if col not in df.columns]
    if faltantes:
        msg = f"Faltan columnas requeridas para el análisis: {faltantes}"
        print("Error:", msg)
        registrar_evento("ERROR", msg, nivel="ERROR")
        return None

    # 3. Validación básica (filtrando DIRIS Lima Centro según alcance)
    df_lima = df[df['departamento'] == 'LIMA'].copy()
    
    # 4. Eliminar duplicados lógicos (agrupando para sumar casos notificados, si es un registro por caso)
    # Como los datos abiertos suelen venir con un registro por persona, primero evaluamos calidad sobre el raw filtrado
    
    # 5. Generar reporte de calidad de datos antes de agrupar
    total_registros = len(df_lima)
    valores_faltantes = df_lima.isnull().sum()
    duplicados_exactos = df_lima.duplicated().sum()
    
    with open(ruta_reporte, "w", encoding="utf-8") as f:
        f.write("="*50 + "\n")
        f.write("REPORTE DE CALIDAD DE DATOS - DengueML-UPN\n")
        f.write("="*50 + "\n")
        f.write(f"Fecha de evaluación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"Total de registros evaluados (Lima): {total_registros}\n")
        f.write(f"Registros duplicados exactos: {duplicados_exactos}\n\n")
        f.write("Valores faltantes por columna:\n")
        for col, val in valores_faltantes.items():
            f.write(f"  - {col}: {val} ({(val/total_registros)*100:.2f}%)\n")
        
        f.write("\nLimitaciones identificadas:\n")
        f.write("  - Prototipo académico: No se han inventado casos epidemiológicos ficticios.\n")
        f.write("  - Si el modelo requiere variables meteorológicas reales, se deben integrar desde otra fuente.\n")
    
    registrar_evento("PROCESAMIENTO_ETL", "Reporte de calidad de datos generado")

    # Eliminar duplicados exactos si los hay
    if duplicados_exactos > 0:
        df_lima = df_lima.drop_duplicates()

    # Agrupar por distrito, año y semana (clave lógica) para generar casos agregados
    df_agrupado = df_lima.groupby(['distrito', 'ano', 'semana']).size().reset_index(name='casos_notificados')
    
    # Estandarizar año y semana a semana_epidemiologica
    df_agrupado['semana_epidemiologica'] = (
        df_agrupado['ano'].astype(str) + "-SE" + 
        df_agrupado['semana'].astype(str).str.zfill(2)
    )
    
    df_agrupado = df_agrupado.sort_values(by=['distrito', 'ano', 'semana']).reset_index(drop=True)
    
    # Eliminar duplicados lógicos (por clave)
    clave_logica = ['distrito', 'ano', 'semana_epidemiologica']
    duplicados_logicos = df_agrupado.duplicated(subset=clave_logica).sum()
    if duplicados_logicos > 0:
        df_agrupado = df_agrupado.drop_duplicates(subset=clave_logica, keep='last')
        registrar_evento("PROCESAMIENTO_ETL", f"Se eliminaron {duplicados_logicos} duplicados lógicos")
    
    # 6. Guardar procesados
    df_agrupado.to_csv(ruta_processed, index=False, encoding='utf-8')
    registrar_evento("PREPARACION_MODELADO", f"Dataset procesado guardado. Registros finales: {len(df_agrupado)}")
    
    print(f"ETL completado con éxito. Datos procesados guardados en {ruta_processed}")
    print(f"Reporte de calidad disponible en {ruta_reporte}")
    return df_agrupado

if __name__ == "__main__":
    ejecutar_etl_calidad()
