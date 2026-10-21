from pathlib import Path
from streamlit.testing.v1 import AppTest


def test_dashboard_publico_predice_y_filtra_automaticamente():
    p = Path(__file__).resolve().parents[1] / 'src/app.py'
    at = AppTest.from_file(str(p), default_timeout=30).run()
    assert not at.exception
    assert not at.error

    # Verifica que existen métricas de los 4 KPI
    assert len(at.metric) >= 4
    assert 'casos' in at.metric[0].value.lower()
    assert at.metric[2].value == 'Pendiente de estimación'

    # Cambia horizonte de proyección a 2 semanas
    at.sidebar.selectbox[1].select(2).run()
    assert not at.exception
    assert not at.error

    # Cambia ventana histórica a 'Últimas 12 semanas'
    at.sidebar.selectbox[0].select('Últimas 12 semanas').run()
    assert not at.exception
    assert not at.error
