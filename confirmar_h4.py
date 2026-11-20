"""Confirmación de la H4 con una muestra NUEVA de mercados históricos (ninguno usado en el backtest original).

Regla (la misma del paper trading): en cada mercado, el lado favorito si cuesta entre 0,50 y 0,85;
como máximo un mercado por evento (el de más volumen); coste = precio + deslizamiento.
Se mide a 24 h, 6 h y 1 h del cierre, con 1 y 2 céntimos de deslizamiento.

Uso: python confirmar_h4.py   (lee data/snapshots_conf.csv y data/mercados.csv)
Salida: resultados/confirmacion_h4.md y resultados/confirmacion_h4.csv
"""
import os

import numpy as np
import pandas as pd

from comun import DATA, RESULTADOS

PMIN, PMAX = 0.50, 0.85
HORIZONTES = [24, 6, 1]
SLIPS = [0.01, 0.02]


def ic_evento(g, n_boot=2000, semilla=0):
    a = g.groupby("event_id").agg(r=("rend", "sum"), n=("rend", "size"))
    if len(a) < 2:
        return np.nan, np.nan
    rng = np.random.default_rng(semilla)
    idx = rng.integers(0, len(a), (n_boot, len(a)))
    v = a["r"].to_numpy()[idx].sum(1) / a["n"].to_numpy()[idx].sum(1)
    return np.percentile(v, 2.5), np.percentile(v, 97.5)


def apuestas(d, h, slip):
    col = f"p_{h}h"
    x = d[d[col].notna()].copy()
    x["p0"] = x[col].astype(float)
    x["lado"] = np.where(x["p0"] >= 0.5, 0, 1)
    x["precio"] = np.where(x["lado"] == 0, x["p0"], 1 - x["p0"])
    x = x[(x["precio"] >= PMIN) & (x["precio"] <= PMAX)]
    x = x.sort_values("volumen", ascending=False).drop_duplicates("event_id")
    x["gana"] = (x["ganador_idx"] == x["lado"]).astype(int)
    x["coste"] = (x["precio"] + slip).clip(upper=0.999)
    x["rend"] = x["gana"] / x["coste"] - 1
    return x


def fila(x, **k):
    lo, hi = ic_evento(x)
    return {**k, "apuestas": len(x), "eventos": x["event_id"].nunique(), "precio_medio": x["precio"].mean(),
            "aciertos": x["gana"].mean(), "rend_por_dolar": x["rend"].mean(), "ic_bajo": lo, "ic_alto": hi}


def main():
    s = pd.read_csv(os.path.join(DATA, "snapshots_conf.csv"))
    m = pd.read_csv(os.path.join(DATA, "mercados.csv"),
                    usecols=["market_id", "event_id", "ganador_idx", "volumen", "categoria", "tags"])
    d = s.merge(m[m["market_id"].isin(s["market_id"])], on="market_id")
    d = d[d["ganador_idx"].notna()]
    print(f"{len(d)} mercados nuevos con precios")

    filas, tramos = [], []
    for h in HORIZONTES:
        for slip in SLIPS:
            x = apuestas(d, h, slip)
            filas.append(fila(x, horizonte_h=h, deslizamiento=slip))
            if slip == 0.01:
                for (a, b) in [(0.50, 0.60), (0.60, 0.70), (0.70, 0.85)]:
                    t = x[(x["precio"] >= a) & (x["precio"] <= b if b == 0.85 else x["precio"] < b)]
                    tramos.append(fila(t, horizonte_h=h, tramo=f"{a:.2f}-{b:.2f}"))
    R, T = pd.DataFrame(filas), pd.DataFrame(tramos)
    R.to_csv(os.path.join(RESULTADOS, "confirmacion_h4.csv"), index=False)

    def fmt(df):
        z = df.copy()
        for c in ("precio_medio",):
            z[c] = z[c].map(lambda v: f"{v:.3f}")
        for c in ("aciertos", "rend_por_dolar", "ic_bajo", "ic_alto"):
            z[c] = z[c].map(lambda v: "—" if pd.isna(v) else f"{v:+.1%}" if c != "aciertos" else f"{v:.1%}")
        return z.to_markdown(index=False)

    base = R[(R["horizonte_h"] == 24) & (R["deslizamiento"] == 0.01)].iloc[0]
    if base["ic_bajo"] > 0:
        veredicto = "SE CONFIRMA en la muestra nueva: el intervalo a 24 h queda entero por encima de 0."
    elif base["ic_alto"] < 0:
        veredicto = "NO se confirma: en la muestra nueva la H4 pierde dinero a 24 h."
    else:
        veredicto = "NO concluyente en la muestra nueva: el intervalo a 24 h incluye el 0."
    txt = ["# Confirmación de la H4 con una muestra nueva", "",
           f"Mercados nuevos con precio: **{len(d)}** (ninguno estaba en el backtest original).", "",
           f"**Veredicto (24 h, 1 céntimo de coste):** {veredicto}", "",
           "Backtest original a comparar: +5% (50–70 cts) y +7% (70–85 cts) a 24 h.", "",
           "## Resultado por horizonte y coste", "", fmt(R), "",
           "## Por tramo de precio (1 céntimo de coste)", "", fmt(T), ""]
    with open(os.path.join(RESULTADOS, "confirmacion_h4.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(txt))
    print("\n".join(txt))


if __name__ == "__main__":
    main()
