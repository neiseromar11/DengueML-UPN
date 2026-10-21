"""Comparación exploratoria pareada; no publica modelos ni modifica el dashboard."""
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from xgboost import XGBRegressor
from experimento_confirmados_v2 import resumen, sha, guardar_json

BASE = Path(__file__).resolve().parents[1]
SOURCE_REPORT = BASE / 'reports/experimento_confirmados_clima_v3'
ROOT = BASE / 'reports/experimento_vacios_0_1'
SOURCE = BASE / 'data/candidates/confirmados-3c5551eb8fa2/panel_candidato.csv'


def run(fill):
    OUT = ROOT / f'vacios_{fill}'
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / 'huellas_antes.json').exists():
        raise FileExistsError('Ejecución existente; no se sobrescribe.')
    provenance = json.loads((SOURCE_REPORT / 'fuente_clima.json').read_text(encoding='utf-8'))
    climate_source = SOURCE_REPORT / 'clima_lima_centro_fuente.csv'
    assert sha(BASE / provenance['archivo']) == provenance['sha256']
    assert sha(climate_source) == provenance['csv_sha256']
    cuts = json.loads((BASE / 'reports/protocolo_confirmados_v2/cortes.json').read_text())
    assert sha(SOURCE) == cuts['fuente_sha256']
    active = json.loads((BASE / 'models/actual.json').read_text())
    protected = [BASE / 'models/actual.json', BASE / active['modelo'], BASE / active['datos'],
                 SOURCE, BASE / provenance['archivo'], climate_source, ROOT / 'PROTOCOLO.md',
                 BASE / 'reports/experimento_confirmados_v2/predicciones_externas.csv',
                 *sorted((BASE / 'src').rglob('*.py'))]
    before = {str(p.relative_to(BASE)): sha(p) for p in protected}
    guardar_json(OUT / 'huellas_antes.json', before)
    d = pd.read_csv(SOURCE)
    d = d.loc[d.ano.ge(2020)].copy()
    names = sorted(d.distrito.unique())
    weeks = sorted(d.semana_epidemiologica.unique())
    assert len(names) == 14 and not d.duplicated(['distrito', 'semana_epidemiologica']).any()
    d['imputado'] = d.casos_confirmados.isna()
    d['objetivo'] = d.casos_confirmados.fillna(fill)
    def pivot(col):
        return d.pivot(index='distrito', columns='semana_epidemiologica', values=col).loc[names, weeks].to_numpy()
    assert d.loc[~d.imputado, 'objetivo'].equals(d.loc[~d.imputado, 'casos_confirmados'])
    d[['distrito', 'semana_epidemiologica', 'casos_confirmados', 'imputado', 'objetivo']].to_csv(OUT / 'auditoria_imputacion.csv', index=False)
    y, missing = pivot('objetivo'), pivot('imputado')
    group = pd.read_csv(climate_source)
    group['semana_epidemiologica'] = group.Ano.astype(str) + '-SE' + group.Semana.astype(str).str.zfill(2)
    assert not group.semana_epidemiologica.duplicated().any()
    group = group.set_index('semana_epidemiologica')
    replacements = []
    fields = ['tmean', 'tmax', 'tmin', 'humr', 'ptot']
    for col in fields:
        flag = col + '_sustituido'
        d[flag] = 0
        proxy = d.semana_epidemiologica.map(group[col])
        eligible = d.distrito.isin(['Breña', 'Magdalena', 'Pueblo Libre', 'San Miguel'])
        mask = eligible & d[col].isna() & proxy.notna() & (col != 'ptot')
        for index in d.index[mask]:
            replacements.append(dict(distrito=d.at[index, 'distrito'], semana=d.at[index, 'semana_epidemiologica'],
                                     variable=col, valor=float(proxy[index]), fuente='Provincia: LIMA CENTRO'))
        d.loc[mask, col] = proxy[mask]
        d.loc[mask, flag] = 1
    pd.DataFrame(replacements).to_csv(OUT / 'sustituciones_territoriales.csv', index=False)
    d.groupby('distrito')[fields].agg(['count', 'size']).to_csv(OUT / 'cobertura_clima.csv')
    climate = {c: pivot(c) for c in fields + [c + '_sustituido' for c in fields]}
    matrices, targets = {}, {}
    for h in (2, 3, 4):
        blocks, expanded = [], []
        for s in range(51, len(weeks)-h):
            f = pd.DataFrame({f'casos_rezago_{lag}': y[:, s-lag] for lag in (0, 1, 2, 3, 7, 11, 25, 51)})
            for n in (4, 8, 12):
                f[f'media_{n}'] = y[:, s-n+1:s+1].mean(axis=1)
            f['ceros_12'] = (y[:, s-11:s+1] == 0).sum(axis=1)
            f['imputados_12'] = missing[:, s-11:s+1].sum(axis=1)
            week = int(weeks[s+h][-2:])
            f['sem_sin'] = np.sin(2*np.pi*week/52.1775)
            f['sem_cos'] = np.cos(2*np.pi*week/52.1775)
            for name in names:
                f[f'distrito_{name}'] = [int(name == v) for v in names]
            blocks.append(f)
            extra = {f'{col}_rezago_{lag}': values[:, s-lag] for col, values in climate.items() for lag in (2, 3, 5)}
            expanded.append(pd.concat([f, pd.DataFrame(extra)], axis=1))
        matrices[h] = {'sin_clima': pd.concat(blocks, ignore_index=True),
                       'con_clima': pd.concat(expanded, ignore_index=True)}
        targets[h] = y[:, 51+h:].T.reshape(-1)
    params = dict(objective='count:poisson', max_depth=2, n_estimators=150,
                  learning_rate=.05, min_child_weight=5, reg_lambda=10, subsample=.8,
                  colsample_bytree=.8, random_state=42, n_jobs=1)
    rows, timing = [], []
    for number, fold in enumerate(cuts['cortes'], 1):
        i = weeks.index(fold['origen_externo'])
        start = time.perf_counter()
        for h in (2, 3, 4):
            count = (i-h-51+1)*14
            assert count > 0 and count//14-1+51+h == i
            for name, matrix in matrices[h].items():
                train = matrix.iloc[:count]
                target = targets[h][:count]
                xp = matrix.iloc[(i-51)*14:(i-50)*14]
                assert len(xp) == 14 and len(target) == len(train)
                if target.any():
                    reg = XGBRegressor(**params).fit(train, target)
                    pred = np.maximum(0, reg.predict(xp))
                else:
                    pred = np.zeros(14)
                assert np.isfinite(pred).all()
                for j, district in enumerate(names):
                    rows.append(dict(modelo=name, corte=weeks[i], horizonte=h, semana=weeks[i+h],
                                     distrito=district, real=float(y[j, i+h]), real_imputado=bool(missing[j, i+h]),
                                     prediccion=float(pred[j]), probabilidad=np.nan))
        for h in (2, 3, 4):
            for name, pred in {'ultima_semana': y[:, i], 'promedio_4': y[:, i-3:i+1].mean(axis=1), 'cero': np.zeros(14), 'uno': np.ones(14)}.items():
                for j, district in enumerate(names):
                    rows.append(dict(modelo=name, corte=weeks[i], horizonte=h, semana=weeks[i+h], distrito=district, real=float(y[j, i+h]), real_imputado=bool(missing[j, i+h]), prediccion=float(pred[j]), probabilidad=np.nan))
        timing.append(dict(corte=weeks[i], segundos=time.perf_counter()-start))
        print(f'Origen {number}/49: {weeks[i]}', flush=True)
    detail = pd.DataFrame(rows)
    keys = ['modelo', 'corte', 'horizonte', 'distrito']
    assert not detail.duplicated(keys).any()
    assert detail.groupby(['modelo', 'corte', 'horizonte']).distrito.nunique().eq(14).all()
    detail['ano'] = detail.semana.str[:4]
    detail.to_csv(OUT / 'predicciones.csv', index=False)
    # Los objetivos imputados NO son observaciones confirmadas. Comparación principal en el mismo subconjunto informado.
    for scope, subset in [('informados', detail.loc[~detail.real_imputado]), ('supuestos', detail)]:
        for label, groups in [('global', ['modelo']), ('horizonte', ['modelo', 'horizonte']), ('distrito', ['modelo', 'distrito']), ('ano', ['modelo', 'ano'])]:
            resumen(subset, groups).to_csv(OUT / f'metricas_{scope}_{label}.csv', index=False)
    pd.DataFrame(timing).to_csv(OUT / 'tiempos.csv', index=False)
    after = {str(p.relative_to(BASE)): sha(p) for p in protected}
    guardar_json(OUT / 'huellas_despues.json', after)
    assert before == after
    guardar_json(OUT / 'resultado.json', dict(relleno=fill, filas_panel=len(d), celdas_rellenadas=int(d.imputado.sum()), archivos_protegidos=len(protected), huellas_identicas=True, publico_modelo=False))
    return detail


def main():
    a, b = run(0), run(1)
    keys = ['modelo', 'corte', 'horizonte', 'semana', 'distrito']
    informed = []
    for fill, detail in [(0, a), (1, b)]:
        actual = detail.loc[~detail.real_imputado].set_index(keys).sort_index()
        informed.append(actual)
    pd.testing.assert_series_equal(informed[0].real, informed[1].real)
    # Verificación de reproducibilidad del escenario 0 respecto del experimento previo.
    prior = pd.read_csv(SOURCE_REPORT / 'predicciones.csv')
    current = a[a.modelo.isin(['sin_clima', 'con_clima'])].set_index(keys).sort_index()
    prior = prior[prior.modelo.isin(['sin_clima', 'con_clima'])].set_index(keys).sort_index()
    assert np.allclose(current.prediccion, prior.prediccion, rtol=1e-6, atol=1e-6)
    parts = []
    for fill in (0, 1):
        for scope in ['informados', 'supuestos']:
            frame = pd.read_csv(ROOT / f'vacios_{fill}/metricas_{scope}_global.csv')
            frame['relleno'] = fill
            frame['evaluacion'] = scope
            parts.append(frame)
    pd.concat(parts, ignore_index=True).to_csv(ROOT / 'comparacion.csv', index=False)
    guardar_json(ROOT / 'verificacion.json', dict(objetivos_informados_identicos=True, reproduce_experimento_previo=True, modelos_publicados=False))
    print(pd.concat(parts, ignore_index=True)[['relleno', 'evaluacion', 'modelo', 'n', 'mae', 'rmse']].to_string(index=False), flush=True)


if __name__ == '__main__':
    main()
