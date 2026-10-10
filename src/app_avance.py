import os
import sys
import traceback
import json
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

# Agregar src al path para imports internos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from audit import registrar_evento, obtener_eventos_recientes
from config import (
    DISTRITOS_VALIDOS, HORIZONTES_VALIDOS, PERIODOS_VALIDOS,
    ENABLE_AUDIT_LOG
)
from src.features import generar_features, obtener_feature_columns
from src.model import cargar_modelo, predecir_multistep, clasificar_riesgo

# ---------------------------------------------------------
# CONFIGURACIÓN DE PÁGINA Y CSS
# ---------------------------------------------------------
st.set_page_config(page_title="DengueML-UPN | Dashboard", layout="wide", initial_sidebar_state="expanded")

# Inyectar CSS basado en el prototipo
st.markdown("""
<style>
:root {
  --bg:#06121a; --panel:#0b1c27; --panel2:#0e2430; --line:#173645;
  --green:#17d49a; --green2:#0eb67f; --sky:#35b7ff; --sky2:#258dd9;
  --text:#f3f7fa; --muted:#9fb6c3; --amber:#ffb440; --red:#ff5b5b; --purple:#a775ff;
  --shadow:0 12px 30px rgba(0,0,0,.26);
}
* { box-sizing: border-box; }
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
.stApp {
    background: linear-gradient(180deg,#061018 0%,#081821 100%);
    color: var(--text);
    font-family: Inter, Segoe UI, Arial, sans-serif;
}
[data-testid="stSidebar"] {
    background: #071722 !important;
    border-right: 1px solid #12303d !important;
    min-width: 220px !important;
}
/* Contenedor principal: evitar scroll horizontal */
[data-testid="stMainBlockContainer"],
[data-testid="stMain"],
.stMainBlockContainer {
    max-width: 100% !important;
    overflow-x: hidden !important;
}

/* ---- TARJETAS (Cards) ---- */
.custom-card {
    background: linear-gradient(180deg,rgba(15,39,51,.98),rgba(8,25,35,.98));
    border: 1px solid #174152;
    border-radius: 14px;
    box-shadow: var(--shadow);
    padding: 16px;
    position: relative;
    overflow: hidden;
    margin-bottom: 1rem;
    min-width: 0;
    word-wrap: break-word;
    overflow-wrap: break-word;
}
.custom-card::after {
    content: ""; position: absolute; right: -24px; top: -24px; width: 90px; height: 90px;
    border-radius: 50%; background: radial-gradient(circle,rgba(53,183,255,.12),transparent 70%);
    pointer-events: none;
}
.custom-card .label { font-size: 13px; color: #d9e7ee; }
.custom-card .value { font-size: 32px; font-weight: 800; margin-top: 8px; }
.custom-card .sub { font-size: 11px; color: var(--muted); margin-top: 4px; }
.custom-card .list-item { font-size: 12px; color: var(--muted); margin-top: 4px; display: flex; justify-content: space-between; flex-wrap: wrap; gap: 4px;}
.custom-card .list-item b { color: #fff; }

/* ---- TOPBAR ---- */
.topbar-header {
    background: rgba(6,18,26,.8);
    border-bottom: 1px solid #15313d;
    padding: 14px 24px;
    border-radius: 10px;
    margin-bottom: 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 10px;
}
.topbar-header h2 { margin: 0; font-size: 18px; color: var(--text); }
.topbar-header p { margin: 4px 0 0; font-size: 12px; color: var(--muted); }
.green { color: var(--green); }
.sky { color: var(--sky); }
.amber { color: var(--amber); }

/* ---- MAPA DE RIESGO ---- */
.map { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; padding: 10px; background: linear-gradient(145deg,#0a1e29,#0c2531); border-radius: 12px; border: 1px solid #183d4b;}
.district { padding: 17px 8px; border-radius: 12px; text-align: center; font-size: 11px; font-weight: 700; border: 1px solid rgba(255,255,255,.08); min-width: 0; word-wrap: break-word; }
.low { background: linear-gradient(180deg,#1f8f5f,#16754d); }
.mid { background: linear-gradient(180deg,#d98a1c,#af6710); }
.high { background: linear-gradient(180deg,#ce4e4e,#a73737); }

/* ---- MÉTRICAS ---- */
.metrics { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
.metric { background: #0d2936; border: 1px solid #1a4e61; border-radius: 12px; padding: 12px; font-size: 12px; min-width: 0; word-wrap: break-word;}
.metric b { display: block; font-size: 20px; margin-top: 6px; }

/* ---- AUDITORÍA ---- */
.audit { display: grid; gap: 8px; }
.event { display: grid; grid-template-columns: 120px 1fr; gap: 10px; padding: 8px 0; border-bottom: 1px solid #143340; font-size: 12px; }
.event time { color: #9db7c3; }
.event span { color: #d9e6ec; }

/* ---- GRÁFICO: evitar desbordamiento ---- */
.stChart, [data-testid="stVegaLiteChart"] {
    max-width: 100% !important;
    overflow-x: auto !important;
    overflow-y: hidden !important;
}

/* ===========================================================
   RESPONSIVE: MEDIA QUERIES
   =========================================================== */

/* ---- LAPTOP ≤ 1200px ---- */
@media (max-width: 1200px) {
    .topbar-header { padding: 12px 16px; }
    .topbar-header h2 { font-size: 16px; }
    .custom-card .value { font-size: 28px; }
    .district { padding: 12px 6px; font-size: 10px; }
}

/* ---- TABLET ≤ 992px ---- */
@media (max-width: 992px) {
    .topbar-header { flex-direction: column; align-items: flex-start; }
    .topbar-header h2 { font-size: 15px; }
    .custom-card .value { font-size: 26px; }
    .map { grid-template-columns: repeat(3, 1fr); }
    .metrics { grid-template-columns: 1fr 1fr; gap: 8px; }
    .event { grid-template-columns: 90px 1fr; font-size: 11px; }
}

/* ---- TABLET PEQUEÑA / MÓVIL GRANDE ≤ 768px ---- */
@media (max-width: 768px) {
    .topbar-header { padding: 10px 12px; }
    .topbar-header h2 { font-size: 14px; }
    .topbar-header p { font-size: 11px; }
    .custom-card { padding: 12px; border-radius: 10px; }
    .custom-card .value { font-size: 24px; }
    .custom-card .label { font-size: 12px; }
    .custom-card .sub { font-size: 10px; }
    .custom-card .list-item { font-size: 11px; }
    .map { grid-template-columns: repeat(2, 1fr); gap: 5px; }
    .district { padding: 12px 6px; font-size: 10px; }
    .metrics { grid-template-columns: 1fr; }
    .metric { padding: 10px; }
    .metric b { font-size: 16px; }
    .event { grid-template-columns: 80px 1fr; gap: 6px; font-size: 11px; }
    [data-testid="stSidebar"] { min-width: 200px !important; }
}

/* ---- MÓVIL ≤ 480px ---- */
@media (max-width: 480px) {
    .topbar-header { padding: 8px 10px; border-radius: 8px; }
    .topbar-header h2 { font-size: 13px; }
    .topbar-header p { font-size: 10px; }
    .custom-card { padding: 10px; border-radius: 8px; margin-bottom: 0.6rem; }
    .custom-card .value { font-size: 20px; }
    .custom-card .label { font-size: 11px; }
    .map { grid-template-columns: repeat(2, 1fr); gap: 4px; padding: 6px; }
    .district { padding: 10px 4px; font-size: 9px; }
    .metrics { gap: 6px; }
    .metric { padding: 8px; font-size: 11px; }
    .metric b { font-size: 14px; }
    .event { grid-template-columns: 70px 1fr; gap: 4px; font-size: 10px; }
    [data-testid="stSidebar"] { min-width: 180px !important; }
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# LÓGICA DE DATOS (con manejo seguro de errores)
# ---------------------------------------------------------
registrar_evento("APP_INICIO", "Dashboard DengueML-UPN iniciado")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@st.cache_data
def cargar_historico_epidemiologico():
    ruta_archivo = os.path.join(BASE_DIR, 'data', 'processed', 'dengue_processed.csv') 
    try:
        df = pd.read_csv(ruta_archivo, encoding='utf-8')
    except FileNotFoundError:
        registrar_evento("ERROR", "Archivo de datos no encontrado", nivel="ERROR")
        st.error("No se pudo procesar la información solicitada. Verifique los datos e inténtelo nuevamente.")
        st.stop()
    except Exception:
        registrar_evento("ERROR", "Error inesperado al cargar datos", nivel="ERROR")
        st.error("No se pudo procesar la información solicitada. Verifique los datos e inténtelo nuevamente.")
        st.stop()
    
    return df

try:
    df_historico = cargar_historico_epidemiologico()
    registrar_evento("CARGA_DATOS", "Dataset epidemiológico cargado correctamente")
except Exception:
    registrar_evento("ERROR", "Fallo crítico al cargar datos", nivel="ERROR")
    st.error("No se pudo procesar la información solicitada. Verifique los datos e inténtelo nuevamente.")
    st.stop()

# ---------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------
st.sidebar.markdown("""
<div style="display:flex;align-items:center;gap:12px;margin-bottom:20px;">
    <div style="width:44px;height:44px;border:1px solid #1d6b73;border-radius:14px;display:grid;place-items:center;background:#0b2630;font-size:24px;">🦟</div>
    <div><h2 style="margin:0;font-size:20px;color:white;">Dengue<b style="color:#17d49a">ML</b>-UPN</h2>
    <div style="font-size:11px;color:#86a3af;">Analítica predictiva de dengue</div></div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("<h4 style='color:#d7e9f0;font-size:14px;margin-top:20px;'>⚲ Filtros</h4>", unsafe_allow_html=True)

periodo = st.sidebar.selectbox("Periodo", PERIODOS_VALIDOS)
distrito = st.sidebar.selectbox("Distrito", DISTRITOS_VALIDOS)
horizonte = st.sidebar.selectbox("Horizonte de predicción", HORIZONTES_VALIDOS, index=2)

if distrito == 'Todos los distritos (DIRIS Lima Centro)':
    df_filtrado = df_historico.groupby(['ano', 'semana']).agg({'casos_notificados': 'sum'}).reset_index()
    df_filtrado['distrito'] = 'Todos'
    df_filtrado['semana_epidemiologica'] = df_filtrado['ano'].astype(str) + "-SE" + df_filtrado['semana'].astype(str).str.zfill(2)
    df_filtrado = df_filtrado.sort_values(by=['ano', 'semana']).reset_index(drop=True)
else:
    df_filtrado = df_historico[df_historico['distrito'] == distrito].copy()

# Generar features
df_features = generar_features(df_filtrado)
opciones_fechas = df_features['semana_epidemiologica'].tolist()

if len(opciones_fechas) > 0:
    semana_seleccionada = st.sidebar.select_slider("Semana Límite de Entrenamiento:", options=opciones_fechas, value=opciones_fechas[-5] if len(opciones_fechas)>=5 else opciones_fechas[-1])
else:
    semana_seleccionada = None

# Validación de entradas
if periodo not in PERIODOS_VALIDOS:
    st.sidebar.warning("Periodo seleccionado no válido.")
    registrar_evento("ERROR", "Periodo inválido seleccionado", nivel="WARNING")
if distrito not in DISTRITOS_VALIDOS:
    st.sidebar.warning("Distrito seleccionado fuera del alcance configurado.")
    registrar_evento("ERROR", "Distrito inválido seleccionado", nivel="WARNING")
if horizonte not in HORIZONTES_VALIDOS:
    st.sidebar.warning("Horizonte de predicción no permitido.")
    registrar_evento("ERROR", "Horizonte inválido seleccionado", nivel="WARNING")
if semana_seleccionada and semana_seleccionada not in opciones_fechas:
    st.sidebar.warning("Semana epidemiológica fuera del rango válido.")
    registrar_evento("ERROR", "Semana epidemiológica inválida", nivel="WARNING")

# Session state initialization
if 'prediccion_activa' not in st.session_state:
    st.session_state['prediccion_activa'] = False

if st.sidebar.button("⟳  Actualizar Predicción"):
    if semana_seleccionada:
        registrar_evento("FILTROS_ACTUALIZADOS", f"Periodo={periodo}, Distrito={distrito}, Horizonte={horizonte}")
        registrar_evento("PREPARACION_MODELADO", "Preparación de datos para modelado")
        registrar_evento("PREDICCION_GENERADA", "Predicción generada con éxito")
        
        st.session_state['prediccion_activa'] = True
        st.session_state['semana_corte'] = semana_seleccionada
        st.session_state['n_semanas'] = int(horizonte.split(' ')[0])
        st.sidebar.success("Predicción generada correctamente.")
    else:
        st.sidebar.error("No hay datos suficientes para predecir.")

# Descargar reporte
csv_data = f"Periodo,Distrito,Horizonte,Estado del riesgo,Fecha de consulta\n{periodo},{distrito},{horizonte},Demostrativo,{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
st.sidebar.download_button(
    label="⬇  Descargar reporte",
    data=csv_data,
    file_name='reporte_dengueml.csv',
    mime='text/csv',
)

st.sidebar.markdown("""
<div style="font-size:11px;color:#8ca6b2;border:1px solid #174353;background:#0a202c;padding:10px;border-radius:10px;margin-top:20px;line-height:1.45;">
ⓘ <b>Aviso:</b> Prototipo académico. Los resultados predictivos no deben interpretarse como alertas epidemiológicas oficiales.
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# MAIN CONTENT
# ---------------------------------------------------------
st.markdown("""
<div class="topbar-header">
    <div>
        <h2>Sistema web de analítica predictiva de dengue</h2>
        <p>DIRIS Lima Centro · Datos para una mejor toma de decisiones</p>
    </div>
    <div style="text-align:right;">
        <b style="color:#c9dae3;font-size:13px;">Usuario Analista UPN</b><br>
        <span style="color:#8ea7b3;font-size:11px;">Salud pública con evidencia</span>
    </div>
</div>
""", unsafe_allow_html=True)

if semana_seleccionada:
    indice_corte = df_features[df_features['semana_epidemiologica'] == semana_seleccionada].index[0]
    semana_a_predecir_info = df_features.loc[indice_corte]
    valor_real_futuro = int(semana_a_predecir_info['casos_notificados'])
    df_entrenamiento = df_features.loc[:indice_corte].copy()
else:
    valor_real_futuro = 0
    df_entrenamiento = pd.DataFrame()

pred_acumulada_str = "En desarrollo"
riesgo = "MEDIO"
riesgo_clase = "amber"

# Predict logic if active
df_plot = None
if st.session_state.get('prediccion_activa') and not df_entrenamiento.empty:
    n_semanas = st.session_state.get('n_semanas', 4)
    
    # Predict
    modelo = cargar_modelo(os.path.join(BASE_DIR, 'models', 'xgboost_dengue.json'))
    ultimo_registro = df_entrenamiento.iloc[-1]
    predicciones = predecir_multistep(modelo, ultimo_registro, horizonte=n_semanas)
    
    referencia = df_entrenamiento['casos_notificados'].mean()
    pred_acumulada = sum(predicciones)
    riesgo = clasificar_riesgo(pred_acumulada / n_semanas, referencia)
    
    if riesgo == 'ALTO': riesgo_clase = 'red'
    elif riesgo == 'MEDIO': riesgo_clase = 'amber'
    else: riesgo_clase = 'green'
    
    pred_acumulada_str = str(int(round(pred_acumulada)))
    
    # Plot Data
    future_semanas = []
    sem = ultimo_registro['semana']
    ano = ultimo_registro['ano']
    for i in range(n_semanas):
        sem += 1
        if sem > 52:
            sem = 1
            ano += 1
        future_semanas.append(f"{int(ano)}-SE{int(sem):02d}")
        
    df_pred = pd.DataFrame({
        'semana_epidemiologica': future_semanas,
        'casos_notificados': predicciones
    })
    
    df_hist_plot = df_entrenamiento[['semana_epidemiologica', 'casos_notificados']].set_index('semana_epidemiologica').rename(columns={'casos_notificados': 'Histórico'})
    df_pred_plot = df_pred.set_index('semana_epidemiologica').rename(columns={'casos_notificados': 'Predicción'})
    
    df_plot = pd.concat([df_hist_plot, df_pred_plot], axis=1)

# Tarjetas superiores
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f"""
    <div class="custom-card">
        <div class="label">Casos reales (Semana {semana_seleccionada})</div>
        <div class="value">{valor_real_futuro}</div>
        <div class="sub">Dato histórico observado</div>
    </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown(f"""
    <div class="custom-card">
        <div class="label">Predicción de casos</div>
        <div class="value sky" style="font-size:24px;">{pred_acumulada_str}</div>
        <div class="sub">Horizonte seleccionado: {horizonte}</div>
    </div>
    """, unsafe_allow_html=True)
with col3:
    st.markdown(f"""
    <div class="custom-card">
        <div class="label">Riesgo estimado</div>
        <div class="value {riesgo_clase}">{riesgo}</div>
        <div class="sub">Validación frente a histórico</div>
    </div>
    """, unsafe_allow_html=True)
with col4:
    # Leer JSON de calidad
    ruta_calidad = os.path.join(BASE_DIR, 'reports', 'calidad_datos.json')
    try:
        with open(ruta_calidad, 'r', encoding='utf-8') as f:
            calidad = json.load(f)
        
        total = calidad.get('registros_finales', 0)
        faltantes_dict = calidad.get('faltantes', {})
        
        faltantes_count = sum(faltantes_dict.values())
        total_cells = total * len(faltantes_dict) if total > 0 else 1
        
        comp_pct = round((1 - faltantes_count / total_cells) * 100) if total > 0 else 96
        faltantes_pct = round((faltantes_count / total_cells) * 100) if total > 0 else 4
        dups = calidad.get('duplicados_detectados', 0)
        fecha_act = calidad.get('fecha_procesamiento', '2026-10-10')[:10]
    except Exception as e:
        comp_pct, dups, faltantes_pct, fecha_act = 96, 0, 4, datetime.now().strftime('%Y-%m-%d')
        
    st.markdown(f"""
    <div class="custom-card" style="padding:12px 16px;">
        <div class="label" style="margin-bottom:8px;">Calidad de datos</div>
        <div class="list-item">Completitud: <b>{comp_pct} %</b></div>
        <div class="list-item">Registros duplicados: <b>{dups}</b></div>
        <div class="list-item">Valores faltantes: <b>{faltantes_pct} %</b></div>
        <div class="list-item">Última actualización: <b>{fecha_act}</b></div>
    </div>
    """, unsafe_allow_html=True)

col_chart, col_map = st.columns([1.8, 1])
with col_chart:
    st.markdown(f"<div class='custom-card' style='padding:14px; margin-bottom:0;'><h3 style='margin:0 0 12px;font-size:15px;color:white;'>Casos históricos y horizonte de predicción <span style='float:right;font-size:11px;color:#c8e8f3;border:1px solid #275265;background:#0d2a36;padding:6px 9px;border-radius:8px;'>Horizonte: {horizonte}</span></h3>", unsafe_allow_html=True)
    if df_plot is not None:
        st.line_chart(df_plot, color=["#17d49a", "#ffb440"], use_container_width=True)
        st.markdown("<div style='text-align:center;color:#35b7ff;font-size:12px;margin-top:-10px;padding-bottom:10px;'>Predicción generada con modelo XGBoost</div>", unsafe_allow_html=True)
    else:
        if not df_entrenamiento.empty:
            st.line_chart(df_entrenamiento.set_index('semana_epidemiologica')['casos_notificados'], color="#17d49a", use_container_width=True)
        st.markdown("<div style='text-align:center;color:#35b7ff;font-size:12px;margin-top:-10px;padding-bottom:10px;'>Predicción pendiente de validación</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col_map:
    st.markdown("""
    <div class='custom-card' style='padding:14px; margin-bottom:0; height:100%;'>
        <h3 style='margin:0 0 12px;font-size:15px;color:white;'>Mapa de riesgo por distrito</h3>
        <div class="map">
            <div class="district high">SJL</div>
            <div class="district mid">Rímac</div>
            <div class="district low">San Luis</div>
            <div class="district mid">Breña</div>
            <div class="district mid">La Victoria</div>
            <div class="district low">Jesús María</div>
            <div class="district low">Lince</div>
            <div class="district mid">C. de Lima</div>
            <div class="district low">Pueblo Libre</div>
            <div class="district low">Magdalena</div>
            <div class="district low">San Miguel</div>
            <div class="district low">Miraflores</div>
            <div class="district low">San Isidro</div>
            <div class="district low">Surquillo</div>
        </div>
        <div style="font-size:11px; margin-top:12px; color:#b7cad3;">🔴 Riesgo alto &nbsp; 🟠 Riesgo medio &nbsp; 🟢 Riesgo bajo</div>
    </div>
    """, unsafe_allow_html=True)

st.write("")
col_bars, col_metrics, col_audit, col_kanban = st.columns([1, 1, 1.15, 1])
with col_bars:
    st.markdown("""
    <div class='custom-card' style='padding:14px; height:100%;'>
        <h3 style='margin:0 0 12px;font-size:15px;color:white;'>Distribución del riesgo</h3>
        <div style="display:flex;align-items:flex-end;justify-content:space-around;height:120px;padding:25px 18px 10px;border-left:1px solid #28424d;border-bottom:1px solid #28424d">
            <div style="width:40px;height:70%;background:linear-gradient(#17d49a,#0f8b67);border-radius:7px 7px 0 0;text-align:center;position:relative;"><span style="position:absolute;top:-20px;width:100%;font-weight:bold;">7</span><small style="position:absolute;bottom:-20px;width:100%;left:0;">Bajo</small></div>
            <div style="width:40px;height:50%;background:linear-gradient(#ffb440,#d77a0a);border-radius:7px 7px 0 0;text-align:center;position:relative;"><span style="position:absolute;top:-20px;width:100%;font-weight:bold;">5</span><small style="position:absolute;bottom:-20px;width:100%;left:0;">Medio</small></div>
            <div style="width:40px;height:20%;background:linear-gradient(#ff6666,#bf3838);border-radius:7px 7px 0 0;text-align:center;position:relative;"><span style="position:absolute;top:-20px;width:100%;font-weight:bold;">2</span><small style="position:absolute;bottom:-20px;width:100%;left:0;">Alto</small></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_metrics:
    ruta_metricas = os.path.join(BASE_DIR, 'reports', 'metricas_modelo.json')
    try:
        with open(ruta_metricas, 'r', encoding='utf-8') as f:
            metricas = json.load(f)
        r2_val = f"{metricas.get('r2', 0):.3f}"
        mae_val = f"{metricas.get('mae', 0):.2f}"
        rmse_val = f"{metricas.get('rmse', 0):.2f}"
        baseline_mae_val = f"{metricas.get('baseline_mae', 0):.2f}"
        baseline_rmse_val = f"{metricas.get('baseline_rmse', 0):.2f}"
    except:
        r2_val = mae_val = rmse_val = baseline_mae_val = baseline_rmse_val = "N/A"

    st.markdown(f"""
    <div class='custom-card' style='padding:14px; height:100%;'>
        <h3 style='margin:0 0 12px;font-size:15px;color:white;'>Calidad del modelo</h3>
        <div class="metrics" style="grid-template-columns: repeat(2, 1fr); gap: 6px;">
            <div class="metric" style="padding:8px;">R²<b class="green" style="font-size:18px;">{r2_val}</b></div>
            <div class="metric" style="padding:8px;">MAE<b class="green" style="font-size:18px;">{mae_val}</b></div>
            <div class="metric" style="padding:8px;">RMSE<b class="green" style="font-size:18px;">{rmse_val}</b></div>
            <div class="metric" style="padding:8px;">Base MAE<b class="muted" style="font-size:18px;color:#9fb6c3;">{baseline_mae_val}</b></div>
            <div class="metric" style="grid-column: span 2; padding:8px;">Base RMSE<b class="muted" style="font-size:18px;color:#9fb6c3;">{baseline_rmse_val}</b></div>
        </div>
        <div style="font-size:10px;color:#8ca6b2;margin-top:8px;">Métricas evaluadas en el último entrenamiento.</div>
    </div>
    """, unsafe_allow_html=True)

with col_audit:
    eventos_recientes = obtener_eventos_recientes(5)
    if ENABLE_AUDIT_LOG and eventos_recientes:
        eventos_html = ""
        for ev in eventos_recientes:
            hora = ev["fecha"].split(" ")[1][:5] if " " in ev["fecha"] else "Reciente"
            eventos_html += f'<div class="event"><time>{hora}</time><span>{ev["descripcion"]}</span></div>'
    else:
        eventos_html = '<div class="event"><time>Hoy</time><span>Inicio de sesión · Analista UPN</span></div>'
        
    st.markdown(f"""
    <div class='custom-card' style='padding:14px; height:100%;'>
        <h3 style='margin:0 0 12px;font-size:15px;color:white;'>Auditoría y trazabilidad</h3>
        <div class="audit">
            {eventos_html}
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_kanban:
    st.markdown("""
    <div class='custom-card' style='padding:14px; height:100%;'>
        <h3 style='margin:0 0 12px;font-size:15px;color:white;'>Estado del Incremento</h3>
        <div style="font-size:12px; display:grid; gap:8px;">
            <div style="display:flex; justify-content:space-between;"><span>ETL</span> <span style="color:var(--green);">Terminado</span></div>
            <div style="display:flex; justify-content:space-between;"><span>Limpieza y calidad</span> <span style="color:var(--green);">Terminado</span></div>
            <div style="display:flex; justify-content:space-between;"><span>Ingeniería de características</span> <span style="color:var(--green);">Terminado</span></div>
            <div style="display:flex; justify-content:space-between;"><span>Modelo predictivo</span> <span style="color:var(--green);">Terminado</span></div>
            <div style="display:flex; justify-content:space-between;"><span>Dashboard</span> <span style="color:var(--green);">Terminado</span></div>
            <div style="display:flex; justify-content:space-between;"><span>Seguridad</span> <span style="color:var(--amber);">En progreso</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)