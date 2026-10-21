"""Piloto provincial retrospectivo aislado; no publica modelos."""
import hashlib
import json
import sys
import time
from pathlib import Path
import numpy as np
import pandas as pd
from xgboost import XGBRegressor

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / 'src'))
from calendar_epi import fecha_semana, siguiente_semana
OUT = BASE / 'reports/experimento_provincias_v1'
SOURCE = BASE / 'datos_abiertos_vigilancia_dengue_2000_2024.csv'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def save(name, obj):
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')


def metrics(data, groups):
    out = []
    for key, g in data.groupby(groups):
        key = key if isinstance(key, tuple) else (key,)
        e = g.real-g.prediccion
        positive = g.real.gt(0)
        out.append(dict(zip(groups, key)) | dict(n=len(g), mae=float(abs(e).mean()),
            rmse=float(np.sqrt((e**2).mean())), mae_positivos=float(abs(e[positive]).mean()) if positive.any() else None,
            positivos=int(positive.sum())))
    return pd.DataFrame(out)


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    (OUT / 'PROTOCOLO.md').write_text('''# Piloto provincial v1
Fijado antes del ajuste. Objetivo: conteo semanal de registros del CSV, no confirmados ni incidencia por población.
Entrenar desde 2015, evaluar 2023 y 2024: orígenes SE04,08,...,48 de cada año; horizontes 2,3,4.
Territorios: códigos provinciales con registros antes de 2023. Provincias que aparecen después se documentan pero no se evalúan.
Una fila equivale a un registro; no eliminar filas idénticas sin identificador de caso. No se certifica que cada fila represente un paciente único.
Completar combinaciones sin filas con cero registros, no afirmar ausencia de transmisión o vigilancia completa.
Mismo modelo fijo XGBoost Poisson directo por horizonte: 100 árboles, profundidad3, eta0.05, min_child_weight5, lambda10, subsample0.8, colsample0.8, seed42, hist, n_jobs2.
Rezagos 0,1,2,3,7,11,25,51; medias4,8,12; ceros12; estacionalidad objetivo; provincia one-hot. Sin clima ni búsqueda de parámetros.
Entrenamiento expansivo: toda etiqueta debe ser <= corte. Controles persistencia, promedio4, estacional52 y cero.
Reportar MAE/RMSE por horizonte/año/provincia, error positivo, promedio macro provincial y porcentaje de provincias donde mejora.
Bootstrap pareado de diferencias MAE por origen, bloques móviles4, 2000 remuestreos seed42.
Criterio exploratorio: >=2% mejor MAE que cada control, sin empeorar ningún horizonte frente a persistencia. No publicar aunque cumpla.
No comparar MAE absoluto con los experimentos distritales: cambian escala, población, objetivo y periodo. No garantiza cobertura de todas las provincias del Perú.
La convención temporal se valida para 2015 en adelante; discrepancias anteriores se registran y no se corrigen silenciosamente.
''', encoding='utf-8')
    active = json.loads((BASE / 'models/actual.json').read_text())
    protected = [SOURCE, BASE / 'models/actual.json', BASE / active['modelo'], BASE / active['datos'], *sorted((BASE / 'src').rglob('*.py'))]
    before = {str(p.relative_to(BASE)): sha(p) for p in protected}
    save('huellas_antes.json', before)
    d = pd.read_csv(SOURCE, sep=';', dtype=str)
    assert not d[['ano', 'semana', 'ubigeo', 'provincia', 'departamento']].isna().any().any()
    assert d.ubigeo.str.fullmatch(r'\d{6}').all()
    d['ano'] = pd.to_numeric(d.ano, errors='raise').astype(int)
    d['semana'] = pd.to_numeric(d.semana, errors='raise').astype(int)
    d['codigo'] = d.ubigeo.str[:4]
    assert d.groupby('codigo').provincia.nunique().max() == 1
    errors = []
    for (year, week), count in d.groupby(['ano', 'semana']).size().items():
        try:
            fecha_semana(year, week)
        except ValueError:
            errors.append(dict(ano=year, semana=week, registros=int(count)))
    assert all(x['ano'] < 2015 for x in errors)
    known = sorted(d.loc[d.ano.lt(2023), 'codigo'].unique())
    catalog = d[['codigo', 'departamento', 'provincia']].drop_duplicates().copy()
    catalog['evaluada'] = catalog.codigo.isin(known)
    catalog.to_csv(OUT / 'catalogo_cobertura.csv', index=False)
    save('auditoria_fuente.json', dict(registros=len(d), provincias=int(d.codigo.nunique()), provincias_evaluadas=len(known),
        anos=d.groupby('ano').size().to_dict(), calendario_incompatible_fuera_entrenamiento=errors,
        diagnosticos=d.diagnostic.value_counts().to_dict(), confirmado_identificable=False))
    weeks = []
    a, s = 2015, 1
    while (a, s) <= (2024, 52):
        weeks.append(f'{a}-SE{s:02d}')
        a, s = siguiente_semana(a, s)
    d = d.loc[d.ano.ge(2015) & d.ano.le(2024) & d.codigo.isin(known)].copy()
    d['periodo'] = d.ano.astype(str)+'-SE'+d.semana.astype(str).str.zfill(2)
    grouped = d.groupby(['codigo', 'periodo']).size()
    index = pd.MultiIndex.from_product([known, weeks], names=['codigo', 'periodo'])
    panel = grouped.reindex(index, fill_value=0).rename('registros').reset_index()
    assert panel.registros.sum() == len(d)
    panel.to_csv(OUT / 'panel_provincial.csv', index=False)
    y = panel.registros.to_numpy().reshape(len(known), len(weeks))
    n = len(known)
    matrices, targets = {}, {}
    for h in (2, 3, 4):
        blocks = []
        for i in range(51, len(weeks)-h):
            f = np.column_stack([y[:, i-lag] for lag in (0,1,2,3,7,11,25,51)] +
                [y[:, i-k+1:i+1].mean(axis=1) for k in (4,8,12)] +
                [(y[:, i-11:i+1] == 0).sum(axis=1),
                 np.full(n, np.sin(2*np.pi*int(weeks[i+h][-2:])/52.1775)),
                 np.full(n, np.cos(2*np.pi*int(weeks[i+h][-2:])/52.1775))])
            blocks.append(np.column_stack([f, np.eye(n)]))
        matrices[h] = np.concatenate(blocks).astype(np.float32)
        targets[h] = y[:, 51+h:].T.reshape(-1)
    cuts = [f'{year}-SE{week:02d}' for year in (2023,2024) for week in range(4,49,4)]
    save('cortes.json', cuts)
    rows, timings = [], []
    for number, cut in enumerate(cuts, 1):
        started = time.perf_counter()
        i = weeks.index(cut)
        for h in (2,3,4):
            count = (i-h-51+1)*n
            assert count//n-1+51+h == i
            model = XGBRegressor(objective='count:poisson', n_estimators=100, max_depth=3,
                learning_rate=.05, min_child_weight=5, reg_lambda=10, subsample=.8,
                colsample_bytree=.8, random_state=42, n_jobs=2, tree_method='hist')
            model.fit(matrices[h][:count], targets[h][:count])
            prediction = model.predict(matrices[h][(i-51)*n:(i-50)*n])
            preds = dict(xgboost=np.maximum(prediction,0), ultima_semana=y[:,i],
                promedio_4=y[:,i-3:i+1].mean(axis=1), estacional_52=y[:,i+h-52], cero=np.zeros(n))
            for name, pred in preds.items():
                assert np.isfinite(pred).all()
                for j, code in enumerate(known):
                    rows.append(dict(modelo=name, corte=cut, horizonte=h, periodo=weeks[i+h], codigo=code,
                        real=int(y[j,i+h]), prediccion=float(pred[j]), ano=int(weeks[i+h][:4])))
        timings.append(dict(corte=cut, segundos=time.perf_counter()-started))
        print(f'Corte {number}/{len(cuts)}: {cut}', flush=True)
    result = pd.DataFrame(rows)
    assert not result.duplicated(['modelo','corte','horizonte','codigo']).any()
    result.to_csv(OUT / 'predicciones.csv', index=False)
    pd.DataFrame(timings).to_csv(OUT / 'tiempos.csv', index=False)
    tables = {}
    for label, groups in [('global',['modelo']),('horizonte',['modelo','horizonte']),('provincia',['modelo','codigo']),('ano',['modelo','ano'])]:
        tables[label] = metrics(result, groups)
        tables[label].to_csv(OUT / f'metricas_{label}.csv', index=False)
    glob = tables['global'].set_index('modelo')
    htab = tables['horizonte'].pivot(index='modelo',columns='horizonte',values='mae')
    ptab = tables['provincia'].pivot(index='codigo',columns='modelo',values='mae')
    result['error'] = abs(result.real-result.prediccion)
    err = result.groupby(['corte','modelo']).error.mean().unstack()
    rng = np.random.default_rng(42)
    draws = np.array([np.concatenate([np.arange(s,s+4) for s in rng.integers(0,len(err)-3,size=6)]) for _ in range(2000)])
    intervals = []
    for name in ['ultima_semana','promedio_4','estacional_52','cero']:
        delta = (err.xgboost-err[name]).to_numpy()
        lo, hi = np.quantile(delta[draws].mean(axis=1), [.025,.975])
        intervals.append(dict(referencia=name,diferencia_mae=float(delta.mean()),inferior=float(lo),superior=float(hi)))
    pd.DataFrame(intervals).to_csv(OUT / 'incertidumbre.csv',index=False)
    after = {str(p.relative_to(BASE)):sha(p) for p in protected}
    save('huellas_despues.json',after)
    assert before == after
    save('resultado.json',dict(mejora_2pct_cada_control={name:bool(glob.loc['xgboost','mae']<=.98*glob.loc[name,'mae']) for name in ['ultima_semana','promedio_4','estacional_52','cero']},
        no_empeora_horizontes=bool((htab.loc['xgboost']<=htab.loc['ultima_semana']).all()),
        provincias_mejora_persistencia=int((ptab.xgboost<ptab.ultima_semana).sum()),
        provincias_empata_persistencia=int((ptab.xgboost==ptab.ultima_semana).sum()),
        provincias=n, huellas_identicas=True, archivos_protegidos=len(protected), publico_modelo=False))
    print(tables['global'].to_string(index=False), flush=True)


if __name__ == '__main__':
    main()
