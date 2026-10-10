import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
import json
import unicodedata

# Añadir el path de src para poder importar modules internos si se ejecuta como script
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audit import registrar_evento
from config import DISTRITOS_DIRIS_DATASET, DISTRITOS_DATASET_MAP

def normalize_district_name(name):
    """Normalize district name for fuzzy matching (remove accents, uppercase, replace weird chars)"""
    if pd.isna(name):
        return ""
    name_str = str(name).strip().upper()
    # Handle \ufffd and other weird characters commonly found for 'Ñ'
    name_str = name_str.replace('\ufffd', 'N').replace('Ñ', 'N')
    # Remove accents
    name_str = ''.join(c for c in unicodedata.normalize('NFD', name_str) if unicodedata.category(c) != 'Mn')
    return name_str

def match_district(raw_name, valid_districts):
    norm_raw = normalize_district_name(raw_name)
    for vd in valid_districts:
        if normalize_district_name(vd) == norm_raw:
            return vd
    return None

def ejecutar_etl_calidad():
    """
    Ejecuta el pipeline ETL para el proyecto DengueML-UPN.
    Carga datos, estandariza, limpia duplicados, evalúa calidad y guarda procesado.
    """
    registrar_evento("APP_INICIO", "Iniciando pipeline ETL y control de calidad")
    
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ruta_raw = os.path.join(BASE_DIR, 'data', 'raw', 'datos_abiertos_vigilancia_dengue.csv')
    ruta_processed = os.path.join(BASE_DIR, 'data', 'processed', 'dengue_processed.csv')
    ruta_reporte_txt = os.path.join(BASE_DIR, 'reports', 'calidad_datos.txt')
    ruta_reporte_json = os.path.join(BASE_DIR, 'reports', 'calidad_datos.json')
    
    # Crear directorios si no existen
    os.makedirs(os.path.dirname(ruta_processed), exist_ok=True)
    os.makedirs(os.path.dirname(ruta_reporte_txt), exist_ok=True)
    
    # 1. Cargar datos
    if not os.path.exists(ruta_raw):
        ruta_raw = os.path.join(BASE_DIR, 'datos_abiertos_vigilancia_dengue.csv')
        if not os.path.exists(ruta_raw):
            msg = f"No se encontró el archivo de datos raw en {ruta_raw}."
            print("Error:", msg)
            registrar_evento("ERROR", msg, nivel="ERROR")
            return None

    try:
        try:
            df = pd.read_csv(ruta_raw, sep=';', encoding='utf-8-sig', low_memory=False, on_bad_lines='skip')
        except UnicodeDecodeError:
            df = pd.read_csv(ruta_raw, sep=';', encoding='latin-1', low_memory=False, on_bad_lines='skip')
        
        total_raw = len(df)
        registrar_evento("CARGA_DATOS", f"Dataset cargado correctamente. Registros iniciales: {total_raw}")
    except Exception as e:
        registrar_evento("ERROR", "Error inesperado al cargar el dataset", nivel="ERROR")
        print("Error inesperado al cargar el dataset. Consulte los logs.")
        return None

    # 2. Estandarizar columnas
    df.columns = df.columns.str.strip().str.lower()
    df.rename(columns=lambda x: x.replace('ï»¿', '').replace('\ufeff', ''), inplace=True)
    
    columnas_requeridas = ['departamento', 'distrito', 'ano', 'semana']
    faltantes_cols = [col for col in columnas_requeridas if col not in df.columns]
    if faltantes_cols:
        msg = f"Faltan columnas requeridas para el análisis: {faltantes_cols}"
        print("Error:", msg)
        registrar_evento("ERROR", msg, nivel="ERROR")
        return None

    # 3. Filtrar departamento LIMA
    df_lima = df[df['departamento'] == 'LIMA'].copy()
    total_lima = len(df_lima)

    # 4. Handle encoding and filter DIRIS Lima Centro districts
    df_lima['distrito_matched'] = df_lima['distrito'].apply(lambda x: match_district(x, DISTRITOS_DIRIS_DATASET))
    
    df_diris = df_lima[df_lima['distrito_matched'].notna()].copy()
    total_diris = len(df_diris)
    
    # 5. Report how many records were discarded
    descartados_fuera_alcance = total_raw - total_diris
    
    df_diris['distrito'] = df_diris['distrito_matched']
    df_diris.drop(columns=['distrito_matched'], inplace=True)

    # 6. Eliminar duplicados exactos
    duplicados_detectados = int(df_diris.duplicated().sum())
    if duplicados_detectados > 0:
        df_diris = df_diris.drop_duplicates()

    faltantes_dict = df_diris.isnull().sum().to_dict()
    faltantes_dict_int = {k: int(v) for k, v in faltantes_dict.items()}

    # 7. Group by distrito, ano, semana
    df_agrupado = df_diris.groupby(['distrito', 'ano', 'semana']).size().reset_index(name='casos_notificados')
    
    # 8. Map district names to display names
    df_agrupado['distrito'] = df_agrupado['distrito'].map(DISTRITOS_DATASET_MAP)
    
    # 9. Generate semana_epidemiologica
    df_agrupado['semana_epidemiologica'] = (
        df_agrupado['ano'].astype(str) + "-SE" + 
        df_agrupado['semana'].astype(str).str.zfill(2)
    )
    
    df_agrupado = df_agrupado.sort_values(by=['distrito', 'ano', 'semana']).reset_index(drop=True)
    
    # 10. Remove logical duplicates
    clave_logica = ['distrito', 'ano', 'semana_epidemiologica']
    duplicados_logicos = int(df_agrupado.duplicated(subset=clave_logica).sum())
    if duplicados_logicos > 0:
        df_agrupado = df_agrupado.drop_duplicates(subset=clave_logica, keep='last')
        registrar_evento("PROCESAMIENTO_ETL", f"Se eliminaron {duplicados_logicos} duplicados lógicos")
    
    registros_finales = len(df_agrupado)

    # 11. Save processed data
    df_agrupado.to_csv(ruta_processed, index=False, encoding='utf-8')
    registrar_evento("PREPARACION_MODELADO", f"Dataset procesado guardado. Registros finales: {registros_finales}")

    # 12 & 13. Generate reports
    with open(ruta_reporte_txt, "w", encoding="utf-8") as f:
        f.write("="*50 + "\n")
        f.write("REPORTE DE CALIDAD DE DATOS - DengueML-UPN\n")
        f.write("="*50 + "\n")
        f.write(f"Fecha de evaluación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"Total de registros originales: {total_raw}\n")
        f.write(f"Total de registros en Lima: {total_lima}\n")
        f.write(f"Total de registros en DIRIS Centro: {total_diris}\n")
        f.write(f"Descartados fuera del alcance: {descartados_fuera_alcance}\n")
        f.write(f"Registros duplicados exactos eliminados: {duplicados_detectados}\n")
        f.write(f"Registros duplicados lógicos eliminados: {duplicados_logicos}\n")
        f.write(f"Registros finales: {registros_finales}\n\n")
        f.write("Valores faltantes por columna (en subset DIRIS):\n")
        for col, val in faltantes_dict_int.items():
            if total_diris > 0:
                f.write(f"  - {col}: {val} ({(val/total_diris)*100:.2f}%)\n")
            else:
                f.write(f"  - {col}: {val} (0%)\n")
    
    reporte_json = {
        "total_raw": total_raw,
        "total_lima": total_lima,
        "total_diris": total_diris,
        "descartados_fuera_alcance": descartados_fuera_alcance,
        "duplicados_detectados": duplicados_detectados,
        "duplicados_logicos": duplicados_logicos,
        "registros_finales": registros_finales,
        "faltantes": faltantes_dict_int,
        "fecha_procesamiento": datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    }
    
    with open(ruta_reporte_json, "w", encoding="utf-8") as f:
        json.dump(reporte_json, f, indent=4, ensure_ascii=False)
        
    registrar_evento("PROCESAMIENTO_ETL", "Reportes de calidad de datos generados (txt y json)")

    print(f"ETL completado con éxito. Datos procesados guardados en {ruta_processed}")
    print(f"Reporte de calidad disponible en {ruta_reporte_txt} y {ruta_reporte_json}")
    return df_agrupado

if __name__ == "__main__":
    ejecutar_etl_calidad()
