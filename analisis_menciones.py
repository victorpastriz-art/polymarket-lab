"""¿Predice la historia de Polymarket mejor que el precio en los mercados de menciones?

Para cada mercado de menciones resuelto, y en el momento de comprar (24 h o 1 h antes del cierre),
la "tasa base" se calcula SOLO con mercados anteriores ya cerrados en ese momento:
  - mismo orador + misma palabra + mismo umbral de veces ("3+ times") -> k síes de n
  - mezclada con la tasa del orador (también solo pasado) como prior: p = (k + 2*prior) / (n + 2)
Se compara con el precio del mercado (Brier score) y se simula una estrategia:
  comprar YES si tasa_base - precio_yes > umbral, comprar NO si precio_yes - tasa_base > umbral,
  coste = precio + 1 céntimo, 10 $ por apuesta, solo si hay al menos N_MIN mercados previos de esa palabra.

Uso: python analisis_menciones.py   (lee data/menciones.csv y data/snapshots_menc.csv)
Salidas: resultados/menciones.md y resultados/menciones_estrategia.csv
"""
import bisect
import os
import re

import numpy as np
import pandas as pd

from comun import DATA, RESULTADOS

HORIZONTES = [24, 1]
UMBRALES = [0.05, 0.10, 0.15, 0.20]
N_MIN = 3
SLIP = 0.01


def umbral_veces(ctx):
    m = re.search(r"(\d+)\s*\+?\s*(?:or more\s+)?times", str(ctx), re.I)
    return int(m.group(1)) if m else 1


def tasas_pasadas(d, claves, t_corte):
    """Para cada fila, (k, n) de filas con las mismas claves cuyo cierre es anterior a t_corte de esa fila."""
    k_out = np.zeros(len(d))
    n_out = np.zeros(len(d), dtype=int)
    for _, g in d.groupby(claves, sort=False):
        g = g.sort_values("t_ref")
        ts = g["t_ref"].to_numpy()
        cum = np.concatenate([[0], np.cumsum(g["gana_yes"].to_numpy())])
        for pos, (idx, corte) in enumerate(zip(g.index, t_corte[g.index])):
            j = bisect.bisect_left(ts, corte)  # mercados cerrados antes del corte
            k_out[d.index.get_loc(idx)] = cum[j]
            n_out[d.index.get_loc(idx)] = j
    return k_out, n_out


def ic_evento(x, n_boot=2000):
    a = x.groupby("event_id").agg(r=("rend", "sum"), n=("rend", "size"))
    if len(a) < 2:
        return np.nan, np.nan
    rng = np.random.default_rng(0)
    idx = rng.integers(0, len(a), (n_boot, len(a)))
    v = a["r"].to_numpy()[idx].sum(1) / a["n"].to_numpy()[idx].sum(1)
    return np.percentile(v, 2.5), np.percentile(v, 97.5)


def main():
    m = pd.read_csv(os.path.join(DATA, "menciones.csv"))
    s = pd.read_csv(os.path.join(DATA, "snapshots_menc.csv"))
    d = s.merge(m, on="market_id").reset_index(drop=True)
    d["umbral"] = d["contexto"].map(umbral_veces)
    print(f"{len(d)} mercados de menciones con precios")

    md = ["# Mercados de menciones: historia de Polymarket vs precio", "",
          f"Mercados de menciones resueltos con precio: **{len(d)}** · oradores distintos: **{d['orador'].nunique()}** · "
          f"tasa global de YES: **{d['gana_yes'].mean():.1%}**", ""]
    filas_est = []
    for h in HORIZONTES:
        col = f"p_{h}h"
        x = d[d[col].notna()].copy()
        x["p_yes"] = np.where(x["yes_idx"] == 0, x[col], 1 - x[col]).astype(float)
        corte = x["t_ref"].to_numpy() - h * 3600
        x = x.reset_index(drop=True)
        corte = pd.Series(corte, index=x.index)
        k_p, n_p = tasas_pasadas(x, ["orador", "palabra", "umbral"], corte)
        k_o, n_o = tasas_pasadas(x, ["orador"], corte)
        glob = x["gana_yes"].mean()
        prior = (k_o + 2 * glob) / (n_o + 2)
        x["n_prev"] = n_p
        x["tasa_base"] = (k_p + 2 * prior) / (n_p + 2)

        y = x[x["n_prev"] >= N_MIN]
        b_mkt = ((y["p_yes"] - y["gana_yes"]) ** 2).mean()
        b_base = ((y["tasa_base"] - y["gana_yes"]) ** 2).mean()
        b_mix = (((y["p_yes"] + y["tasa_base"]) / 2 - y["gana_yes"]) ** 2).mean()
        md += [f"## {h} h antes del cierre", "",
               f"Mercados con al menos {N_MIN} precedentes de la misma palabra y orador: **{len(y)}**", "",
               "| Predicción | Brier score (menor = mejor) |", "|---|---|",
               f"| Precio del mercado | {b_mkt:.4f} |", f"| Tasa base histórica | {b_base:.4f} |",
               f"| Media de ambas | {b_mix:.4f} |", ""]

        md += ["| Umbral de diferencia | Apuestas | Eventos | Aciertos | Por dólar | IC 95% |", "|---|---|---|---|---|---|"]
        extra = []
        for u in UMBRALES:
            e = y.copy()
            e["dif"] = e["tasa_base"] - e["p_yes"]
            e = e[e["dif"].abs() > u]
            e["compra_yes"] = e["dif"] > 0
            e["precio"] = np.where(e["compra_yes"], e["p_yes"], 1 - e["p_yes"])
            e = e[(e["precio"] > 0.02) & (e["precio"] < 0.98)]
            e["coste"] = (e["precio"] + SLIP).clip(upper=0.999)
            e["gana"] = np.where(e["compra_yes"], e["gana_yes"], 1 - e["gana_yes"])
            e["rend"] = e["gana"] / e["coste"] - 1
            lo, hi = ic_evento(e)
            filas_est.append({"horizonte_h": h, "umbral": u, "apuestas": len(e), "eventos": e["event_id"].nunique(),
                              "aciertos": e["gana"].mean(), "rend_por_dolar": e["rend"].mean(), "ic_bajo": lo, "ic_alto": hi})
            md.append(f"| {u:.2f} | {len(e)} | {e['event_id'].nunique()} | {e['gana'].mean():.1%} | "
                      f"{e['rend'].mean():+.1%} | {lo:+.1%} a {hi:+.1%} |")
            if u == 0.10 and len(e):
                e["anio"] = pd.to_datetime(e["t_ref"], unit="s").dt.year
                por = e.groupby("anio")["rend"].agg(["size", "mean"])
                extra.append("Con umbral 0,10, por año (estabilidad): " + ", ".join(
                    f"{a}: {r['mean']:+.1%} ({int(r['size'])} apuestas)" for a, r in por.iterrows()))
                top = e.groupby("orador")["rend"].agg(["size", "mean"]).sort_values("size", ascending=False).head(8)
                extra.append("Por orador (umbral 0,10): " + ", ".join(
                    f"{o}: {r['mean']:+.1%} ({int(r['size'])})" for o, r in top.iterrows()))
        md += [""] + [l + "\n" for l in extra] + [""]

    pd.DataFrame(filas_est).to_csv(os.path.join(RESULTADOS, "menciones_estrategia.csv"), index=False)
    md += ["Notas: solo se usan mercados cerrados antes del momento de compra (sin mirar el futuro). "
           "Se han probado varios umbrales y dos horizontes: un resultado positivo aislado puede ser azar.", ""]
    with open(os.path.join(RESULTADOS, "menciones.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
