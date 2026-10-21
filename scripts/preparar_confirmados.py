"""Audita la exportación del Observatorio sin publicar ni entrenar modelos.

Uso: python scripts/preparar_confirmados.py [--fuente archivo.xlsx]
Dependencias para esta tarea: pandas y openpyxl.
Los CSV de salida son datos candidatos, NO entradas del ETL de microdatos.
"""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "src"))
from calendar_epi import fecha_semana

CATALOGO = {
    "150101": "Cercado de Lima", "150105": "Breña",
    "150113": "Jesús María", "150115": "La Victoria", "150116": "Lince",
    "150120": "Magdalena", "150121": "Pueblo Libre", "150122": "Miraflores",
    "150130": "San Borja", "150131": "San Isidro",
    "150132": "San Juan de Lurigancho", "150134": "San Luis",
    "150136": "San Miguel", "150141": "Surquillo",
}
CLIMA = ["tmean", "tmax", "tmin", "humr", "ptot"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def preparar(fuente):
    firma = sha(fuente)
    destino = BASE / "data" / "candidates" / f"confirmados-{firma[:12]}"
    if destino.exists():
        raise FileExistsError(f"La versión ya existe; no se sobrescribe: {destino}")
    activo = BASE / "models" / "actual.json"
    firma_activa = sha(activo)
    datos = pd.read_excel(fuente, sheet_name="Distrito", dtype={"UBIGEO": str})
    requeridas = {"UBIGEO", "Distrito", "Ano", "Semana", "Tipo caso", "Casos", *CLIMA}
    if not requeridas.issubset(datos.columns):
        raise ValueError(f"Faltan columnas: {sorted(requeridas - set(datos.columns))}")
    datos["UBIGEO"] = datos.UBIGEO.str.strip().str.zfill(6)
    d = datos[datos.UBIGEO.isin(CATALOGO)].copy()
    if set(d.UBIGEO) != set(CATALOGO):
        raise ValueError("La exportación no incluye los 14 UBIGEO esperados.")
    for campo in ["Ano", "Semana", "Casos", *CLIMA]:
        d[campo] = pd.to_numeric(d[campo], errors="raise")
    for campo in ["Ano", "Semana"]:
        if d[campo].isna().any() or d[campo].mod(1).ne(0).any():
            raise ValueError(f"{campo} debe contener enteros.")
        d[campo] = d[campo].astype(int)
    if not d.Semana.between(1, 53).all():
        raise ValueError("Hay semanas fuera del rango 1–53.")
    if d.duplicated(["UBIGEO", "Ano", "Semana"]).any():
        raise ValueError("Hay claves distrito-año-semana duplicadas.")
    casos = d.Casos.dropna()
    if (casos < 0).any() or casos.mod(1).ne(0).any():
        raise ValueError("Los casos deben ser conteos enteros no negativos.")
    etiquetas = d["Tipo caso"].astype("string").str.strip().str.upper()
    if (d.Casos.notna() & etiquetas.ne("CONFIRMADO").fillna(True)).any():
        raise ValueError("Hay conteos sin etiqueta CONFIRMADO.")
    if casos.empty:
        raise ValueError("No hay casos informados.")
    d = d.rename(columns={"UBIGEO": "ubigeo", "Distrito": "distrito_fuente",
                          "Ano": "ano", "Semana": "semana",
                          "Tipo caso": "tipo_caso_fuente", "Casos": "casos_confirmados"})
    d["distrito"] = d.ubigeo.map(CATALOGO)
    d["casos_confirmados"] = d.casos_confirmados.astype("Int64")
    d["semana_epidemiologica"] = d.ano.astype(str) + "-SE" + d.semana.astype(str).str.zfill(2)
    d = d.sort_values(["ubigeo", "ano", "semana"]).reset_index(drop=True)
    corte = d.loc[d.casos_confirmados.notna(), "semana_epidemiologica"].max()
    # Fecha de calendario NO inventada: se contrasta con la convención del proyecto.
    def compatible(row):
        try:
            fecha_semana(row.ano, row.semana)
            return True
        except ValueError:
            return False
    d["compatible_calendario_actual"] = d.apply(compatible, axis=1)
    d["estado_casos"] = "faltante_por_aclarar"
    d.loc[d.casos_confirmados.eq(0).fillna(False), "estado_casos"] = "cero_explicito"
    d.loc[d.casos_confirmados.gt(0).fillna(False), "estado_casos"] = "positivo_informado"
    posterior = d.semana_epidemiologica.gt(corte)
    d.loc[posterior, "estado_casos"] = "posterior_al_ultimo_conteo"
    d["clima_completo"] = d[CLIMA].notna().all(axis=1)
    panel = d[~posterior].copy()
    # No se eliminan huecos para hacer parecer consecutivas semanas separadas.
    semanas = sorted(panel.semana_epidemiologica.unique())
    indice = {s: i for i, s in enumerate(semanas)}
    panel["indice_semana_exportada"] = panel.semana_epidemiologica.map(indice)
    filas_cobertura = []
    for distrito, g in panel.groupby("distrito"):
        serie = g.set_index("semana_epidemiologica").casos_confirmados.reindex(semanas)
        racha = maxima = 0
        for presente in serie.notna():
            racha = racha + 1 if presente else 0
            maxima = max(maxima, racha)
        filas_cobertura.append(dict(
            distrito=distrito, semanas_esperadas=len(semanas),
            filas_presentes=len(g), conteos_informados=int(serie.notna().sum()),
            ceros_explicitos=int(serie.eq(0).sum()),
            faltantes=int(serie.isna().sum()), racha_max_con_conteos=maxima,
            semanas_clima_completo=int(g.clima_completo.sum())))
    cobertura = pd.DataFrame(filas_cobertura)
    anual = panel.groupby("ano").agg(
        filas=("ubigeo", "size"), conteos_informados=("casos_confirmados", "count"),
        suma_casos_disponibles=("casos_confirmados", lambda x: x.sum(min_count=1)))
    anual["faltantes"] = anual.filas - anual.conteos_informados
    semanal = panel.groupby("semana_epidemiologica").agg(
        distritos=("ubigeo", "nunique"), conteos_informados=("casos_confirmados", "count"),
        clima_completo=("clima_completo", "sum"))
    alertas_calendario = d.loc[~d.compatible_calendario_actual, ["ano", "semana"]].drop_duplicates()
    resumen = {
        "generado_utc": datetime.now(timezone.utc).isoformat(),
        "fuente_archivo": fuente.name, "fuente_sha256": firma,
        "hoja": "Distrito", "version": destino.name,
        "objetivo": "casos_confirmados", "unidad": "conteo semanal por distrito",
        "ultimo_conteo_no_nulo": corte,
        "nota_corte": "Último conteo presente; no certifica completitud ni corte oficial.",
        "filas_exportadas_14_distritos": len(d), "filas_panel_hasta_corte": len(panel),
        "filas_posteriores_separadas": int(posterior.sum()),
        "semanas_con_14_conteos": int(semanal.conteos_informados.eq(14).sum()),
        "calendario_incompatible": alertas_calendario.to_dict("records"),
        "faltantes_casos_panel": int(panel.casos_confirmados.isna().sum()),
        "politica_faltantes": "Se mantienen vacíos. No se imputan como cero.",
        "columnas_climatologicas_excluidas_como_features": [c for c in d if c.endswith("_clima")],
        "nota_clima": "No usar clima contemporáneo futuro. Evaluar rezagos y fecha de disponibilidad. Normales *_clima requieren conocer periodo de cálculo.",
        "listo_para_entrenar": False,
        "bloqueos": ["Significado de casos vacíos pendiente de documentación",
                     "Calendario semanal de la fuente pendiente de conciliación",
                     "Definir cobertura y periodo final reservado antes de entrenar"],
        "modelo_activo_sha256_antes": firma_activa,
    }
    destino.mkdir(parents=True)
    for nombre, tabla in [
        ("panel_candidato.csv", panel),
        ("filas_posteriores_al_corte.csv", d[posterior]),
        ("cobertura_distrital.csv", cobertura),
        ("cobertura_anual.csv", anual.reset_index()),
        ("cobertura_semanal.csv", semanal.reset_index()),
    ]:
        tabla.to_csv(destino / nombre, index=False, encoding="utf-8-sig")
    resumen["salidas_sha256"] = {p.name: sha(p) for p in destino.glob("*.csv")}
    if sha(activo) != firma_activa or sha(fuente) != firma:
        raise RuntimeError("El origen o el puntero activo cambió durante la auditoría.")
    (destino / "metadata.json").write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(resumen, ensure_ascii=False, indent=2))
    print(cobertura.to_string(index=False))
    print(f"Salida: {destino}")
    return destino


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fuente", type=Path,
                        default=BASE / "clima_departamento confirmado.xlsx")
    args = parser.parse_args()
    preparar(args.fuente.resolve())
