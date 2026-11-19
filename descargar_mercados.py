"""Paso 1: descarga todos los eventos CERRADOS de Polymarket (Gamma API, solo lectura)
y los aplana a una fila por mercado binario en data/mercados.csv.

Uso:
    python descargar_mercados.py                    # desde 2023-01 hasta hoy
    python descargar_mercados.py --desde 2025-01    # solo desde enero 2025
    python descargar_mercados.py --rehacer          # vuelve a bajar meses ya guardados

Es reanudable: cada mes se guarda en data/meses/AAAA-MM.csv y se salta si ya existe
(salvo el mes en curso, que siempre se rehace).
"""
import argparse
import os
import re
from datetime import date, datetime, timedelta, timezone

import pandas as pd

from comun import DATA, GAMMA, get_json, lista_json

PAGINA = 100
RE_MENCION = re.compile(r"\b(?:say|says|mention|mentions)\b", re.I)


def meses(desde, hasta):
    a, m = desde
    while (a, m) <= hasta:
        yield a, m
        a, m = (a + 1, 1) if m == 12 else (a, m + 1)


def limites_mes(a, m):
    ini = datetime(a, m, 1, tzinfo=timezone.utc)
    fin = datetime(a + 1, 1, 1, tzinfo=timezone.utc) if m == 12 else datetime(a, m + 1, 1, tzinfo=timezone.utc)
    return ini.strftime("%Y-%m-%dT%H:%M:%SZ"), fin.strftime("%Y-%m-%dT%H:%M:%SZ")


MAX_OFFSET = 1900  # la API rechaza offsets grandes (~2.000): si una ventana tiene más eventos, se parte


def _fmt(t):
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def eventos_ventana(ini, fin):
    """Todos los eventos cerrados con fecha de fin en [ini, fin). Si no caben, parte la ventana en dos."""
    lotes, offset = [], 0
    while True:
        if offset > MAX_OFFSET:
            if fin - ini <= timedelta(minutes=30):
                print(f"  aviso: ventana {_fmt(ini)} con más de {offset} eventos, se queda incompleta")
                break
            medio = ini + (fin - ini) / 2
            return eventos_ventana(ini, medio) + eventos_ventana(medio, fin)
        params = {
            "closed": "true",
            "end_date_min": _fmt(ini),
            "end_date_max": _fmt(fin),
            "limit": PAGINA,
            "offset": offset,
            "order": "id",
            "ascending": "true",
        }
        lote = get_json(f"{GAMMA}/events", params)
        if not lote:
            break
        lotes.extend(lote)
        if len(lote) < PAGINA:
            break
        offset += PAGINA
    return lotes


def eventos_del_mes(a, m):
    ini, fin = (datetime.strptime(x, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) for x in limites_mes(a, m))
    vistos = set()
    dia = ini
    while dia < fin:
        sig = min(dia + timedelta(days=1), fin)
        for ev in eventos_ventana(dia, sig):
            if ev.get("id") not in vistos:  # los límites de ventana pueden solaparse
                vistos.add(ev.get("id"))
                yield ev
        dia = sig


def ganador(precios):
    """Índice del resultado ganador si el mercado está resuelto con claridad (precio final ≥0.99)."""
    try:
        p = [float(x) for x in precios]
    except (TypeError, ValueError):
        return None
    if len(p) != 2:
        return None
    if p[0] >= 0.99:
        return 0
    if p[1] >= 0.99:
        return 1
    return None  # anulado, 50-50 o sin resolver


def filas_de_evento(ev):
    tags = ev.get("tags") or []
    etiquetas = "|".join(str(t.get("label") or t.get("slug") or "") for t in tags if isinstance(t, dict))
    slugs_tags = " ".join(str(t.get("slug") or "") for t in tags if isinstance(t, dict)).lower()
    for mk in ev.get("markets") or []:
        outcomes = lista_json(mk.get("outcomes"))
        precios = lista_json(mk.get("outcomePrices"))
        tokens = lista_json(mk.get("clobTokenIds"))
        if len(outcomes) != 2 or len(tokens) != 2:
            continue
        pregunta = mk.get("question") or ""
        yield {
            "market_id": mk.get("id"),
            "condition_id": mk.get("conditionId"),
            "pregunta": pregunta,
            "slug": mk.get("slug"),
            "event_id": ev.get("id"),
            "event_slug": ev.get("slug"),
            "event_titulo": ev.get("title"),
            "categoria": mk.get("category") or ev.get("category") or "",
            "tags": etiquetas,
            "es_mencion": bool("mention" in slugs_tags or RE_MENCION.search(pregunta)),
            "outcome0": outcomes[0],
            "outcome1": outcomes[1],
            "token0": tokens[0],
            "token1": tokens[1],
            "ganador_idx": ganador(precios),
            "volumen": float(mk.get("volumeNum") or mk.get("volume") or 0),
            "liquidez": float(mk.get("liquidityNum") or mk.get("liquidity") or 0),
            "neg_risk": bool(mk.get("negRisk") or ev.get("negRisk")),
            "n_mercados_evento": len(ev.get("markets") or []),
            "fecha_inicio": mk.get("startDate") or ev.get("startDate"),
            "fecha_fin": mk.get("endDate") or ev.get("endDate"),
            "fecha_cierre": mk.get("closedTime") or ev.get("closedTime"),
        }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--desde", default="2023-01", help="AAAA-MM")
    ap.add_argument("--hasta", default=date.today().strftime("%Y-%m"), help="AAAA-MM")
    ap.add_argument("--rehacer", action="store_true")
    args = ap.parse_args()

    d = tuple(int(x) for x in args.desde.split("-"))
    h = tuple(int(x) for x in args.hasta.split("-"))
    hoy = (date.today().year, date.today().month)
    carpeta = os.path.join(DATA, "meses")
    os.makedirs(carpeta, exist_ok=True)

    for a, m in meses(d, h):
        ruta = os.path.join(carpeta, f"{a:04d}-{m:02d}.csv")
        if os.path.exists(ruta) and not args.rehacer and (a, m) != hoy:
            print(f"{a}-{m:02d}: ya descargado, salto")
            continue
        filas, n_ev = [], 0
        for ev in eventos_del_mes(a, m):
            n_ev += 1
            filas.extend(filas_de_evento(ev))
        pd.DataFrame(filas).to_csv(ruta, index=False)
        print(f"{a}-{m:02d}: {n_ev} eventos, {len(filas)} mercados binarios")

    partes = [pd.read_csv(os.path.join(carpeta, f)) for f in sorted(os.listdir(carpeta))
              if f.endswith(".csv") and os.path.getsize(os.path.join(carpeta, f)) > 1]
    partes = [p for p in partes if len(p)]
    if not partes:
        print("No hay datos. ¿La API respondió? Revisa los mensajes de arriba.")
        return
    todo = pd.concat(partes).drop_duplicates("market_id")
    todo.to_csv(os.path.join(DATA, "mercados.csv"), index=False)
    res = todo["ganador_idx"].notna()
    print(f"\nTotal: {len(todo)} mercados ({res.sum()} resueltos con claridad, "
          f"{int(todo['es_mencion'].sum())} de menciones) -> data/mercados.csv")


if __name__ == "__main__":
    main()
