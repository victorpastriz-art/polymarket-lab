"""Paso 2: para una muestra de mercados resueltos, baja el historial de precios
(CLOB, solo lectura) y guarda el precio del resultado 0 a 168h, 24h, 6h y 1h del cierre.

Uso:
    python descargar_precios.py --muestra 20000          # todos los de menciones + aleatorios hasta 20.000
    python descargar_precios.py --muestra 0               # TODOS los resueltos (puede tardar muchas horas)
    python descargar_precios.py --desde 2025-01-01

Es reanudable: añade a data/snapshots.csv y salta los mercados ya hechos.
"""
import argparse
import os

import pandas as pd

from comun import CLOB, DATA, get_json

HORIZONTES_H = [168, 24, 6, 1]
MAX_ANTIGUEDAD_H = 6  # si el último precio conocido es más viejo que esto, no lo usamos


def momento_referencia(fila):
    """El primero entre la fecha de fin prevista y el cierre real (UTC, segundos)."""
    ts = []
    for c in ("fecha_fin", "fecha_cierre"):
        v = fila.get(c)
        if isinstance(v, str) and v:
            t = pd.to_datetime(v, utc=True, errors="coerce")
            if pd.notna(t):
                ts.append(int(t.timestamp()))
    return min(ts) if ts else None


def snapshots(historia, t_ref):
    pts = sorted((int(p["t"]), float(p["p"])) for p in historia if "t" in p and "p" in p)
    out = {}
    for h in HORIZONTES_H:
        objetivo = t_ref - h * 3600
        previos = [p for p in pts if p[0] <= objetivo]
        if previos and objetivo - previos[-1][0] <= MAX_ANTIGUEDAD_H * 3600:
            out[f"p_{h}h"] = previos[-1][1]
        else:
            out[f"p_{h}h"] = None
    out["n_puntos"] = len(pts)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--muestra", type=int, default=20000, help="0 = todos")
    ap.add_argument("--desde", default=None, help="AAAA-MM-DD (fecha de fin mínima)")
    ap.add_argument("--semilla", type=int, default=42)
    args = ap.parse_args()

    m = pd.read_csv(os.path.join(DATA, "mercados.csv"))
    m = m[m["ganador_idx"].notna()].copy()
    if args.desde:
        fin = pd.to_datetime(m["fecha_fin"], utc=True, errors="coerce")
        m = m[fin >= pd.Timestamp(args.desde, tz="UTC")]

    if args.muestra and len(m) > args.muestra:
        menc = m[m["es_mencion"].astype(bool)]
        resto = m[~m["es_mencion"].astype(bool)]
        n_resto = max(0, args.muestra - len(menc))
        m = pd.concat([menc, resto.sample(min(n_resto, len(resto)), random_state=args.semilla)])

    ruta = os.path.join(DATA, "snapshots.csv")
    hechos = set()
    if os.path.exists(ruta):
        hechos = set(pd.read_csv(ruta, usecols=["market_id"])["market_id"].astype(str))
    pendientes = m[~m["market_id"].astype(str).isin(hechos)]
    print(f"{len(m)} mercados en la muestra, {len(pendientes)} pendientes")

    buffer = []
    for i, fila in enumerate(pendientes.to_dict("records"), 1):
        t_ref = momento_referencia(fila)
        if t_ref is None:
            continue
        datos = get_json(f"{CLOB}/prices-history", {
            "market": str(fila["token0"]),
            "startTs": t_ref - 8 * 24 * 3600,
            "endTs": t_ref,
            "fidelity": 60,
        })
        historia = (datos or {}).get("history", [])
        buffer.append({"market_id": fila["market_id"], "t_ref": t_ref, **snapshots(historia, t_ref)})
        if len(buffer) >= 200 or i == len(pendientes):
            pd.DataFrame(buffer).to_csv(ruta, mode="a", header=not os.path.exists(ruta), index=False)
            buffer = []
            print(f"  {i}/{len(pendientes)} guardados")
    if buffer:
        pd.DataFrame(buffer).to_csv(ruta, mode="a", header=not os.path.exists(ruta), index=False)
    print("Listo -> data/snapshots.csv")


if __name__ == "__main__":
    main()
