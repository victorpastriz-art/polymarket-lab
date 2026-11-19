"""Utilidades compartidas: sesión HTTP con reintentos, límite de ritmo y rutas."""
import json
import os
import time

import requests

GAMMA = os.environ.get("GAMMA_URL", "https://gamma-api.polymarket.com")
CLOB = os.environ.get("CLOB_URL", "https://clob.polymarket.com")

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
RESULTADOS = os.path.join(BASE, "resultados")
os.makedirs(DATA, exist_ok=True)
os.makedirs(RESULTADOS, exist_ok=True)

_session = requests.Session()
_session.headers["User-Agent"] = "polymarket-lab/1.0 (investigacion academica, solo lectura)"
_ultimo = [0.0]


def get_json(url, params=None, pausa=0.15, intentos=6):
    """GET con pausa mínima entre llamadas y reintentos con espera creciente (429/5xx)."""
    espera = 2.0
    for i in range(intentos):
        dt = time.time() - _ultimo[0]
        if dt < pausa:
            time.sleep(pausa - dt)
        _ultimo[0] = time.time()
        try:
            r = _session.get(url, params=params, timeout=30)
        except requests.RequestException as e:
            print(f"  red: {e} (reintento {i + 1})")
            time.sleep(espera)
            espera *= 2
            continue
        if r.status_code == 200:
            return r.json()
        if r.status_code in (429, 500, 502, 503, 504):
            print(f"  HTTP {r.status_code} en {url} (reintento {i + 1}, espero {espera:.0f}s)")
            time.sleep(espera)
            espera *= 2
            continue
        # 4xx distinto de 429: no tiene sentido reintentar
        print(f"  HTTP {r.status_code} en {url}: {r.text[:200]}")
        return None
    return None


def lista_json(valor):
    """Gamma devuelve algunos campos como texto JSON ('[\"Yes\",\"No\"]')."""
    if valor is None:
        return []
    if isinstance(valor, list):
        return valor
    try:
        v = json.loads(valor)
        return v if isinstance(v, list) else []
    except (TypeError, ValueError):
        return []
