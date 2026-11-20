"""Paper trading de la H4 (reglas en paper/REGLAS.md). Solo lee datos públicos; no hay órdenes reales.

Cada ejecución:
  1) resuelve las operaciones abiertas cuyo mercado ya cerró,
  2) busca entradas nuevas (mercados que cierran en 21-24 h, favorito con ask real entre 0,50 y 0,85),
  3) actualiza paper/resumen.md y, si hay credenciales, avisa por Telegram.

Uso:  python paper_h4.py            (--sin-entradas para solo resolver y resumir)
Telegram (opcional): variables de entorno TELEGRAM_TOKEN y TELEGRAM_CHAT_ID.
"""
import argparse
import hashlib
import os
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import requests

from comun import BASE, CLOB, GAMMA, get_json, lista_json

PAPER = os.path.join(BASE, "paper")
OPS = os.path.join(PAPER, "operaciones.csv")
DESC = os.path.join(PAPER, "descartes.csv")
RESUMEN = os.path.join(PAPER, "resumen.md")
os.makedirs(PAPER, exist_ok=True)

PROF_MIN_USD = 20.0
APUESTA = 10.0
# Carteras (ver paper/REGLAS.md). "lado": favorito = el más caro, barato = el más barato, azar = uno al azar fijo.
ESTRATEGIAS = {
    "H4-24h": {"ventana": (21, 24), "lado": "favorito", "pmin": 0.50, "pmax": 0.85, "max_ops": 250},
    "H4-4h": {"ventana": (2, 5), "lado": "favorito", "pmin": 0.50, "pmax": 0.85, "max_ops": 250},
    "H2-control": {"ventana": (21, 24), "lado": "barato", "pmin": 0.01, "pmax": 0.15, "max_ops": 250},
    "Azar": {"ventana": (21, 24), "lado": "azar", "pmin": 0.02, "pmax": 0.98, "max_ops": 250},
}
EVALUADAS = ["H4-24h", "H4-4h"]
MIN_OPS_VEREDICTO, MIN_DIAS_VEREDICTO = 200, 30
FMT = "%Y-%m-%dT%H:%M:%SZ"


def ahora():
    return datetime.now(timezone.utc)


# ---------- 1. escaneo ----------
def mercados_ventana(ini, fin, profundidad=0):
    """Mercados abiertos con fecha de fin en [ini, fin). Parte la ventana si la paginación no da más de sí."""
    out, offset = [], 0
    while True:
        if offset > 1900:
            if profundidad > 8:
                break
            medio = ini + (fin - ini) / 2
            return mercados_ventana(ini, medio, profundidad + 1) + mercados_ventana(medio, fin, profundidad + 1)
        lote = get_json(f"{GAMMA}/markets", {
            "active": "true", "closed": "false",
            "end_date_min": ini.strftime(FMT), "end_date_max": fin.strftime(FMT),
            "limit": 100, "offset": offset, "order": "id", "ascending": "true",
        })
        if not lote:
            break
        out.extend(lote)
        if len(lote) < 100:
            break
        offset += 100
    return out


def mejor_ask(token):
    libro = get_json(f"{CLOB}/book", {"token_id": token}, pausa=0.08)
    if not libro:
        return None, 0.0
    asks = [(float(a["price"]), float(a["size"])) for a in libro.get("asks", []) if "price" in a]
    if not asks:
        return None, 0.0
    p = min(x[0] for x in asks)
    tam = sum(s for q, s in asks if q == p)
    return p, p * tam


def info_evento(mk):
    evs = mk.get("events") or []
    ev = evs[0] if evs and isinstance(evs[0], dict) else {}
    tags = ev.get("tags") or mk.get("tags") or []
    cat = mk.get("category") or ev.get("category") or \
        next((t.get("label") for t in tags if isinstance(t, dict) and t.get("label")), "") or "sin categoría"
    return str(ev.get("id") or mk.get("eventId") or f"m{mk.get('id')}"), cat


def elegir_lado(mid, p, regla):
    if regla["lado"] == "favorito":
        return 0 if p[0] >= p[1] else 1
    if regla["lado"] == "barato":
        return 0 if p[0] < p[1] else 1
    return int(hashlib.md5(f"azar-{mid}".encode()).hexdigest(), 16) % 2


def buscar_entradas(ops):
    t = ahora()
    nuevas, descartes, n_brutos = [], [], {}
    cache = {}
    for nombre, regla in ESTRATEGIAS.items():
        ya = ops[ops["estrategia"] == nombre] if not ops.empty else ops
        ya_m = set(ya["market_id"]) if not ya.empty else set()
        ya_e = set(ya["event_id"]) if not ya.empty else set()
        v = regla["ventana"]
        if v not in cache:
            cache[v] = mercados_ventana(t + timedelta(hours=v[0]), t + timedelta(hours=v[1]))
        brutos = cache[v]
        n_brutos[nombre] = len(brutos)
        cand = []
        for mk in brutos:
            mid = str(mk.get("id"))
            if mid in ya_m:
                continue
            outs, precios, toks = (lista_json(mk.get(k)) for k in ("outcomes", "outcomePrices", "clobTokenIds"))
            if len(outs) != 2 or len(toks) != 2 or len(precios) != 2:
                continue
            if mk.get("acceptingOrders") is False or mk.get("enableOrderBook") is False:
                continue
            try:
                p = [float(x) for x in precios]
            except ValueError:
                continue
            lado = elegir_lado(mid, p, regla)
            if not (regla["pmin"] - 0.05 <= p[lado] <= regla["pmax"] + 0.05):  # filtro grueso antes del libro
                continue
            ev, cat = info_evento(mk)
            if ev in ya_e:  # 1 operación por evento y cartera, también entre escaneos
                continue
            cand.append({
                "estrategia": nombre, "market_id": mid, "event_id": ev, "categoria": cat,
                "pregunta": mk.get("question"), "slug": mk.get("slug"), "lado": outs[lado], "token": toks[lado],
                "precio_gamma": p[lado], "volumen": float(mk.get("volumeNum") or mk.get("volume") or 0),
                "fecha_fin": mk.get("endDate"),
            })
        c = pd.DataFrame(cand)
        if c.empty:
            continue
        c = c.sort_values("volumen", ascending=False).drop_duplicates("event_id")
        hechas = 0
        for fila in c.to_dict("records"):
            if hechas >= regla["max_ops"]:
                break
            ask, prof = mejor_ask(fila["token"])
            motivo = None
            if ask is None:
                motivo = "sin asks"
            elif not (regla["pmin"] <= ask <= regla["pmax"]):
                motivo = f"ask {ask:.3f} fuera de rango"
            elif prof < PROF_MIN_USD:
                motivo = f"profundidad {prof:.1f}$ < {PROF_MIN_USD:.0f}$"
            reg = {**fila, "fecha_escaneo": t.strftime(FMT), "ask": ask, "profundidad_usd": round(prof, 2)}
            if motivo:
                descartes.append({**reg, "motivo": motivo})
            else:
                hechas += 1
                nuevas.append({**reg, "apuesta": APUESTA, "estado": "abierta", "ganancia": np.nan,
                               "fecha_resolucion": ""})
    return nuevas, descartes, n_brutos


# ---------- 2. resolución ----------
def resolver(ops):
    cambios = []
    t = ahora()
    for i, op in ops[ops["estado"] == "abierta"].iterrows():
        fin = pd.to_datetime(op["fecha_fin"], utc=True, errors="coerce")
        if pd.notna(fin) and fin > t:
            continue
        mk = get_json(f"{GAMMA}/markets/{op['market_id']}")
        if not mk or not mk.get("closed"):
            continue
        outs, precios = lista_json(mk.get("outcomes")), lista_json(mk.get("outcomePrices"))
        try:
            p = dict(zip(outs, [float(x) for x in precios]))
        except ValueError:
            continue
        pl = p.get(op["lado"])
        if pl is None:
            continue
        if pl >= 0.99:
            ops.at[i, "estado"], ops.at[i, "ganancia"] = "ganada", round(APUESTA / op["ask"] - APUESTA, 4)
        elif pl <= 0.01:
            ops.at[i, "estado"], ops.at[i, "ganancia"] = "perdida", -APUESTA
        else:
            ops.at[i, "estado"], ops.at[i, "ganancia"] = "anulada", 0.0
        ops.at[i, "fecha_resolucion"] = t.strftime(FMT)
        cambios.append(ops.loc[i])
    return cambios


# ---------- 3. resumen ----------
def ic_evento(r, n_boot=2000):
    g = r.groupby("event_id").agg(g=("ganancia", "sum"), a=("apuesta", "sum"))
    if len(g) < 2:
        return np.nan, np.nan
    rng = np.random.default_rng(0)
    idx = rng.integers(0, len(g), (n_boot, len(g)))
    v = g["g"].to_numpy()[idx].sum(1) / g["a"].to_numpy()[idx].sum(1)
    return np.percentile(v, 2.5), np.percentile(v, 97.5)


def bloque(r_all, nombre):
    ops = r_all[r_all["estrategia"] == nombre]
    r = ops[ops["estado"].isin(["ganada", "perdida"])]
    n = len(r)
    abiertas = int((ops["estado"] == "abierta").sum())
    lin = [f"## {nombre}", "", f"- Operaciones: **{len(ops)}** ({n} resueltas, {abiertas} abiertas, "
           f"{int((ops['estado'] == 'anulada').sum())} anuladas)"]
    corto = f"{nombre}: {n} resueltas"
    if n:
        roi = r["ganancia"].sum() / r["apuesta"].sum()
        lo, hi = ic_evento(r)
        acierto = (r["estado"] == "ganada").mean()
        lin += [f"- Aciertos: **{acierto:.1%}** (precio medio pagado {r['ask'].mean():.3f})",
                f"- P&L ficticio: **{r['ganancia'].sum():+.2f} $** sobre {r['apuesta'].sum():.0f} $",
                f"- Rendimiento por $: **{roi:+.2%}** (IC 95% por evento: {lo:+.2%} a {hi:+.2%})"]
        corto = f"{nombre}: {n} resueltas, {roi:+.1%} (IC {lo:+.1%} a {hi:+.1%})"
        if nombre in EVALUADAS:
            dias = (ahora() - pd.to_datetime(ops["fecha_escaneo"], utc=True).min()).days
            if n >= MIN_OPS_VEREDICTO and dias >= MIN_DIAS_VEREDICTO:
                if roi > 0 and lo > 0:
                    v = "ÉXITO según las reglas."
                elif hi < 0 or (n >= 400 and roi <= 0):
                    v = "FRACASO según las reglas."
                else:
                    v = "No concluyente todavía: se sigue recogiendo."
            else:
                v = f"En curso ({n}/{MIN_OPS_VEREDICTO} resueltas, {dias}/{MIN_DIAS_VEREDICTO} días)."
            lin.append(f"- **Veredicto:** {v}")
    return lin + [""], corto


def resumen(ops):
    lineas = ["# Paper trading — carteras ficticias en Polymarket", "",
              f"_Actualizado: {ahora().strftime('%Y-%m-%d %H:%M')} UTC · reglas en [REGLAS.md](REGLAS.md)_", ""]
    if ops.empty:
        return "\n".join(lineas + ["Aún no hay operaciones."]), None
    cortos = []
    for nombre in ESTRATEGIAS:
        b, c = bloque(ops, nombre)
        lineas += b
        cortos.append(c)
    return "\n".join(lineas) + "\n", "\n".join(cortos)


def telegram(texto):
    tok, chat = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not tok or not chat or not texto:
        return
    try:
        requests.post(f"https://api.telegram.org/bot{tok}/sendMessage",
                      data={"chat_id": chat, "text": texto[:4000]}, timeout=20)
    except requests.RequestException as e:
        print(f"Telegram: {e}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sin-entradas", action="store_true")
    args = ap.parse_args()

    ops = pd.read_csv(OPS, dtype={"market_id": str, "event_id": str, "estado": str, "fecha_resolucion": str,
                                  "lado": str}, keep_default_na=False, na_values={"ganancia": [""]}) \
        if os.path.exists(OPS) else pd.DataFrame()
    if not ops.empty:
        ops["ganancia"] = pd.to_numeric(ops["ganancia"], errors="coerce").astype(float)
        if "estrategia" not in ops.columns:
            ops.insert(0, "estrategia", "H4-24h")  # las operaciones anteriores al 20-nov eran todas H4-24h
        ops["estrategia"] = ops["estrategia"].replace("", "H4-24h")
    cambios = resolver(ops) if not ops.empty else []
    print(f"Resueltas en esta pasada: {len(cambios)}")

    nuevas, descartes, n_brutos = ([], [], {}) if args.sin_entradas else buscar_entradas(ops)
    por = pd.Series([o["estrategia"] for o in nuevas]).value_counts().to_dict() if nuevas else {}
    print(f"Mercados por ventana: {n_brutos} · entradas nuevas: {por} · descartes: {len(descartes)}")
    if nuevas:
        ops = pd.concat([ops, pd.DataFrame(nuevas)], ignore_index=True)
    if descartes:
        pd.DataFrame(descartes).to_csv(DESC, mode="a", header=not os.path.exists(DESC), index=False)
    if not ops.empty:
        ops.to_csv(OPS, index=False)

    texto, corto = resumen(ops)
    with open(RESUMEN, "w", encoding="utf-8") as f:
        f.write(texto)
    print(texto)

    msg = []
    if nuevas:
        msg.append(f"📥 {len(nuevas)} entradas nuevas (paper): " + ", ".join(f"{k} {v}" for k, v in por.items()))
    if cambios:
        g = sum(1 for c in cambios if c["estado"] == "ganada")
        pnl = sum(float(c["ganancia"]) for c in cambios if c["estado"] in ("ganada", "perdida"))
        msg.append(f"✅ {len(cambios)} resueltas: {g} ganadas, P&L {pnl:+.2f} $")
    if msg and corto:
        msg.append(corto)
    telegram("\n".join(msg))


if __name__ == "__main__":
    main()
