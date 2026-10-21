"""Ejecuta el protocolo v2 exclusivamente en reports/experimento_confirmados_v2."""
import hashlib
import json
import sys
import time
from pathlib import Path
from functools import lru_cache

import numpy as np
import pandas as pd
import xgboost as xgb

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "src"))
from features import generar_features
from model import entrenar_xgboost, predecir_multistep

SOURCE = BASE / "data/candidates/confirmados-3c5551eb8fa2/panel_candidato.csv"
PROTOCOL = BASE / "reports/protocolo_confirmados_v2"
OUT = BASE / "reports/experimento_confirmados_v2"
CANDIDATOS = ["directo_2", "directo_3", "dos_etapas_2", "dos_etapas_3"]
REFS = ["cero", "ultima_semana", "promedio_4", "estacional_52"]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def guardar_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False),
                    encoding="utf-8")


def resumen(d, grupos):
    filas = []
    for key, g in d.groupby(grupos):
        if not isinstance(key, tuple):
            key = (key,)
        realpos = g.real.ge(1)
        predpos = g.prediccion.ge(.5)
        tp = int((realpos & predpos).sum())
        fn = int((realpos & ~predpos).sum())
        fp = int((~realpos & predpos).sum())
        tn = int((~realpos & ~predpos).sum())
        error = abs(g.real-g.prediccion)
        prob = g.probabilidad.notna()
        filas.append(dict(zip(grupos, key)) | dict(
            n=len(g), mae=float(error.mean()), rmse=float(np.sqrt((error**2).mean())),
            mae_positivos=float(error[realpos].mean()) if realpos.any() else None,
            mae_informados=float(error[~g.real_imputado].mean()) if (~g.real_imputado).any() else None,
            imputados=int(g.real_imputado.sum()), tp=tp, fn=fn, fp=fp, tn=tn,
            sensibilidad=tp/(tp+fn) if tp+fn else None,
            precision_positiva=tp/(tp+fp) if tp+fp else None,
            tasa_falsos_positivos=fp/(fp+tn) if fp+tn else None,
            n_probabilidad=int(prob.sum()),
            brier=float(((g.loc[prob, "probabilidad"]-realpos[prob].astype(int))**2).mean()) if prob.any() else None))
    return pd.DataFrame(filas)


def main():
    if OUT.exists():
        raise FileExistsError("La ejecución existe; no se sobrescribe.")
    cortes = json.loads((PROTOCOL / "cortes.json").read_text())
    assert sha(SOURCE) == cortes["fuente_sha256"]
    assert sha(PROTOCOL / "PROTOCOLO.md") == cortes["protocolo_sha256"]
    active = json.loads((BASE / "models/actual.json").read_text())
    protegidos = [BASE / "models/actual.json", BASE / active["modelo"], BASE / active["datos"],
                  SOURCE, *sorted((BASE / "src").glob("*.py"))]
    huellas = {str(p.relative_to(BASE)): sha(p) for p in protegidos}
    OUT.mkdir(parents=True)
    guardar_json(OUT / "huellas_antes.json", huellas)
    guardar_json(OUT / "cortes_utilizados.json", cortes)
    d = pd.read_csv(SOURCE, dtype={"ubigeo": str})
    d = d[d.ano.ge(2020)].copy()
    d["real_imputado"] = d.casos_confirmados.isna()
    d["casos_notificados"] = d.casos_confirmados.fillna(0).astype(float)
    nombres = sorted(d.distrito.unique())
    semanas = sorted(d.semana_epidemiologica.unique())
    idx = {s: i for i, s in enumerate(semanas)}
    y = d.pivot(index="distrito", columns="semana_epidemiologica", values="casos_notificados").loc[nombres, semanas].to_numpy()
    missing = d.pivot(index="distrito", columns="semana_epidemiologica", values="real_imputado").loc[nombres, semanas].to_numpy()
    assert y.shape[0] == 14 and np.isfinite(y).all()
    features_actuales = generar_features(d)
    # Matrices ordenadas por origen, luego distrito. Las etiquetas se limitan en cada ajuste.
    matrices = {}
    objetivos = {}
    for h in (2, 3, 4):
        bloques = []
        for s in range(51, len(semanas)-h):
            f = pd.DataFrame({f"casos_rezago_{lag}": y[:, s-lag] for lag in (0, 1, 2, 3, 7, 11, 25, 51)})
            for n in (4, 8, 12):
                f[f"media_{n}"] = y[:, s-n+1:s+1].mean(axis=1)
            f["ceros_12"] = (y[:, s-11:s+1] == 0).sum(axis=1)
            f["imputados_12"] = missing[:, s-11:s+1].sum(axis=1)
            week = int(semanas[s+h][-2:])
            f["sem_sin"] = np.sin(2*np.pi*week/52.1775)
            f["sem_cos"] = np.cos(2*np.pi*week/52.1775)
            for n in nombres:
                f[f"distrito_{n}"] = [int(n == v) for v in nombres]
            bloques.append(f)
        matrices[h] = pd.concat(bloques, ignore_index=True)
        objetivos[h] = y[:, 51+h:].T.reshape(-1)
    internos = []
    tiempos = []
    casos_especiales = []
    internos_guardados = set()
    comunes = dict(n_estimators=150, learning_rate=.05, min_child_weight=5,
                   reg_lambda=10, subsample=.8, colsample_bytree=.8,
                   random_state=42, n_jobs=1)

    def filas(i, nombre, pred, probs=None):
        rows = []
        for k, h in enumerate((2, 3, 4)):
            for j, distrito in enumerate(nombres):
                rows.append(dict(modelo=nombre, corte=semanas[i], horizonte=h,
                    semana=semanas[i+h], distrito=distrito, real=float(y[j, i+h]),
                    real_imputado=bool(missing[j, i+h]), prediccion=float(pred[k][j]),
                    probabilidad=float(probs[k][j]) if probs is not None else np.nan))
        return pd.DataFrame(rows)

    @lru_cache(maxsize=None)
    def predecir(i, nombre):
        inicio = time.perf_counter()
        if nombre in REFS:
            pred = [np.zeros(14) if nombre == "cero" else
                    y[:, i] if nombre == "ultima_semana" else
                    y[:, i-3:i+1].mean(axis=1) if nombre == "promedio_4" else
                    y[:, i+h-52] for h in (2, 3, 4)]
            out = filas(i, nombre, pred)
        elif nombre == "reglas_actuales":
            train = features_actuales[features_actuales.semana_epidemiologica.le(semanas[i])]
            modelo = entrenar_xgboost(train, params=dict(max_depth=3, n_estimators=150, min_child_weight=3, reg_lambda=5))
            ultimos = train[train.semana_epidemiologica.eq(semanas[i])].set_index("distrito").loc[nombres]
            pred = np.array([predecir_multistep(modelo, ultimos.loc[n], 4)[1:] for n in nombres]).T
            out = filas(i, nombre, pred)
        else:
            depth = int(nombre[-1])
            pred, probs = [], []
            for h in (2, 3, 4):
                # último origen entrenable s=i-h; todas sus etiquetas <=i.
                count = (i-h-51+1)*14
                assert count > 0 and (count//14-1+51+h) == i
                X = matrices[h].iloc[:count]
                target = objetivos[h][:count]
                xp = matrices[h].iloc[(i-51)*14:(i-50)*14]
                assert len(xp) == 14 and len(X) == len(target)
                if nombre.startswith("directo"):
                    reg = xgb.XGBRegressor(objective="count:poisson", max_depth=depth, **comunes)
                    if not target.any():
                        pred.append(np.zeros(14))
                        casos_especiales.append(dict(corte=semanas[i], candidato=nombre, horizonte=h, caso="regresion_sin_positivos"))
                    else:
                        reg.fit(X, target)
                        pred.append(np.maximum(0, reg.predict(xp)))
                else:
                    positive = target > 0
                    if positive.all() or not positive.any():
                        probability = np.full(14, float(positive.all()))
                        casos_especiales.append(dict(corte=semanas[i], candidato=nombre, horizonte=h, caso="clasificacion_una_clase"))
                    else:
                        clf = xgb.XGBClassifier(objective="binary:logistic", max_depth=depth, **comunes)
                        clf.fit(X, positive.astype(int))
                        probability = clf.predict_proba(xp)[:, 1]
                    if positive.any():
                        reg = xgb.XGBRegressor(objective="count:poisson", max_depth=depth, **comunes)
                        reg.fit(X.loc[positive], target[positive])
                        quantity = np.maximum(1, reg.predict(xp))
                    else:
                        quantity = np.ones(14)
                    pred.append(probability*quantity)
                    probs.append(probability)
            assert np.isfinite(pred).all()
            out = filas(i, nombre, pred, probs if probs else None)
        tiempos.append(dict(corte=semanas[i], modelo=nombre, segundos=time.perf_counter()-inicio))
        return out

    externos, selecciones = [], []
    for numero, fold in enumerate(cortes["cortes"], 1):
        i = idx[fold["origen_externo"]]
        conjuntos = {}
        for nombre in CANDIDATOS + REFS:
            partes = []
            for origen in fold["origenes_internos"]:
                j = idx[origen]
                assert j+4 <= i
                parte = predecir(j, nombre)
                partes.append(parte)
                if (j, nombre) not in internos_guardados:
                    internos.append(parte)
                    internos_guardados.add((j, nombre))
            conjuntos[nombre] = pd.concat(partes, ignore_index=True)
        def orden(nombre):
            g = conjuntos[nombre]
            mae = float(abs(g.real-g.prediccion).mean())
            p = g.real.gt(0)
            posmae = float(abs(g.loc[p, "real"]-g.loc[p, "prediccion"]).mean()) if p.any() else float("inf")
            return (round(mae, 6), posmae, int(nombre[-1]), 0 if nombre.startswith("directo") else 1)
        elegido = min(CANDIDATOS, key=orden)
        referencia = min(REFS, key=lambda n: (float(abs(conjuntos[n].real-conjuntos[n].prediccion).mean()), n))
        selecciones.append(dict(corte=semanas[i], candidato=elegido, referencia=referencia,
                                mae_interno=orden(elegido)[0]))
        candidato = predecir(i, elegido).copy()
        candidato["configuracion"] = elegido
        candidato["modelo"] = "candidato_anidado"
        externos.append(candidato)
        for nombre in REFS + ["reglas_actuales"]:
            externos.append(predecir(i, nombre))
        ref = predecir(i, referencia).copy()
        ref["configuracion"] = referencia
        ref["modelo"] = "referencia_anidada"
        externos.append(ref)
        print(f"Origen {numero}/49: {semanas[i]} / {elegido}", flush=True)
    detalle = pd.concat(externos, ignore_index=True)
    assert not detalle.duplicated(["modelo", "corte", "distrito", "horizonte"]).any()
    assert detalle.groupby(["modelo", "corte", "horizonte"]).distrito.nunique().eq(14).all()
    detalle["ano"] = detalle.semana.str[:4]
    detalle.to_csv(OUT / "predicciones_externas.csv", index=False)
    pd.concat(internos, ignore_index=True).to_csv(OUT / "predicciones_internas.csv", index=False)
    pd.DataFrame(selecciones).to_csv(OUT / "selecciones.csv", index=False)
    pd.DataFrame(tiempos).to_csv(OUT / "tiempos.csv", index=False)
    guardar_json(OUT / "casos_especiales.json", casos_especiales)
    tablas = {}
    for nombre, groups in [("global", ["modelo"]), ("horizonte", ["modelo", "horizonte"]),
                           ("distrito", ["modelo", "distrito"]), ("ano", ["modelo", "ano"])]:
        tablas[nombre] = resumen(detalle, groups)
        tablas[nombre].to_csv(OUT / f"metricas_{nombre}.csv", index=False)
    glob = tablas["global"].set_index("modelo")
    htab = tablas["horizonte"].pivot(index="modelo", columns="horizonte", values="mae")
    candidate, actual = glob.loc["candidato_anidado"], glob.loc["reglas_actuales"]
    checks = {
        "mae_mejora_2pct_todas_referencias": bool(all(candidate.mae <= glob.loc[n, "mae"]*.98 and glob.loc[n, "mae"] > 0 for n in REFS+["reglas_actuales"])),
        "sin_empeorar_horizontes": bool(all((htab.loc["candidato_anidado"] <= htab.loc[n]).all() for n in ["reglas_actuales", "referencia_anidada"])),
        "sin_empeorar_positivos": bool(all(candidate.mae_positivos <= glob.loc[n, "mae_positivos"] for n in ["reglas_actuales", "referencia_anidada"])),
        "sensibilidad_y_falsos_positivos": bool(candidate.sensibilidad >= actual.sensibilidad+.05 and candidate.tasa_falsos_positivos <= actual.tasa_falsos_positivos+.02),
        "desglose_completo": True,
    }
    rng = np.random.default_rng(42)
    origenes = [f["origen_externo"] for f in cortes["cortes"]]
    err = detalle.assign(error=abs(detalle.real-detalle.prediccion)).groupby(["corte", "modelo"]).error.mean().unstack().loc[origenes]
    samples = np.array([np.concatenate([np.arange(s, s+4) for s in rng.integers(0, len(err)-3, size=13)])[:len(err)] for _ in range(2000)])
    intervalos = []
    for nombre in REFS+["reglas_actuales", "referencia_anidada"]:
        delta = (err.candidato_anidado-err[nombre]).to_numpy()
        lo, hi = np.quantile(delta[samples].mean(axis=1), [.025, .975])
        intervalos.append(dict(comparador=nombre, diferencia_mae=float(delta.mean()),
                               inferior_95=float(lo), superior_95=float(hi)))
    pd.DataFrame(intervalos).to_csv(OUT / "incertidumbre_mae.csv", index=False)
    despues = {str(p.relative_to(BASE)): sha(p) for p in protegidos}
    assert despues == huellas, "Algún archivo protegido cambió durante la ejecución."
    guardar_json(OUT / "huellas_despues.json", despues)
    resultado = dict(criterios=checks, cumple_todos=all(checks.values()),
                     provisional=True, publicado=False, archivos_protegidos_intactos=True)
    guardar_json(OUT / "resultado.json", resultado)
    print(tablas["global"].to_string(index=False))
    print(json.dumps(resultado))


if __name__ == "__main__":
    main()
