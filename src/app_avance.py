import os
import sys
import traceback
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
*{ box-sizing: border-box; }
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

@st.cache_data
def cargar_historico_epidemiologico():
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ruta_archivo = os.path.join(BASE_DIR, 'datos_abiertos_vigilancia_dengue.csv') 
    try:
        try:
            df = pd.read_csv(ruta_archivo, sep=';', encoding='utf-8-sig', low_memory=False, on_bad_lines='skip')
        except UnicodeDecodeError:
            df = pd.read_csv(ruta_archivo, sep=';', encoding='latin-1', low_memory=False, on_bad_lines='skip')
    except FileNotFoundError:
        registrar_evento("ERROR", "Archivo de datos no encontrado", nivel="ERROR")
        st.error("No se pudo procesar la información solicitada. Verifique los datos e inténtelo nuevamente.")
        st.stop()
    except Exception:
        registrar_evento("ERROR", "Error inesperado al cargar datos", nivel="ERROR")
        st.error("No se pudo procesar la información solicitada. Verifique los datos e inténtelo nuevamente.")
        st.stop()
    
    df.columns = df.columns.str.strip().str.lower()
    df.rename(columns=lambda x: x.replace('ï»¿', '').replace('\ufeff', ''), inplace=True)
    
    if 'departamento' not in df.columns:
        registrar_evento("ERROR", "Columna departamento no encontrada en dataset", nivel="ERROR")
        st.error("No se pudo procesar la información solicitada. Verifique los datos e inténtelo nuevamente.")
        st.stop()
        
    df_sjl = df[(df['departamento'] == 'LIMA') & (df['distrito'] == 'SAN JUAN DE LURIGANCHO')].copy()
    df_agrupado = df_sjl.groupby(['ano', 'semana']).size().reset_index(name='casos_notificados')
    df_agrupado['semana_epidemiologica'] = (
        df_agrupado['ano'].astype(str) + "-SE" + 
        df_agrupado['semana'].astype(str).str.zfill(2)
    )
    df_agrupado = df_agrupado.sort_values(by=['ano', 'semana']).reset_index(drop=True)
    df_agrupado['casos_semana_anterior'] = df_agrupado['casos_notificados'].shift(1)
    df_agrupado['casos_hace_2_semanas'] = df_agrupado['casos_notificados'].shift(2)
    
    return df_agrupado.dropna().reset_index(drop=True)

try:
    df_historico = cargar_historico_epidemiologico()
    registrar_evento("CARGA_DATOS", "Dataset epidemiológico cargado correctamente")
    registrar_evento("PROCESAMIENTO_ETL", "Agrupación y generación de lags completada")
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

opciones_fechas = df_historico['semana_epidemiologica'].tolist()[20:]
semana_seleccionada = st.sidebar.select_slider("Semana Límite de Entrenamiento:", options=opciones_fechas, value=opciones_fechas[-5])

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
if semana_seleccionada not in opciones_fechas:
    st.sidebar.warning("Semana epidemiológica fuera del rango válido.")
    registrar_evento("ERROR", "Semana epidemiológica inválida", nivel="WARNING")

if st.sidebar.button("⟳  Actualizar Predicción"):
    registrar_evento("FILTROS_ACTUALIZADOS", f"Periodo={periodo}, Distrito={distrito}, Horizonte={horizonte}")
    registrar_evento("PREPARACION_MODELADO", "Preparación de datos para modelado")
    st.sidebar.success("Información actualizada para fines demostrativos.")

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

indice_corte = df_historico[df_historico['semana_epidemiologica'] == semana_seleccionada].index[0]
semana_a_predecir_info = df_historico.iloc[indice_corte]
valor_real_futuro = int(semana_a_predecir_info['casos_notificados'])
df_entrenamiento = df_historico.iloc[:indice_corte].copy()

# Tarjetas superiores
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f"""
    <div class="custom-card">
        <div class="label">Casos reales (Semana {semana_a_predecir_info['semana_epidemiologica']})</div>
        <div class="value">{valor_real_futuro}</div>
        <div class="sub">Dato histórico observado</div>
    </div>
    """, unsafe_allow_html=True)
with col2:
    # Corrección 5: Mejorar la tarjeta de predicción
    st.markdown(f"""
    <div class="custom-card">
        <div class="label">Predicción de casos</div>
        <div class="value sky" style="font-size:24px;">En desarrollo</div>
        <div class="sub">Horizonte seleccionado: {horizonte}</div>
    </div>
    """, unsafe_allow_html=True)
with col3:
    # Corrección 6: Cambiar la tarjeta de riesgo
    st.markdown(f"""
    <div class="custom-card">
        <div class="label">Riesgo preliminar</div>
        <div class="value amber">MEDIO</div>
        <div class="sub">Valor demostrativo; pendiente de validación del modelo</div>
    </div>
    """, unsafe_allow_html=True)
with col4:
    # Corrección 9: Mejorar "Calidad de datos"
    fecha_actual = datetime.now().strftime('%d/%m/%Y')
    st.markdown(f"""
    <div class="custom-card" style="padding:12px 16px;">
        <div class="label" style="margin-bottom:8px;">Calidad de datos</div>
        <div class="list-item">Completitud: <b>96 %</b></div>
        <div class="list-item">Registros duplicados: <b>0</b></div>
        <div class="list-item">Valores faltantes: <b>4 %</b></div>
        <div class="list-item">Última actualización: <b>{fecha_actual}</b></div>
    </div>
    """, unsafe_allow_html=True)

col_chart, col_map = st.columns([1.8, 1])
with col_chart:
    # Corrección 7: Título del gráfico y mensaje de pendiente
    st.markdown(f"<div class='custom-card' style='padding:14px; margin-bottom:0;'><h3 style='margin:0 0 12px;font-size:15px;color:white;'>Casos históricos y horizonte de predicción <span style='float:right;font-size:11px;color:#c8e8f3;border:1px solid #275265;background:#0d2a36;padding:6px 9px;border-radius:8px;'>Horizonte: {horizonte}</span></h3>", unsafe_allow_html=True)
    st.line_chart(df_entrenamiento.set_index('semana_epidemiologica')['casos_notificados'], color="#17d49a", use_container_width=True)
    st.markdown("<div style='text-align:center;color:#35b7ff;font-size:12px;margin-top:-10px;padding-bottom:10px;'>Predicción pendiente de validación</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col_map:
    # Corrección 8: Mapa de riesgo por distrito
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
    # Corrección 3 y 4: Calidad del modelo y Recall
    st.markdown("""
    <div class='custom-card' style='padding:14px; height:100%;'>
        <h3 style='margin:0 0 12px;font-size:15px;color:white;'>Calidad del modelo</h3>
        <div class="metrics" style="grid-template-columns: repeat(2, 1fr); gap: 6px;">
            <div class="metric" style="padding:8px;">R²<b class="muted" style="font-size:13px;color:#9fb6c3;">Pendiente</b></div>
            <div class="metric" style="padding:8px;">MAE<b class="muted" style="font-size:13px;color:#9fb6c3;">Pendiente</b></div>
            <div class="metric" style="padding:8px;">RMSE<b class="muted" style="font-size:13px;color:#9fb6c3;">Pendiente</b></div>
            <div class="metric" style="padding:8px;">Recall<b class="muted" style="font-size:13px;color:#9fb6c3;">Pendiente</b></div>
            <div class="metric" style="grid-column: span 2; padding:8px;">Precisión<b class="muted" style="font-size:13px;color:#9fb6c3;">Pendiente</b></div>
        </div>
        <div style="font-size:10px;color:#8ca6b2;margin-top:8px;">Métricas disponibles después del entrenamiento y validación del modelo. Datos demostrativos – no corresponden a resultados finales.</div>
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
    # Corrección 11: Estado del proyecto
    st.markdown("""
    <div class='custom-card' style='padding:14px; height:100%;'>
        <h3 style='margin:0 0 12px;font-size:15px;color:white;'>Estado del Incremento</h3>
        <div style="font-size:12px; display:grid; gap:8px;">
            <div style="display:flex; justify-content:space-between;"><span>ETL</span> <span style="color:var(--amber);">En progreso</span></div>
            <div style="display:flex; justify-content:space-between;"><span>Limpieza y calidad</span> <span style="color:var(--amber);">En progreso</span></div>
            <div style="display:flex; justify-content:space-between;"><span>Ingeniería de características</span> <span style="color:var(--amber);">En progreso</span></div>
            <div style="display:flex; justify-content:space-between;"><span>Modelo predictivo</span> <span style="color:var(--muted);">Pendiente</span></div>
            <div style="display:flex; justify-content:space-between;"><span>Dashboard</span> <span style="color:var(--green);">Terminado</span></div>
            <div style="display:flex; justify-content:space-between;"><span>Seguridad</span> <span style="color:var(--amber);">En progreso</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)