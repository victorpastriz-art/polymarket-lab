"""Paso 2: para una muestra de mercados resueltos, baja el historial de precios
(CLOB, solo lectura) y guarda el precio del resultado 0 a 168h, 24h, 6h y 1h del cierre.

Uso:
    python descargar_precios.py                                   # muestra estratificada por defecto
    python descargar_precios.py --por-categoria 800 --menciones 6000
    python descargar_precios.py --desde 2025-01-01

Muestra estratificada: hasta N mercados al azar POR CATEGORÍA (para que los millones de mercados
cripto de 5 minutos no se coman la muestra) + hasta M mercados de menciones.

Es reanudable: añade a data/snapshots.csv y salta los mercados ya hechos.
"""
import argparse
import os

import pandas as pd

from comun import CLOB, DATA, anadir_columnas, get_json

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
    ap.add_argument("--por-categoria", type=int, default=800)
    ap.add_argument("--menciones", type=int, default=6000)
    ap.add_argument("--max-categorias", type=int, default=30)
    ap.add_argument("--desde", default=None, help="AAAA-MM-DD (fecha de fin mínima)")
    ap.add_argument("--semilla", type=int, default=42)
    ap.add_argument("--salida", default="snapshots.csv", help="fichero dentro de data/")
    ap.add_argument("--excluir", default=None, help="CSV con columna market_id de mercados a no usar")
    args = ap.parse_args()

    m = pd.read_csv(os.path.join(DATA, "mercados.csv"),
                    usecols=["market_id", "pregunta", "categoria", "tags", "ganador_idx", "token0",
                             "fecha_fin", "fecha_cierre"])
    m = anadir_columnas(m[m["ganador_idx"].notna()].copy())
    if args.excluir and os.path.exists(args.excluir):
        usados = set(pd.read_csv(args.excluir, usecols=["market_id"])["market_id"].astype(str))
        m = m[~m["market_id"].astype(str).isin(usados)]
        print(f"Excluidos {len(usados)} mercados ya usados en el backtest anterior")
    if args.desde:
        fin = pd.to_datetime(m["fecha_fin"], utc=True, errors="coerce")
        m = m[fin >= pd.Timestamp(args.desde, tz="UTC")]

    menc = m[m["mencion"]]
    menc = menc.sample(min(args.menciones, len(menc)), random_state=args.semilla)
    top = m["cat"].value_counts().head(args.max_categorias).index
    partes = [g.sample(min(args.por_categoria, len(g)), random_state=args.semilla)
              for c, g in m[m["cat"].isin(top) & ~m["mencion"]].groupby("cat")]
    m = pd.concat([menc] + partes)
    print(m["cat"].value_counts().to_string())

    ruta = os.path.join(DATA, args.salida)
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
