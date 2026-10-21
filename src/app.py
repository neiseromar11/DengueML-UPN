"""
Sistema predictivo basado en XGBoost para la estimación semanal de casos de dengue
y la clasificación preliminar del nivel de riesgo en los 14 distritos de la DIRIS Lima Centro.

Dashboard público e informativo: sin autenticación, usuarios ni roles.
"""
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
import streamlit as st
from config import DISTRITOS_VALIDOS
from calidad_ui import mostrar_calidad
from etl import BASE
from dashboard import filtrar, indicadores
from services import leer_bundle, preparar_version, leer_json_version, predecir_version
from charts import (barras_acumulado_distrital, barras_pronostico_semana,
                    heatmap_distrital, comparador_distritos,
                    curva_historico_pronostico, resumen_riesgo_distrital,
                    estilizar, colorear_riesgo)

# ── Configuración ───────────────────────────────────────────
st.set_page_config(page_title='DengueML - DIRIS Lima Centro',
                   page_icon='🦟', layout='wide',
                   initial_sidebar_state='expanded')

st.markdown("""
<style>
.block-container {max-width: 1450px; padding-top: 1.5rem; padding-bottom: 3rem;}
h1 {letter-spacing: -.03em; font-weight: 700;}
h2, h3 {letter-spacing: -.02em; font-weight: 600; margin-top: 1.1rem; margin-bottom: 0.4rem;}

/* Hero Banner */
.hero {
  background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 60%, #2563eb 100%);
  color: #ffffff;
  border-radius: 16px;
  padding: 26px 30px;
  margin-bottom: 14px;
  box-shadow: 0 10px 25px -5px rgba(30, 58, 138, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.12);
}
.hero small {letter-spacing: .12em; text-transform: uppercase; opacity: .85; font-weight: 700; font-size: 0.78rem;}
.hero h1 {color: #ffffff; margin: 6px 0 8px 0; padding: 0; font-size: clamp(1.6rem, 2.8vw, 2.2rem); font-weight: 800;}
.hero p {margin: 0 0 16px 0; opacity: .92; max-width: 62rem; font-size: 0.98rem; line-height: 1.5;}
.chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: rgba(255, 255, 255, 0.14);
  border: 1px solid rgba(255, 255, 255, 0.26);
  backdrop-filter: blur(8px);
  border-radius: 999px;
  padding: 5px 14px;
  margin: 0 8px 8px 0;
  font-size: .84rem;
  font-weight: 500;
  color: #ffffff;
}

/* Metric Cards Layout & Visuals */
[data-testid="stHorizontalBlock"] {flex-wrap: wrap; gap: .85rem;}
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {min-width: 210px; flex: 1 1 210px;}

[data-testid="stMetric"] {
  border: 1px solid rgba(148, 163, 184, 0.2);
  background: var(--secondary-background-color);
  border-radius: 14px;
  padding: 16px 20px;
  min-height: 125px;
  box-shadow: 0 2px 6px -1px rgba(15, 23, 42, 0.05);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
[data-testid="stMetric"]:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 16px -2px rgba(15, 23, 42, 0.08);
}
[data-testid="stMetricLabel"] {font-weight: 600; font-size: 0.88rem; letter-spacing: .01em; color: var(--text-color); opacity: 0.85;}
[data-testid="stMetricValue"], [data-testid="stMetricValue"] * {
  font-size: clamp(1.15rem, 1.8vw, 1.6rem);
  font-weight: 700;
  white-space: normal;
  overflow: visible;
  line-height: 1.25;
}
[data-testid="stMetricDelta"], [data-testid="stMetricDelta"] * {
  white-space: normal;
  overflow: visible;
  line-height: 1.35;
  font-size: 0.84rem;
}

/* Colored accent borders for the 4 KPI cards */
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(1) [data-testid="stMetric"] { border-left: 5px solid #2563eb; }
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) [data-testid="stMetric"] { border-left: 5px solid #7c3aed; }
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(3) [data-testid="stMetric"] { border-left: 5px solid #059669; }
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(4) [data-testid="stMetric"] { border-left: 5px solid #0284c7; }

/* Plotly, expanders, tables */
[data-testid="stPlotlyChart"] {
  border-radius: 14px;
  overflow: hidden;
  border: 1px solid rgba(148, 163, 184, 0.15);
  background: var(--secondary-background-color);
  padding: 8px 8px 2px 8px;
}
[data-testid="stExpander"] {border-radius: 12px; border: 1px solid rgba(148, 163, 184, 0.25);}
[data-testid="stDataFrame"] {border-radius: 12px; overflow: hidden;}
[data-testid="stAlert"] {border-radius: 12px;}
[data-testid="stSidebar"] h2 {font-size: 1.15rem;}
[data-testid="stRadio"] {padding: .6rem 0;}
</style>
""", unsafe_allow_html=True)

# ── Datos y modelo ──────────────────────────────────────────
try:
    bundle = leer_bundle()
    datos, _ = preparar_version(str(BASE / bundle['datos']), bundle['sha256_datos'])
    evaluacion = leer_json_version(str(BASE / bundle['evaluacion']), bundle['version'])
except (OSError, ValueError, KeyError):
    st.error('No hay una versión operativa válida. Se requiere completar el ETL y la validación.')
    st.stop()

CORTE_SE = bundle['corte']       # e.g. "2024-SE52"
DISTRITOS_14 = sorted(DISTRITOS_VALIDOS[:-1])  # sin "Todos los distritos ..."

# ── Barra lateral ───────────────────────────────────────────
st.sidebar.header('⚙️ Parámetros de consulta')
periodo = st.sidebar.selectbox(
    'Periodo histórico visible',
    ['Todo el histórico', 'Últimas 12 semanas'], index=0,
    help='Controla los gráficos y resúmenes históricos. No modifica el pronóstico.')
horizonte = st.sidebar.selectbox(
    'Horizonte de estimación', [2, 3, 4], index=2,
    format_func=lambda n: f'{n} semanas',
    help='Controla cuántas semanas futuras se estiman.')

st.sidebar.markdown('---')
st.sidebar.markdown('**Cobertura:** 14 distritos de DIRIS Lima Centro')
st.sidebar.caption(f'Método activo: {bundle["metodo"]}')
st.sidebar.caption(f'Versión: {bundle["version"][:20]}…')
st.sidebar.caption(f'Corte histórico: {CORTE_SE}')

# ── Datos filtrados (para vistas globales) ──────────────────
ultimas_n = 12 if periodo == 'Últimas 12 semanas' else None
hist_global = filtrar(datos, None, ultimas_n)
periodo_label = 'Últimas 12 semanas' if ultimas_n else f'{datos.semana_epidemiologica.min()} a {CORTE_SE}'

vista = st.sidebar.radio('Sección', ['Resumen', 'Comparación distrital', 'Detalle del distrito', 'Calidad y límites'])
distrito_sel = st.sidebar.selectbox('Distrito', DISTRITOS_14, key='distrito_detalle') if vista == 'Detalle del distrito' else None

# La caché del servicio incluye versión, distrito y horizonte.
try:
    resultado_global = predecir_version(bundle, distrito_sel, horizonte)
except (OSError, ValueError, KeyError):
    st.error('No se pudo cargar el pronóstico de esta versión de datos.')
    st.stop()
if resultado_global.empty:
    st.info('No hay estimaciones disponibles para esta versión.')
    st.stop()
semanas_futuras = sorted(resultado_global.semana_epidemiologica.unique())
modelo_label = 'Persistencia' if bundle['metodo'] == 'baseline' else 'XGBoost'

# ── Encabezado ──────────────────────────────────────────────
st.markdown(
    f'''<div class="hero"><small>DENGUEML · OBSERVATORIO DISTRITAL</small>
<h1>Dengue: evolución y pronóstico</h1>
<p>Estimación semanal de casos registrados y clasificación preliminar del nivel de riesgo · 14 distritos de DIRIS Lima Centro.
Sistema informativo: no es diagnóstico médico ni alerta sanitaria oficial.</p>
<span class="chip">📊 Fuente: CDC Perú / MINSA (Datos Abiertos)</span>
<span class="chip">📍 Última semana observada: {CORTE_SE}</span>
<span class="chip">🔮 Estimación: {semanas_futuras[0]} a {semanas_futuras[-1]}</span>
<span class="chip">🧠 Modelo: {modelo_label}</span></div>''', unsafe_allow_html=True)

st.warning(f'Esta versión tiene corte en {CORTE_SE}. Las estimaciones parten de ese corte histórico; '
           'no representan un pronóstico actualizado a la fecha de consulta.')

# ══════════════════════════════════════════════════════════════
#  PESTAÑAS
# ══════════════════════════════════════════════════════════════
st.caption(f'VISTA: {vista.upper()} · ÁMBITO: {distrito_sel or "14 distritos de Lima Centro"}')
with st.expander('Cómo leer este dashboard'):
    st.markdown('**1. Histórico:** registros disponibles hasta la fecha de corte. '
                '**2. Estimación:** cantidad esperada después del corte, no un dato observado. '
                '**3. Calidad:** error histórico frente a referencias sencillas. '
                '**4. Riesgo:** indicador relativo experimental, no diagnóstico ni alerta oficial.')
    st.caption('Una estimación decimal representa un valor esperado, no una fracción de persona. '
               'No se muestran intervalos porque todavía no se ha validado su cobertura.')
if vista == 'Calidad y límites':
    mostrar_calidad(BASE, bundle, DISTRITOS_14)

# ──────────────────────────────────────────────────────────────
#  TAB 1: RESUMEN
# ──────────────────────────────────────────────────────────────
if vista == 'Resumen':
    kpi_global = indicadores(hist_global)

    # ── Los 4 KPI (agregado de 14 distritos) ─────────────
    st.subheader('Indicadores clave · Agregado de 14 distritos')
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            '1. Casos semanales',
            f'{kpi_global["ultima"]:,} casos',
            help=(f'Casos registrados en la última semana observada ({CORTE_SE}). '
                  'Conteo absoluto; no es tasa de incidencia (sin denominador poblacional).'))

    with c2:
        # Vista global: mostrar conteo de distritos por nivel de riesgo
        sem1 = semanas_futuras[0]
        r1 = resultado_global[resultado_global.semana_epidemiologica == sem1]
        niveles_conteo = r1.riesgo_relativo.value_counts()
        resumen_txt = ' · '.join(f'{n}: {c}' for n, c in niveles_conteo.items())
        st.metric('2. Riesgo distrital', f'{len(r1)} distritos',
                  help=(f'Distribución de los 14 distritos por nivel de riesgo '
                        f'para la primera semana estimada ({sem1}). '
                        'Clasificación experimental: BAJO (≤80%), MEDIO (>80–150%), ALTO (>150%) '
                        'respecto a la media de las últimas 12 semanas. '
                        'No constituye una alerta sanitaria oficial.'))
        st.caption(f'{resumen_txt} (semana {sem1})')

    with c3:
        st.metric('3. Anticipación',
                  'Pendiente de estimación',
                  delta=f'Horizonte: {horizonte} sem. (parámetro)',
                  delta_color='off',
                  help=('El horizonte de proyección (2-4 semanas) es un parámetro del modelo. '
                        'La capacidad real de anticipación requiere medición retrospectiva '
                        'frente a eventos definidos, aún no realizada.'))

    with c4:
        if kpi_global['tendencia_pct'] is not None:
            st.metric('4. Tendencia de casos',
                      kpi_global['tendencia_texto'],
                      delta=f'{kpi_global["diferencia_absoluta"]:+d} casos vs sem. anterior',
                      delta_color='inverse' if kpi_global['diferencia_absoluta'] else 'off',
                      help=('Variación porcentual: (Casos actuales − Casos anteriores) / '
                            'Casos anteriores × 100. Última semana observada del periodo visible.'))
        else:
            st.metric('4. Tendencia de casos',
                      kpi_global['tendencia_texto'],
                      delta=f'{kpi_global["diferencia_absoluta"]:+d} casos (ref. anterior = 0)',
                      delta_color='off',
                      help=('Porcentaje no calculable: la semana anterior registró 0 casos. '
                            'Se muestra la diferencia absoluta.'))

    st.markdown('---')

    # ── Curva histórica + pronóstico ─────────────────────
    st.subheader('Curva epidemiológica: observado vs. estimación futura')
    hist_s = hist_global.groupby('semana_epidemiologica').casos_notificados.sum()
    hist_s = hist_s.mask(hist_global.groupby('semana_epidemiologica').sin_registros_fuente.all())
    pred_s = resultado_global.groupby('semana_epidemiologica').prediccion.sum()
    fig_curva = curva_historico_pronostico(
        hist_s, pred_s, CORTE_SE,
        titulo=f'14 distritos agregados · {periodo_label}')
    st.plotly_chart(estilizar(fig_curva), use_container_width=True)
    st.caption(
        '**Línea sólida azul:** casos registrados observados (fuente oficial). '
        f'**Línea discontinua ámbar:** estimación {modelo_label}. '
        '**Línea punteada gris:** corte entre datos históricos y proyección. '
        'En la vista global, los valores son la suma de los 14 distritos.')

    # ── Barras acumuladas por distrito ───────────────────
    st.subheader('Casos acumulados por distrito')
    fig_barras = barras_acumulado_distrital(hist_global, periodo_label)
    st.plotly_chart(estilizar(fig_barras), use_container_width=True)
    st.caption('Conteo absoluto de casos registrados acumulados en el periodo visible. '
               'Los 14 distritos se muestran aunque tengan 0 casos. '
               'Gris = sin registros en la fuente (no equivale a confirmación de cero transmisión).')

    # ── Riesgo por distrito para una semana seleccionada ─
    st.subheader('Distribución de riesgo por distrito')
    sem_riesgo = st.selectbox('Semana estimada a evaluar', semanas_futuras,
                               index=0, key='sem_riesgo_resumen')
    resumen_r, tabla_r = resumen_riesgo_distrital(resultado_global, sem_riesgo)
    col_r1, col_r2 = st.columns([1, 2])
    with col_r1:
        st.dataframe(colorear_riesgo(resumen_r[['Nivel de riesgo', 'Distritos']], 'Nivel de riesgo'), hide_index=True)
    with col_r2:
        st.dataframe(colorear_riesgo(tabla_r, 'Nivel'), hide_index=True)
    st.caption(
        'Clasificación experimental por distrito para la semana seleccionada. '
        'BAJO: ≤80% de la referencia. MEDIO: >80% y ≤150%. ALTO: >150%. '
        '"Evaluación especial": referencia histórica igual a 0. '
        '"Sin datos suficientes": menos de 12 semanas de historia. '
        'No constituye una alerta sanitaria oficial.')

    # ── Tabla de predicciones ────────────────────────────
    with st.expander('Tabla completa de estimaciones'):
        cols_tabla = ['distrito', 'semana_epidemiologica', 'horizonte',
                      'prediccion', 'riesgo_relativo', 'umbral_referencia', 'explicacion']
        st.dataframe(resultado_global[cols_tabla], hide_index=True)
        csv_dl = resultado_global[cols_tabla].to_csv(index=False).encode('utf-8-sig')
        st.download_button('📥 Descargar CSV', csv_dl,
                          f'estimaciones_DIRIS_{CORTE_SE}.csv', 'text/csv')


# ──────────────────────────────────────────────────────────────
#  TAB 2: COMPARACIÓN DISTRITAL
# ──────────────────────────────────────────────────────────────
if vista == 'Comparación distrital':
    st.subheader('Mapa de calor: distritos × semanas')
    fig_heat = heatmap_distrital(hist_global, periodo_label)
    st.plotly_chart(estilizar(fig_heat), use_container_width=True)
    st.caption('Color = casos registrados por semana. Escala azul = registros observados; gris = sin registros. '
               '"Sin registros" = la semana no tiene datos en la fuente oficial.')

    st.markdown('---')

    st.subheader('Comparación de pronósticos por distrito (semana individual)')
    sem_comp = st.selectbox('Semana futura a comparar', semanas_futuras,
                             index=0, key='sem_comp_tab2')
    fig_comp = barras_pronostico_semana(resultado_global, sem_comp)
    if fig_comp:
        st.plotly_chart(estilizar(fig_comp), use_container_width=True)
        st.caption(
            f'Estimación para la semana {sem_comp} únicamente (no acumulado). '
            'Color = nivel de riesgo: 🟢 Bajo, 🟡 Medio, 🔴 Alto, 🟣 Evaluación especial.')
    else:
        st.info('No hay estimaciones para la semana seleccionada.')

    st.markdown('---')

    st.subheader('Comparador de curvas históricas')
    distritos_comp = st.multiselect(
        'Selecciona entre 2 y 4 distritos',
        DISTRITOS_14, default=DISTRITOS_14[:2],
        max_selections=4, key='comp_multi')
    if len(distritos_comp) >= 2:
        fig_cmp = comparador_distritos(hist_global, distritos_comp)
        if fig_cmp:
            st.plotly_chart(estilizar(fig_cmp), use_container_width=True)
            st.caption('Curvas históricas en el mismo periodo. Las interrupciones indican semanas sin registros en la fuente; no se interpolan.')
    elif len(distritos_comp) == 1:
        st.warning('Selecciona al menos 2 distritos para comparar.')
    else:
        st.info('Selecciona distritos en el menú superior.')

# ──────────────────────────────────────────────────────────────
#  TAB 3: DETALLE DEL DISTRITO
# ──────────────────────────────────────────────────────────────
if vista == 'Detalle del distrito':

    hist_dist = filtrar(datos, distrito_sel, ultimas_n)
    kpi_dist = indicadores(hist_dist)

    # Predicción distrital (reutiliza caché global)
    res_dist = resultado_global[resultado_global.distrito == distrito_sel].copy()

    # ── KPI distritales ──────────────────────────────────
    st.subheader(f'Indicadores clave · {distrito_sel}')
    d1, d2, d3, d4 = st.columns(4)

    with d1:
        st.metric('1. Casos semanales',
                  f'{kpi_dist["ultima"]:,} casos',
                  help=f'Casos registrados en la última semana observada ({CORTE_SE}) '
                       f'para {distrito_sel}. Conteo absoluto.')

    with d2:
        if not res_dist.empty:
            fila1 = res_dist.iloc[0]
            indice = fila1['indice_riesgo']
            st.metric('2. Nivel de riesgo',
                      fila1['riesgo_relativo'],
                      delta=f'Índice: {indice} (Ref: {fila1["umbral_referencia"]})',
                      delta_color='off',
                      help=f'Riesgo para {distrito_sel} en {fila1["semana_epidemiologica"]}. '
                           'Clasificación experimental.')
        else:
            st.metric('2. Nivel de riesgo', 'No disponible')

    with d3:
        st.metric('3. Anticipación',
                  'Pendiente de estimación',
                  delta=f'Horizonte: {horizonte} sem.',
                  delta_color='off',
                  help='Medición retrospectiva aún no realizada para este distrito.')

    with d4:
        if kpi_dist['tendencia_pct'] is not None:
            st.metric('4. Tendencia',
                      kpi_dist['tendencia_texto'],
                      delta=f'{kpi_dist["diferencia_absoluta"]:+d} casos',
                      delta_color='inverse',
                      help=f'Variación en la última semana observada de {distrito_sel}.')
        else:
            st.metric('4. Tendencia',
                      kpi_dist['tendencia_texto'],
                      delta=f'{kpi_dist["diferencia_absoluta"]:+d} casos',
                      delta_color='off',
                      help='Porcentaje no calculable (referencia anterior = 0).')

    st.markdown('---')

    # ── Curva distrital ──────────────────────────────────
    st.subheader(f'Curva epidemiológica · {distrito_sel}')
    hist_d_s = hist_dist.groupby('semana_epidemiologica').casos_notificados.sum()
    hist_d_s = hist_d_s.mask(
        hist_dist.groupby('semana_epidemiologica').sin_registros_fuente.all())
    pred_d_s = res_dist.groupby('semana_epidemiologica').prediccion.sum()
    fig_dist = curva_historico_pronostico(
        hist_d_s, pred_d_s, CORTE_SE,
        titulo=f'{distrito_sel} · {periodo_label}')
    st.plotly_chart(estilizar(fig_dist), use_container_width=True)
    st.caption(
        f'Casos registrados observados y estimación {modelo_label} para {distrito_sel}. '
        f'Las predicciones parten de {CORTE_SE}, no de la fecha actual.')

    # ── Tabla distrital ──────────────────────────────────
    st.subheader(f'Estimaciones semanales · {distrito_sel}')
    cols_det = ['semana_epidemiologica', 'horizonte', 'prediccion',
                'riesgo_relativo', 'umbral_referencia', 'explicacion']
    st.dataframe(colorear_riesgo(res_dist[cols_det], 'riesgo_relativo'), hide_index=True)

    # ── Resumen histórico ────────────────────────────────
    with st.expander(f'Resumen histórico · {distrito_sel}'):
        st.write(f'**Total acumulado en el periodo visible:** {kpi_dist["total"]:,} casos')
        st.write(f'**Semanas incluidas:** {kpi_dist["semanas"]}')
        st.write(f'**Semanas con 0 casos:** {kpi_dist["semanas_sin_registros"]}')
        st.write(f'**Semanas sin registros en fuente:** {kpi_dist["combinaciones_sin_registros"]}')


# ══════════════════════════════════════════════════════════════
#  SECCIONES DESPLEGABLES COMUNES (fuera de las pestañas)
# ══════════════════════════════════════════════════════════════
st.markdown('---')

with st.expander('🏛️ Procedencia de datos y metodología'):
    fuente_path = BASE / 'reports/fuente_oficial.json'
    if fuente_path.exists():
        try:
            info = json.loads(fuente_path.read_text(encoding='utf-8'))
            st.write(f'**Entidad:** {info.get("entidad")}')
            st.write(f'**Plataforma:** {info.get("fuente")}')
            st.write(f'**Sincronización:** {info.get("estado_sincronizacion")}')
            st.write(f'**SHA-256:** `{info.get("sha256_local")}`')
            st.caption(info.get('notas_metodologicas', ''))
        except Exception:
            pass
    st.write(f'**Versión activa:** `{bundle["version"]}`')
    st.write(
        '**Variable analizada:** Casos registrados semanales de dengue (registros Notiweb / CDC Perú). '
        'El responsable del proyecto identifica la fuente como casos confirmados. '
        'Esta condición procede de su revisión de la fuente; no se verifica mediante un campo de confirmación en el CSV. '
        'La versión activa conserva su procesamiento y no se ha mezclado con la base climática.')
    st.write(
        '**Clasificación de riesgo:** Experimental, basada en umbrales sobre la media móvil '
        'de 12 semanas. BAJO: ratio ≤ 0.8. MEDIO: ratio > 0.8 y ≤ 1.5. ALTO: ratio > 1.5. '
        'No sustituye al canal endémico del CDC Perú.')
