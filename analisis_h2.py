"""Paso 3: calibración del mercado y prueba de la H2.

H2: "comprar el resultado barato (≤15 céntimos) en mercados poco seguidos tiene valor esperado positivo".
La literatura (sesgo favorito-longshot) predice lo contrario: los longshots están sobrevalorados.

Para cada mercado resuelto y cada horizonte (168h, 24h, 6h, 1h antes del cierre) se consideran
los dos lados del mercado binario: lado 0 a precio p y lado 1 a precio 1-p.
Coste de compra = precio + deslizamiento (por defecto 1 céntimo) + comisión.

Uso:
    python analisis_h2.py
    python analisis_h2.py --slip 0.005 --fee 0 --solo-yes
Salidas en resultados/: calibracion.csv, h2_por_volumen.csv, h2_por_categoria.csv,
h2_menciones.csv y h2_grafico.png
"""
import argparse
import os

import numpy as np
import pandas as pd

from comun import DATA, RESULTADOS, anadir_columnas

HORIZONTES = [168, 24, 6, 1]
TRAMOS_PRECIO = [0, 0.01, 0.02, 0.05, 0.10, 0.15, 0.30, 0.50, 0.70, 0.85, 0.95, 0.98, 1.0001]
TRAMOS_VOL = [0, 1e3, 1e4, 1e5, 1e6, np.inf]
NOMBRES_VOL = ["<1k $", "1k-10k $", "10k-100k $", "100k-1M $", ">1M $"]
LONGSHOT_MIN, LONGSHOT_MAX = 0.01, 0.15


def wilson(k, n, z=1.96):
    if n == 0:
        return np.nan, np.nan
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    m = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - m, c + m


def ic_bootstrap_eventos(df, n_boot=1000, semilla=0):
    """IC 95% del rendimiento medio remuestreando EVENTOS (los tramos de un mismo evento están correlacionados)."""
    if df.empty:
        return np.nan, np.nan
    g = df.groupby("event_id")["rend"].agg(["sum", "count"])
    s, c = g["sum"].to_numpy(), g["count"].to_numpy()
    rng = np.random.default_rng(semilla)
    idx = rng.integers(0, len(g), size=(n_boot, len(g)))
    medias = s[idx].sum(1) / c[idx].sum(1)
    return np.percentile(medias, 2.5), np.percentile(medias, 97.5)


def tabla_larga(slip, fee, solo_yes):
    s = pd.read_csv(os.path.join(DATA, "snapshots.csv"))
    m = pd.read_csv(os.path.join(DATA, "mercados.csv"),
                    usecols=["market_id", "event_id", "pregunta", "categoria", "tags", "ganador_idx",
                             "outcome0", "outcome1", "volumen"])
    m = anadir_columnas(m[m["market_id"].isin(s["market_id"])].copy())
    d = s.merge(m, on="market_id", how="inner")
    d = d[d["ganador_idx"].notna()]
    filas = []
    for h in HORIZONTES:
        col = f"p_{h}h"
        x = d[d[col].notna()]
        for lado in (0, 1):
            p = x[col] if lado == 0 else 1 - x[col]
            filas.append(pd.DataFrame({
                "market_id": x["market_id"], "event_id": x["event_id"], "horizonte_h": h,
                "lado": lado, "resultado": x[f"outcome{lado}"],
                "precio": p, "gana": (x["ganador_idx"] == lado).astype(int),
                "volumen": x["volumen"], "cat": x["cat"], "es_mencion": x["mencion"].astype(bool),
            }))
    L = pd.concat(filas, ignore_index=True)
    if solo_yes:
        L = L[L["resultado"].astype(str).str.lower() == "yes"]
    L["coste"] = (L["precio"] + slip + fee).clip(upper=0.999)
    L["rend"] = L["gana"] / L["coste"] - 1  # rendimiento por euro apostado
    L["tramo_precio"] = pd.cut(L["precio"], TRAMOS_PRECIO, right=False)
    L["tramo_vol"] = pd.cut(L["volumen"], TRAMOS_VOL, labels=NOMBRES_VOL, right=False)
    return L


def resumen(g):
    n, k = len(g), int(g["gana"].sum())
    lo, hi = wilson(k, n)
    elo, ehi = ic_bootstrap_eventos(g)
    return pd.Series({
        "n": n, "n_eventos": g["event_id"].nunique(), "precio_medio": g["precio"].mean(),
        "tasa_acierto": k / n if n else np.nan, "acierto_ic_bajo": lo, "acierto_ic_alto": hi,
        "rend_medio_por_euro": g["rend"].mean(), "rend_ic_bajo": elo, "rend_ic_alto": ehi,
    })


def grafico(cal, vol, ruta):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    azul, gris, tinta, tinta2 = "#2a78d6", "#b5b4ae", "#0b0b0b", "#52514e"
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 5), facecolor="#fcfcfb")
    for a in (a1, a2):
        a.set_facecolor("#fcfcfb")
        for lado in ("top", "right"):
            a.spines[lado].set_visible(False)
        a.spines["left"].set_color(gris)
        a.spines["bottom"].set_color(gris)
        a.tick_params(colors=tinta2)

    c = cal[(cal["horizonte_h"] == 24) & (cal["n"] >= 30)]
    a1.plot([0, 1], [0, 1], color=gris, lw=1.5, ls="--", label="Calibración perfecta")
    a1.errorbar(c["precio_medio"], c["tasa_acierto"],
                yerr=[c["tasa_acierto"] - c["acierto_ic_bajo"], c["acierto_ic_alto"] - c["tasa_acierto"]],
                color=azul, lw=2, marker="o", ms=8, mec="#fcfcfb", mew=2, capsize=0, label="Mercado (24 h antes)")
    a1.set_xlabel("Precio pagado", color=tinta2)
    a1.set_ylabel("Frecuencia real de acierto", color=tinta2)
    a1.set_title("¿Los precios aciertan como probabilidades?", color=tinta, loc="left")
    a1.legend(frameon=False, labelcolor=tinta2)

    v = vol[(vol["horizonte_h"] == 24) & (vol["n"] >= 30)].reset_index(drop=True)
    y = v["rend_medio_por_euro"] * 100
    a2.axhline(0, color=gris, lw=1)
    a2.bar(range(len(v)), y, color=azul, width=0.6, edgecolor="#fcfcfb", linewidth=2)
    a2.errorbar(range(len(v)), y, yerr=[y - v["rend_ic_bajo"] * 100, v["rend_ic_alto"] * 100 - y],
                fmt="none", ecolor=tinta2, lw=1.5)
    a2.set_xticks(range(len(v)))
    a2.set_xticklabels([f"{t}\n(n={int(n)})" for t, n in zip(v["tramo_vol"], v["n"])], color=tinta2)
    a2.set_ylabel("Rendimiento medio por € apostado (%)", color=tinta2)
    a2.set_title(f"H2: comprar a {int(LONGSHOT_MIN*100)}-{int(LONGSHOT_MAX*100)} cts, por volumen del mercado",
                 color=tinta, loc="left")
    fig.tight_layout()
    fig.savefig(ruta, dpi=140)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slip", type=float, default=0.01, help="deslizamiento por compra (precio)")
    ap.add_argument("--fee", type=float, default=0.0, help="comisión por compra (precio)")
    ap.add_argument("--solo-yes", action="store_true", help="solo el lado llamado 'Yes'")
    args = ap.parse_args()

    L = tabla_larga(args.slip, args.fee, args.solo_yes)
    print(f"{len(L)} observaciones (mercado x horizonte x lado), {L['market_id'].nunique()} mercados")

    cal = L.groupby(["horizonte_h", "tramo_precio"], observed=True).apply(resumen, include_groups=False).reset_index()
    cal.to_csv(os.path.join(RESULTADOS, "calibracion.csv"), index=False)

    LS = L[(L["precio"] >= LONGSHOT_MIN) & (L["precio"] <= LONGSHOT_MAX)]
    vol = LS.groupby(["horizonte_h", "tramo_vol"], observed=True).apply(resumen, include_groups=False).reset_index()
    vol.to_csv(os.path.join(RESULTADOS, "h2_por_volumen.csv"), index=False)

    top = LS["cat"].value_counts().head(15).index
    cat = LS[LS["cat"].isin(top)].groupby(["horizonte_h", "cat"]).apply(resumen, include_groups=False).reset_index()
    cat.sort_values(["horizonte_h", "rend_medio_por_euro"], ascending=[True, False]) \
        .to_csv(os.path.join(RESULTADOS, "h2_por_categoria.csv"), index=False)

    men = L[L["es_mencion"]].groupby(["horizonte_h", "tramo_precio"], observed=True) \
        .apply(resumen, include_groups=False).reset_index()
    men.to_csv(os.path.join(RESULTADOS, "h2_menciones.csv"), index=False)

    grafico(cal, vol, os.path.join(RESULTADOS, "h2_grafico.png"))

    pd.set_option("display.width", 160)
    cols = ["tramo_vol", "n", "n_eventos", "precio_medio", "tasa_acierto", "rend_medio_por_euro", "rend_ic_bajo", "rend_ic_alto"]
    print("\nH2 a 24 h del cierre (longshots 1-15 cts):")
    print(vol[vol["horizonte_h"] == 24][cols].round(3).to_string(index=False))
    print("\nH2 a 24 h por categoría:")
    print(cat[cat["horizonte_h"] == 24].drop(columns="horizonte_h").round(3).to_string(index=False))
    print("\nCalibración a 24 h (todos los precios):")
    print(cal[cal["horizonte_h"] == 24].drop(columns="horizonte_h").round(3).to_string(index=False))
    print("\nMercados de menciones a 24 h:")
    print(men[men["horizonte_h"] == 24].drop(columns="horizonte_h").round(3).to_string(index=False))
    print("\nRegla de lectura: la H2 solo sobrevive en un grupo si rend_ic_bajo > 0 con n_eventos >= 30,"
          "\ny hay que repetirlo en datos nuevos (se han probado muchos grupos a la vez).")


if __name__ == "__main__":
    main()
