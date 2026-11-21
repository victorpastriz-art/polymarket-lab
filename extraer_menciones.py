"""Extrae los mercados de menciones resueltos ("Will X say 'Y' during Z?") de data/mercados.csv
y los separa en orador, palabra y evento -> data/menciones.csv

Uso: python extraer_menciones.py
"""
import os
import re

import pandas as pd

from comun import DATA, anadir_columnas

COMILLAS = "\"'“”‘’«»"
RE_CON_COMILLAS = re.compile(
    r"^\s*(?:will\s+)?(?P<orador>.+?)\s+(?:say|says|mention|mentions)\s+[" + COMILLAS + r"](?P<palabra>.+?)[" + COMILLAS + r"]"
    r"(?P<resto>.*)$", re.I)
RE_SIN_COMILLAS = re.compile(
    r"^\s*will\s+(?P<orador>.+?)\s+(?:say|says|mention|mentions)\s+(?P<palabra>.+?)"
    r"(?P<resto>\s+(?:during|at|in|on|by|before|this|at least|\d+\+? times).*|\?)\s*$", re.I)


ALIAS = {"donald trump": "trump", "president trump": "trump", "donald j. trump": "trump",
         "karoline leavitt": "leavitt", "jerome powell": "powell", "jay powell": "powell",
         "keir starmer": "starmer", "jd vance": "vance", "j.d. vance": "vance", "j. d. vance": "vance",
         "kamala harris": "kamala", "bernie sanders": "bernie", "joe biden": "biden", "kevin warsh": "warsh",
         "zohran mamdani": "mamdani", "elon musk": "elon", "elon": "elon"}
RE_CITAS = re.compile(r"[" + COMILLAS + r"]([^" + COMILLAS + r"]{1,60})[" + COMILLAS + r"]")


def normaliza(t):
    t = re.sub(r"\s+", " ", str(t)).strip().strip("?").strip()
    return t.lower()


def parsear(pregunta):
    for rx in (RE_CON_COMILLAS, RE_SIN_COMILLAS):
        m = rx.match(str(pregunta))
        if m:
            orador = normaliza(m.group("orador"))
            orador = re.sub(r"^(?:president|press secretary|chair(?:man)?|fed chair|secretary)\s+", "", orador)
            orador = ALIAS.get(orador, orador)
            citas = sorted({normaliza(c) for c in RE_CITAS.findall(str(pregunta))})
            palabra = " / ".join(citas) if citas else normaliza(m.group("palabra"))
            return orador, palabra, m.group("resto").strip(" ?")
    return None, None, None


def main():
    m = pd.read_csv(os.path.join(DATA, "mercados.csv"),
                    usecols=["market_id", "event_id", "pregunta", "event_titulo", "categoria", "tags", "ganador_idx",
                             "outcome0", "outcome1", "volumen", "fecha_fin", "fecha_cierre"])
    m = anadir_columnas(m[m["ganador_idx"].notna()].copy())
    m = m[m["mencion"]]
    print(f"Mercados de menciones resueltos: {len(m)}")

    partes = m["pregunta"].map(parsear)
    m["orador"] = partes.map(lambda p: p[0])
    m["palabra"] = partes.map(lambda p: p[1])
    m["contexto"] = partes.map(lambda p: p[2])
    m["yes_idx"] = (m["outcome1"].astype(str).str.lower() == "yes").astype(int)
    ok_yes = m["outcome0"].astype(str).str.lower().isin(["yes", "no"])
    ok = m["orador"].notna() & ok_yes
    print(f"Con orador y palabra reconocidos: {ok.sum()} ({ok.mean():.0%})")
    print("\nEjemplos NO reconocidos:")
    print("\n".join("  " + q for q in m.loc[~ok, "pregunta"].head(20)))
    print("\nEjemplos reconocidos:")
    for r in m[ok].sample(min(20, ok.sum()), random_state=1).itertuples():
        print(f"  [{r.orador}] [{r.palabra}] <- {r.pregunta}")

    d = m[ok].copy()
    d["gana_yes"] = (d["ganador_idx"] == d["yes_idx"]).astype(int)
    print("\nOradores con más mercados:")
    print(d["orador"].value_counts().head(25).to_string())
    print(f"\nTasa global de YES: {d['gana_yes'].mean():.1%}")
    cols = ["market_id", "event_id", "orador", "palabra", "contexto", "event_titulo", "pregunta", "yes_idx",
            "gana_yes", "volumen", "fecha_fin", "fecha_cierre"]
    d[cols].to_csv(os.path.join(DATA, "menciones.csv"), index=False)
    print(f"\n{len(d)} mercados -> data/menciones.csv")


if __name__ == "__main__":
    main()
