"""Experimento provisional, aislado del modelo publicado.

Hipótesis no confirmada: vacíos anteriores al corte = cero registros.
No utiliza clima ni modifica el panel candidato o el modelo activo.
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "src"))
from features import generar_features, obtener_feature_columns
from model import entrenar_xgboost, predecir_multistep

SOURCE = BASE / "data/candidates/confirmados-3c5551eb8fa2/panel_candidato.csv"
OUT = BASE / "reports/experimento_confirmados_v1"
PARAMS = {
    "xgb_sin_reglas": dict(objective="reg:squarederror", max_depth=3),
    "xgb_poisson_estacional": dict(objective="count:poisson", max_depth=2),
    "xgb_cuadratico_estacional": dict(objective="reg:squarederror", max_depth=2),
}
REFERENCIAS = ["cero", "ultima_semana", "promedio_4", "estacional_52"]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def variables(hist, ano, semana, nombres, extendido=True):
    # hist tiene distritos en filas, semanas pasadas en columnas.
    f = pd.DataFrame({f"lag_{i}": hist[:, -i] for i in range(1, 5)})
    from calendar_epi import fecha_semana
    mes = fecha_semana(ano, semana).month
    f["media_movil_3"] = hist[:, -3:].mean(axis=1)
    f["media_movil_4"] = hist[:, -4:].mean(axis=1)
    f["crecimiento_semanal"] = np.divide(
        hist[:, -1], hist[:, -2], out=np.ones(len(hist)), where=hist[:, -2] != 0) - 1
    f["mes"], f["trimestre"] = mes, (mes - 1) // 3 + 1
    if extendido:
        for n in (8, 12, 26, 52):
            f[f"lag_{n}"] = hist[:, -n]
        for n in (8, 12):
            f[f"media_{n}"] = hist[:, -n:].mean(axis=1)
        f["sem_sin"] = np.sin(2 * np.pi * semana / 52.1775)
        f["sem_cos"] = np.cos(2 * np.pi * semana / 52.1775)
        for nombre in nombres:
            f[f"distrito_{nombre}"] = [int(v == nombre) for v in nombres]
    return f


def metricas(d, grupos):
    filas = []
    for clave, g in d.groupby(grupos, dropna=False):
        if not isinstance(clave, tuple):
            clave = (clave,)
        positivo = g.real.gt(0)
        informado = ~g.real_imputado
        filas.append(dict(zip(grupos, clave)) | {
            "n": len(g), "mae": float(abs(g.real-g.prediccion).mean()),
            "rmse": float(np.sqrt(((g.real-g.prediccion)**2).mean())),
            "n_positivos": int(positivo.sum()),
            "mae_positivos": float(abs(g.loc[positivo, "real"]-g.loc[positivo, "prediccion"]).mean()) if positivo.any() else None,
            "positivos_pred_menor_05": int((positivo & g.prediccion.lt(.5)).sum()),
            "n_objetivos_imputados": int(g.real_imputado.sum()),
            "mae_solo_informados": float(abs(g.loc[informado, "real"]-g.loc[informado, "prediccion"]).mean()) if informado.any() else None,
        })
    return pd.DataFrame(filas)


def main():
    if OUT.exists():
        raise FileExistsError("El experimento ya existe; no se reescribe ni se reajusta con el resultado final.")
    OUT.mkdir(parents=True)
    firma_activa = sha(BASE / "models/actual.json")
    firma_fuente = sha(SOURCE)
    d = pd.read_csv(SOURCE, dtype={"ubigeo": str})
    d = d[d.ano.ge(2020)].copy()  # 2018–2019 no contienen ningún conteo informado.
    d["real_imputado"] = d.casos_confirmados.isna()
    d["casos_notificados"] = d.casos_confirmados.fillna(0).astype(float)
    nombres = sorted(d.distrito.unique())
    semanas = sorted(d.semana_epidemiologica.unique())
    y = d.pivot(index="distrito", columns="semana_epidemiologica", values="casos_notificados").reindex(index=nombres, columns=semanas).to_numpy()
    mask = d.pivot(index="distrito", columns="semana_epidemiologica", values="real_imputado").reindex(index=nombres, columns=semanas).to_numpy()
    assert len(nombres) == 14 and np.isfinite(y).all()
    pares = [(int(w[:4]), int(w[-2:])) for w in semanas]
    # Ventanas objetivo no solapadas de cuatro semanas.
    val = [i for i in range(len(semanas)-4)
           if semanas[i+1] >= "2023-SE01" and semanas[i+4] <= "2024-SE52"][::4]
    final = [i for i in range(len(semanas)-4) if semanas[i+1] >= "2025-SE01"][::4]
    protocolo = dict(
        hipotesis="Vacíos de Casos hasta 2026-SE40 tratados como cero registros; sin confirmación institucional.",
        corte="2026-SE40", inicio="2020-SE01", fuente_sha256=firma_fuente,
        modelo_activo_sha256=firma_activa, candidatos=PARAMS,
        referencias=REFERENCIAS, cortes_seleccion=[semanas[i] for i in val],
        cortes_finales=[semanas[i] for i in final],
        seleccion="Menor MAE medio de pasos 2–4 entre candidatos XGBoost, solo en selección.",
        criterio="Mejora >2% del MAE frente a cada referencia, sin empeorar ningún horizonte 2–4.",
        ajuste="Reentrenar en cada origen con información disponible hasta ese origen; configuraciones fijas.",
        limites=["Corte inferido, no certificado como consolidado", "Sin calibración de riesgo ni medición de brotes",
                 "No es validación del modelo publicado: objetivo confirmado diferente",
                 "2025–2026 permanece fuera de selección, aunque sus totales ya se inspeccionaron en auditoría",
                 "Estacional usa 52 semanas de rezago, no correspondencia exacta entre años de 53 semanas"],
        generado_utc=datetime.now(timezone.utc).isoformat(),
    )
    (OUT / "protocolo.json").write_text(json.dumps(protocolo, ensure_ascii=False, indent=2), encoding="utf-8")
    d.to_csv(OUT / "panel_hipotesis_cero.csv", index=False, encoding="utf-8-sig")
    base_features = generar_features(d)
    bloques = [variables(y[:, :j], *pares[j], nombres) for j in range(52, len(semanas))]
    X = pd.concat(bloques, ignore_index=True)
    target = y[:, 52:].T.reshape(-1)

    def ejecutar(indices, candidatos, fase):
        filas = []
        for k, i in enumerate(indices):
            ultimo = base_features[base_features.semana_epidemiologica.eq(semanas[i])].set_index("distrito").loc[nombres]
            train = base_features[base_features.semana_epidemiologica.le(semanas[i])]
            original = entrenar_xgboost(train, params=dict(max_depth=3, n_estimators=150, min_child_weight=3, reg_lambda=5))
            preds = {r: [] for r in REFERENCIAS}
            preds["xgb_reglas_actuales_reentrenado"] = np.array([
                predecir_multistep(original, ultimo.loc[n], 4) for n in nombres]).T.tolist()
            for h in range(1, 5):
                preds["cero"].append(np.zeros(14))
                preds["ultima_semana"].append(y[:, i])
                preds["promedio_4"].append(y[:, i-3:i+1].mean(axis=1))
                preds["estacional_52"].append(y[:, i+h-52])
            ntrain = (i - 51) * 14
            for nombre in candidatos:
                if nombre == "xgb_sin_reglas":
                    modelo = original
                else:
                    modelo = xgb.XGBRegressor(n_estimators=150, learning_rate=.05,
                        min_child_weight=5, reg_lambda=10, subsample=.8,
                        colsample_bytree=.8, n_jobs=1, random_state=42, **PARAMS[nombre])
                    modelo.fit(X.iloc[:ntrain], target[:ntrain])
                historia = y[:, :i+1].copy()
                preds[nombre] = []
                for h in range(1, 5):
                    f = variables(historia, *pares[i+h], nombres, nombre != "xgb_sin_reglas")
                    if nombre == "xgb_sin_reglas":
                        f = f[obtener_feature_columns()]
                    p = np.maximum(0, modelo.predict(f))
                    assert np.isfinite(p).all()
                    preds[nombre].append(p)
                    historia = np.column_stack([historia, p])
            for modelo, ps in preds.items():
                for h, p in enumerate(ps, 1):
                    for j, distrito in enumerate(nombres):
                        filas.append(dict(fase=fase, modelo=modelo, corte=semanas[i],
                            semana=semanas[i+h], horizonte=h, distrito=distrito,
                            real=float(y[j, i+h]), real_imputado=bool(mask[j, i+h]),
                            prediccion=float(p[j])))
            print(f"{fase}: {k+1}/{len(indices)}", flush=True)
        return pd.DataFrame(filas)

    seleccion = ejecutar(val, list(PARAMS), "seleccion")
    seleccion.to_csv(OUT / "seleccion_detalle.csv", index=False)
    resumen_val = metricas(seleccion[seleccion.horizonte.ge(2)], ["modelo"])
    elegido = resumen_val[resumen_val.modelo.isin(PARAMS)].sort_values("mae").iloc[0].modelo
    (OUT / "seleccion_congelada.json").write_text(json.dumps({"candidato": elegido}, indent=2), encoding="utf-8")
    print("Candidato congelado:", elegido, flush=True)
    prueba = ejecutar(final, [elegido], "final")
    prueba.to_csv(OUT / "final_detalle.csv", index=False)
    resumen_val.to_csv(OUT / "seleccion_resumen.csv", index=False)
    resumen = metricas(prueba[prueba.horizonte.ge(2)], ["modelo"])
    resumen.to_csv(OUT / "final_resumen.csv", index=False)
    mh = metricas(prueba, ["modelo", "horizonte"])
    mh.to_csv(OUT / "final_por_horizonte.csv", index=False)
    metricas(prueba[prueba.horizonte.ge(2)], ["modelo", "distrito"]).to_csv(OUT / "final_por_distrito.csv", index=False)
    prueba["ano"] = prueba.semana.str[:4]
    metricas(prueba[prueba.horizonte.ge(2)], ["modelo", "ano"]).to_csv(OUT / "final_por_ano.csv", index=False)
    valores = resumen.set_index("modelo").mae
    tabla_h = mh[mh.horizonte.ge(2)].pivot(index="modelo", columns="horizonte", values="mae")
    supera = {r: bool(valores[elegido] < valores[r]*.98 and (tabla_h.loc[elegido] <= tabla_h.loc[r]).all()) for r in REFERENCIAS}
    resultado = dict(candidato=elegido, supera_criterio_por_referencia=supera,
                     supera_todas=all(supera.values()), provisional=True, publicado=False)
    assert sha(BASE / "models/actual.json") == firma_activa and sha(SOURCE) == firma_fuente
    (OUT / "resultado.json").write_text(json.dumps(resultado, indent=2), encoding="utf-8")
    print(resumen.to_string(index=False))
    print(json.dumps(resultado))


if __name__ == "__main__":
    main()
