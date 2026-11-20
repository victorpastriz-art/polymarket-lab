"""Convierte paper/operaciones.csv en paper/panel.json ({rows, meta}) para el panel de la cartera ficticia."""
import json
import math
import os

import pandas as pd

from comun import BASE

OPS = os.path.join(BASE, "paper", "operaciones.csv")
SALIDA = os.path.join(BASE, "paper", "panel.json")
COLS = ["estrategia", "market_id", "event_id", "pregunta", "lado", "ask", "apuesta", "estado", "ganancia",
        "fecha_escaneo", "fecha_fin", "fecha_resolucion", "categoria", "slug", "volumen", "profundidad_usd"]


def limpio(v):
    if isinstance(v, float) and math.isnan(v):
        return None
    return v


def main():
    o = pd.read_csv(OPS, dtype={"market_id": str, "event_id": str}, keep_default_na=False,
                    na_values={"ganancia": [""], "ask": [""], "volumen": [""], "profundidad_usd": [""]})
    if "estrategia" not in o.columns:
        o.insert(0, "estrategia", "H4-24h")
    o["estrategia"] = o["estrategia"].replace("", "H4-24h")
    for c in ("ask", "apuesta", "ganancia", "volumen", "profundidad_usd"):
        o[c] = pd.to_numeric(o[c], errors="coerce")
    rows = [{c: limpio(r.get(c)) for c in COLS} for r in o.to_dict("records")]
    meta = [
        {"label": "Origen", "value": "paper/operaciones.csv del repositorio victorpastriz-art/polymarket-lab"},
        {"label": "Generado", "value": pd.Timestamp.now("UTC").strftime("%Y-%m-%d %H:%M UTC")},
        {"label": "Reglas", "value": "paper/REGLAS.md (H4: favorito con ask real 0,50-0,85 a 21-24 h del cierre, 10 $ ficticios)"},
    ]
    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump({"rows": rows, "meta": meta}, f, ensure_ascii=False)
    print(f"{len(rows)} operaciones -> {SALIDA}")


if __name__ == "__main__":
    main()
