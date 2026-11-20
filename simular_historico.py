"""Histórico: cómo habrían ido 1.000 $ ficticios por cartera, mes a mes, con las mismas reglas del paper trading.

Usa dos muestras de mercados ya resueltos:
  - "descubrimiento": la del backtest del que salió la H4 (optimista para la H4, porque la regla se eligió con ella)
  - "confirmacion": una muestra nueva e independiente (la que cuenta)

Carteras (como en paper/REGLAS.md; coste = precio + 1 céntimo; 10 $ por apuesta; 1 por evento y cartera):
  H4-24h      favorito a 0,50-0,85, 24 h antes del cierre
  H4-4h       favorito a 0,50-0,85, aproximado con el precio 6 h antes (el histórico no tiene 2-5 h)
  H2-control  lado más barato a 0,01-0,15, 24 h antes
  Azar        un lado al azar (el mismo sorteo que el paper trading) a 0,02-0,98, 24 h antes

Uso: python simular_historico.py --muestra descubrimiento=RUTA.csv --muestra confirmacion=RUTA.csv
Salidas: resultados/historico_mensual.csv, resultados/historico.md, resultados/historico_panel.json
"""
import argparse
import hashlib
import json
import os

import numpy as np
import pandas as pd

from comun import DATA, RESULTADOS

CAPITAL, APUESTA, SLIP = 1000.0, 10.0, 0.01
CARTERAS = {
    "H4-24h": ("p_24h", "favorito", 0.50, 0.85),
    "H4-4h": ("p_6h", "favorito", 0.50, 0.85),
    "H2-control": ("p_24h", "barato", 0.01, 0.15),
    "Azar": ("p_24h", "azar", 0.02, 0.98),
}


def lado_azar(mid):
    return int(hashlib.md5(f"azar-{mid}".encode()).hexdigest(), 16) % 2


def apuestas(d, nombre):
    col, regla, pmin, pmax = CARTERAS[nombre]
    x = d[d[col].notna()].copy()
    p0 = x[col].astype(float)
    if regla == "favorito":
        x["lado"] = np.where(p0 >= 0.5, 0, 1)
    elif regla == "barato":
        x["lado"] = np.where(p0 < 0.5, 0, 1)
    else:
        x["lado"] = x["market_id"].astype(str).map(lado_azar)
    x["precio"] = np.where(x["lado"] == 0, p0, 1 - p0)
    x = x[(x["precio"] >= pmin) & (x["precio"] <= pmax)]
    x = x.sort_values("volumen", ascending=False).drop_duplicates("event_id")
    x["coste"] = (x["precio"] + SLIP).clip(upper=0.999)
    x["gana"] = (x["ganador_idx"] == x["lado"]).astype(int)
    x["ganancia"] = np.where(x["gana"] == 1, APUESTA / x["coste"] - APUESTA, -APUESTA)
    x["fecha"] = pd.to_datetime(x["t_ref"], unit="s", utc=True)
    x["mes"] = x["fecha"].dt.strftime("%Y-%m")
    return x.sort_values("fecha")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--muestra", action="append", required=True, help="nombre=ruta de snapshots")
    args = ap.parse_args()

    m = pd.read_csv(os.path.join(DATA, "mercados.csv"), usecols=["market_id", "event_id", "ganador_idx", "volumen"])
    filas, md = [], ["# Histórico: 1.000 $ ficticios por cartera, mes a mes", "",
                     "Mismas reglas que el paper trading (coste = precio + 1 céntimo, 10 $ por apuesta, 1 por evento). "
                     "Son **muestras** de mercados, no todos los que había: el número de apuestas por mes es menor que el "
                     "que habría tenido el bot de verdad, y el rendimiento por dólar es lo que hay que mirar.", ""]
    for arg in args.muestra:
        nombre_m, ruta = arg.split("=", 1)
        if not os.path.exists(ruta):
            print(f"No existe {ruta}, salto la muestra {nombre_m}")
            continue
        s = pd.read_csv(ruta)
        d = s.merge(m[m["market_id"].isin(s["market_id"])], on="market_id")
        d = d[d["ganador_idx"].notna()]
        md += [f"## Muestra: {nombre_m} ({d['market_id'].nunique()} mercados)", ""]
        resumen = []
        for c in CARTERAS:
            x = apuestas(d, c)
            if x.empty:
                continue
            g = x.groupby("mes").agg(apuestas=("ganancia", "size"), ganancia=("ganancia", "sum"),
                                     aciertos=("gana", "mean")).reset_index()
            g["saldo"] = CAPITAL + g["ganancia"].cumsum()
            g["rendimiento"] = g["ganancia"] / (g["apuestas"] * APUESTA)
            for r in g.to_dict("records"):
                filas.append({"muestra": nombre_m, "estrategia": c, **r})
            total = x["ganancia"].sum()
            resumen.append({"cartera": c, "apuestas": len(x), "aciertos": f"{x['gana'].mean():.1%}",
                            "ganancia": f"{total:+.0f} $", "saldo_final": f"{CAPITAL + total:,.0f} $",
                            "por_dolar": f"{total / (len(x) * APUESTA):+.1%}",
                            "meses_en_positivo": f"{int((g['ganancia'] > 0).sum())}/{len(g)}",
                            "peor_mes": f"{g['ganancia'].min():+.0f} $"})
        md += [pd.DataFrame(resumen).to_markdown(index=False), ""]

    H = pd.DataFrame(filas)
    H.to_csv(os.path.join(RESULTADOS, "historico_mensual.csv"), index=False)
    with open(os.path.join(RESULTADOS, "historico.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    rows = [{k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()} for r in H.to_dict("records")]
    meta = [{"label": "Código", "value": "simular_historico.py del repositorio victorpastriz-art/polymarket-lab"},
            {"label": "Muestras", "value": "descubrimiento = backtest de la ejecución 44624425236; "
                                          "confirmacion = muestra nueva sin mercados repetidos"}]
    with open(os.path.join(RESULTADOS, "historico_panel.json"), "w", encoding="utf-8") as f:
        json.dump({"rows": rows, "meta": meta}, f, ensure_ascii=False)
    print("\n".join(md))


if __name__ == "__main__":
    main()
