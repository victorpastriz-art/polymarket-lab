"""¿Por qué la H4 gana en unas épocas y pierde en otras? ¿Hay un filtro que aguante fuera de muestra?

1) Descompone el resultado por mes, categoría, tramo de precio y volumen, en las dos muestras.
2) Filtros "estáticos" (p. ej. quitar categorías perdedoras) se ELIGEN solo con la muestra de descubrimiento
   y se PRUEBAN en la de confirmación (y al revés, como control).
3) Filtro "de momento", que solo usa el pasado: apostar en una categoría solo si su resultado en los
   últimos 60 días (con apuestas ya resueltas antes del momento de entrar) es positivo.

Uso: python estudio_regimenes.py --muestra descubrimiento=RUTA --muestra confirmacion=RUTA
Salida: resultados/regimenes.md
"""
import argparse
import os

import numpy as np
import pandas as pd

from comun import DATA, RESULTADOS, anadir_columnas
from simular_historico import CARTERAS, apuestas

ESTRATEGIAS = ["H4-24h", "H4-4h"]
TRAMOS_P = [0.50, 0.60, 0.70, 0.85001]
TRAMOS_V = [0, 1e4, 1e5, 1e6, np.inf]
NOMBRES_V = ["<10k $", "10k-100k $", "100k-1M $", ">1M $"]
VENTANA_DIAS, MIN_HIST = 60, 20


def ic(x, col="rend", n_boot=1500):
    if len(x) < 2:
        return np.nan, np.nan
    a = x.groupby("event_id")[col].agg(["sum", "size"])
    rng = np.random.default_rng(0)
    idx = rng.integers(0, len(a), (n_boot, len(a)))
    v = a["sum"].to_numpy()[idx].sum(1) / a["size"].to_numpy()[idx].sum(1)
    return np.percentile(v, 2.5), np.percentile(v, 97.5)


def tabla(x, por, minimo=30):
    g = x.groupby(por, observed=True).agg(apuestas=("rend", "size"), aciertos=("gana", "mean"),
                                          por_dolar=("rend", "mean"), ganancia=("ganancia", "sum")).reset_index()
    return g[g["apuestas"] >= minimo]


def fmt(df):
    z = df.copy()
    for c in z.columns:
        if c in ("aciertos",):
            z[c] = z[c].map(lambda v: f"{v:.1%}")
        elif c.startswith("por_dolar") or c in ("ic_bajo", "ic_alto"):
            z[c] = z[c].map(lambda v: "—" if pd.isna(v) else f"{v:+.1%}")
        elif c.startswith("ganancia"):
            z[c] = z[c].map(lambda v: f"{v:+.0f} $")
    return z.to_markdown(index=False)


def resumen(x):
    lo, hi = ic(x)
    return {"apuestas": len(x), "por_dolar": x["rend"].mean() if len(x) else np.nan, "ic_bajo": lo, "ic_alto": hi,
            "ganancia": x["ganancia"].sum()}


def filtro_momento(x):
    """Mantiene una apuesta solo si su categoría ganaba en los 60 días previos (apuestas cerradas antes de entrar)."""
    x = x.sort_values("t_ref").copy()
    keep = np.zeros(len(x), dtype=bool)
    for _, g in x.groupby("cat"):
        t = g["t_ref"].to_numpy()
        r = g["rend"].to_numpy()
        cs = np.concatenate([[0], np.cumsum(r)])
        for i, ti in enumerate(t):
            entrada = ti - 6 * 3600  # se apuesta ~6 h antes del cierre como muy tarde
            hi_ = np.searchsorted(t, entrada, side="left")          # cerradas antes de entrar
            lo_ = np.searchsorted(t, entrada - VENTANA_DIAS * 86400, side="left")
            n = hi_ - lo_
            keep[x.index.get_loc(g.index[i])] = n >= MIN_HIST and (cs[hi_] - cs[lo_]) > 0
    return x[keep]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--muestra", action="append", required=True)
    args = ap.parse_args()
    m = pd.read_csv(os.path.join(DATA, "mercados.csv"),
                    usecols=["market_id", "event_id", "ganador_idx", "volumen", "categoria", "tags", "pregunta"])
    m = anadir_columnas(m)

    datos = {}
    for arg in args.muestra:
        nombre, ruta = arg.split("=", 1)
        s = pd.read_csv(ruta)
        d = s.merge(m[m["market_id"].isin(s["market_id"])], on="market_id")
        datos[nombre] = d[d["ganador_idx"].notna()]

    md = ["# Estudio de rachas de la H4: por qué gana o pierde según la época", ""]
    for est in ESTRATEGIAS:
        md += [f"# {est}", ""]
        ap_ = {}
        for nombre, d in datos.items():
            x = apuestas(d, est)
            x["rend"] = x["ganancia"] / 10.0
            x["tramo_precio"] = pd.cut(x["precio"], TRAMOS_P, right=False).astype(str)
            x["tramo_volumen"] = pd.cut(x["volumen"], TRAMOS_V, labels=NOMBRES_V, right=False).astype(str)
            x["periodo"] = np.where(x["mes"] >= "2026-09", "sep-nov 2026",
                                    np.where(x["mes"] >= "2026-01", "ene-ago 2026", "2024-2025"))
            ap_[nombre] = x

        # 1. Qué cambia entre la buena y la mala racha (confirmación, donde se vio la curva)
        if "confirmacion" in ap_:
            x = ap_["confirmacion"]
            md += ["## 1. Buena racha (ene-ago 2026) vs mala racha (sep-nov 2026), muestra de confirmación", ""]
            md += [fmt(tabla(x, "periodo", 1)), ""]
            g = x[x["periodo"] != "2024-2025"].groupby(["cat", "periodo"])["ganancia"].sum().unstack(fill_value=0)
            g["cambio"] = g.get("sep-nov 2026", 0) - g.get("ene-ago 2026", 0)
            n_cat = x[x["periodo"] != "2024-2025"].groupby(["cat", "periodo"]).size().unstack(fill_value=0)
            g = g.join(n_cat, rsuffix=" (apuestas)")
            peores = g.sort_values("sep-nov 2026" if "sep-nov 2026" in g.columns else "cambio").head(10).reset_index()
            peores.columns = [str(c) for c in peores.columns]
            for c in [c for c in peores.columns if "2026" in c and "apuestas" not in c] + ["cambio"]:
                peores[c] = peores[c].map(lambda v: f"{v:+.0f} $")
            md += ["Categorías que más pierden en sep-nov 2026 (ganancia en $ de cada periodo):", "",
                   peores.to_markdown(index=False), ""]
            md += ["Composición: % de apuestas por tramo de precio en cada periodo:", "",
                   (pd.crosstab(x["periodo"], x["tramo_precio"], normalize="index") * 100).round(1).to_markdown(), ""]

        # 2. ¿Los patrones se repiten en las dos muestras?
        md += ["## 2. ¿Se repite en las dos muestras? (por dólar)", ""]
        for por in ["tramo_precio", "tramo_volumen", "cat"]:
            tablas = []
            for nombre, x in ap_.items():
                t = tabla(x, por, 100)[[por, "apuestas", "por_dolar"]].rename(
                    columns={"apuestas": f"apuestas_{nombre}", "por_dolar": f"por_dolar_{nombre}"})
                tablas.append(t)
            if len(tablas) == 2:
                j = tablas[0].merge(tablas[1], on=por, how="inner")
                cols = [c for c in j.columns if c.startswith("por_dolar")]
                j["mismo_signo"] = np.sign(j[cols[0]]) == np.sign(j[cols[1]])
                md += [f"Por {por}:", "", fmt(j), ""]

        # 3. Filtros: diseñados en una muestra, probados en la otra
        if len(ap_) == 2:
            nombres = list(ap_)
            md += ["## 3. Filtros diseñados en una muestra y probados en la otra", ""]
            filas = []
            for dis, prueba in [(nombres[0], nombres[1]), (nombres[1], nombres[0])]:
                xd, xp = ap_[dis], ap_[prueba]
                t = tabla(xd, "cat", 100)
                buenas = set(t[t["por_dolar"] > 0]["cat"])
                tp = tabla(xd, "tramo_precio", 100)
                buenos_p = set(tp[tp["por_dolar"] > 0]["tramo_precio"])
                for etiqueta, sel in [
                    ("Sin filtro", xp),
                    (f"Solo categorías positivas en {dis}", xp[xp["cat"].isin(buenas)]),
                    (f"Solo tramos de precio positivos en {dis}", xp[xp["tramo_precio"].isin(buenos_p)]),
                    ("Filtro de momento (60 días, solo pasado)", filtro_momento(xp)),
                ]:
                    filas.append({"diseñado_en": dis, "probado_en": prueba, "filtro": etiqueta, **resumen(sel)})
            md += [fmt(pd.DataFrame(filas)), ""]
            md += ["Lectura: un filtro solo vale si mejora el resultado en la muestra donde NO se diseñó y el "
                   "intervalo de confianza deja de incluir el 0. El filtro de momento no se diseña con ninguna "
                   "muestra (solo mira el pasado), así que su resultado vale en las dos.", ""]

    with open(os.path.join(RESULTADOS, "regimenes.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
