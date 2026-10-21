"""Comparación exploratoria pareada; no publica modelos ni modifica el dashboard."""
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from xgboost import XGBRegressor
from experimento_confirmados_v2 import resumen, sha, guardar_json

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / 'reports/experimento_confirmados_clima_v3'
SOURCE = BASE / 'data/candidates/confirmados-3c5551eb8fa2/panel_candidato.csv'


def main():
    if (OUT / 'huellas_antes.json').exists():
        raise FileExistsError('Ejecución existente; no se sobrescribe.')
    provenance = json.loads((OUT / 'fuente_clima.json').read_text(encoding='utf-8'))
    climate_source = OUT / 'clima_lima_centro_fuente.csv'
    assert sha(BASE / provenance['archivo']) == provenance['sha256']
    assert sha(climate_source) == provenance['csv_sha256']
    cuts = json.loads((BASE / 'reports/protocolo_confirmados_v2/cortes.json').read_text())
    assert sha(SOURCE) == cuts['fuente_sha256']
    active = json.loads((BASE / 'models/actual.json').read_text())
    protected = [BASE / 'models/actual.json', BASE / active['modelo'], BASE / active['datos'],
                 SOURCE, BASE / provenance['archivo'], climate_source, OUT / 'PROTOCOLO.md',
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
    d['objetivo'] = d.casos_confirmados.fillna(0)
    def pivot(col):
        return d.pivot(index='distrito', columns='semana_epidemiologica', values=col).loc[names, weeks].to_numpy()
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
        timing.append(dict(corte=weeks[i], segundos=time.perf_counter()-start))
        print(f'Origen {number}/49: {weeks[i]}', flush=True)
    detail = pd.DataFrame(rows)
    previous = pd.read_csv(BASE / 'reports/experimento_confirmados_v2/predicciones_externas.csv')
    controls = ['cero', 'ultima_semana', 'promedio_4', 'estacional_52', 'reglas_actuales']
    keys = ['corte', 'horizonte', 'semana', 'distrito']
    truth = detail.loc[detail.modelo.eq('sin_clima')].set_index(keys)[['real', 'real_imputado']].sort_index()
    for name in controls:
        check = previous.loc[previous.modelo.eq(name)].set_index(keys)[['real', 'real_imputado']].sort_index()
        pd.testing.assert_frame_equal(truth, check)
    detail = pd.concat([detail, previous.loc[previous.modelo.isin(controls), detail.columns]], ignore_index=True)
    assert not detail.duplicated(['modelo'] + keys).any()
    assert detail.groupby(['modelo', 'corte', 'horizonte']).distrito.nunique().eq(14).all()
    detail['ano'] = detail.semana.str[:4]
    detail.to_csv(OUT / 'predicciones.csv', index=False)
    pd.DataFrame(timing).to_csv(OUT / 'tiempos.csv', index=False)
    tables = {}
    for label, groups in [('global', ['modelo']), ('horizonte', ['modelo', 'horizonte']),
                          ('distrito', ['modelo', 'distrito']), ('ano', ['modelo', 'ano'])]:
        tables[label] = resumen(detail, groups)
        tables[label].to_csv(OUT / f'metricas_{label}.csv', index=False)
    metrics = tables['global'].set_index('modelo')
    c, b = metrics.loc['con_clima'], metrics.loc['sin_clima']
    horizons = tables['horizonte'].pivot(index='modelo', columns='horizonte', values='mae')
    checks = dict(mejora_mae_2pct=bool(c.mae <= .98*b.mae),
                  ningun_horizonte_empeora=bool((horizons.loc['con_clima'] <= horizons.loc['sin_clima']).all()),
                  error_positivos_no_empeora=bool(c.mae_positivos <= b.mae_positivos),
                  sensibilidad_no_empeora=bool(c.sensibilidad >= b.sensibilidad),
                  incremento_falsos_positivos_max_2pp=bool(c.tasa_falsos_positivos <= b.tasa_falsos_positivos+.02))
    detail['error'] = abs(detail.real-detail.prediccion)
    errors = detail.groupby(['corte', 'modelo']).error.mean().unstack()
    rng = np.random.default_rng(42)
    n = len(errors)
    samples = []
    for _ in range(2000):
        starts = rng.integers(0, n-4+1, size=int(np.ceil(n/4)))
        samples.append(np.concatenate([np.arange(s, s+4) for s in starts])[:n])
    intervals = []
    for reference in ['sin_clima', 'reglas_actuales']:
        delta = (errors.con_clima-errors[reference]).to_numpy()
        draws = delta[np.array(samples)].mean(axis=1)
        lo, hi = np.quantile(draws, [.025, .975])
        intervals.append(dict(referencia=reference, diferencia_mae=float(delta.mean()),
                              limite_inferior=float(lo), limite_superior=float(hi)))
    pd.DataFrame(intervals).to_csv(OUT / 'incertidumbre_mae.csv', index=False)
    after = {str(p.relative_to(BASE)): sha(p) for p in protected}
    guardar_json(OUT / 'huellas_despues.json', after)
    assert before == after, 'Se detectó cambio en archivos protegidos.'
    result = dict(parametros=params, criterios_aporte_clima=checks, cumple_aporte_clima=all(checks.values()),
                  mejora_mae_porcentaje=float(100*(1-c.mae/b.mae)),
                  supera_referencias_2pct={name: bool(c.mae <= .98*metrics.loc[name, 'mae']) for name in controls},
                  sustituciones=len(replacements), archivos_protegidos=len(protected), huellas_identicas=True,
                  publico_modelo=False, naturaleza='Exploratorio retrospectivo; vacíos como cero provisionalmente')
    guardar_json(OUT / 'resultado.json', result)
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    main()
