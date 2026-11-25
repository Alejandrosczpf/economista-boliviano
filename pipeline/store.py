"""Almacén de observaciones en CSV (formato largo).

Un archivo de texto en el repositorio: git guarda cada versión ("vintage"),
así siempre se puede ver qué sabía el sistema en una fecha dada.
Columnas: serie, fecha, valor, fuente, url, nota, capturado
"""
from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OBS = os.path.join(RAIZ, "data", "observaciones.csv")
CUARENTENA = os.path.join(RAIZ, "data", "cuarentena.csv")
CONTRATOS = os.path.join(RAIZ, "config", "series.json")
CAMPOS = ["serie", "fecha", "valor", "fuente", "url", "nota", "capturado"]


@dataclass
class Obs:
    serie: str
    fecha: str  # AAAA-MM-DD
    valor: float
    fuente: str = ""
    url: str = ""
    nota: str = ""
    capturado: str = field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"))

    @property
    def dia(self) -> date:
        return date.fromisoformat(self.fecha)


def cargar_contratos(ruta: str = CONTRATOS) -> dict:
    with open(ruta, encoding="utf-8") as f:
        return {s["id"]: s for s in json.load(f)["series"]}


def leer(ruta: str = OBS) -> list[Obs]:
    if not os.path.exists(ruta):
        return []
    with open(ruta, encoding="utf-8", newline="") as f:
        filas = list(csv.DictReader(f))
    out = []
    for r in filas:
        try:
            out.append(Obs(r["serie"], r["fecha"], float(r["valor"]), r.get("fuente", ""),
                           r.get("url", ""), r.get("nota", ""), r.get("capturado", "")))
        except (ValueError, KeyError):
            continue
    return out


def escribir(obs: list[Obs], ruta: str = OBS) -> None:
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    obs = sorted(obs, key=lambda o: (o.serie, o.fecha))
    with open(ruta, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        w.writeheader()
        for o in obs:
            d = asdict(o)
            d["valor"] = repr(o.valor) if isinstance(o.valor, float) else o.valor
            w.writerow(d)


def fusionar(existentes: list[Obs], nuevas: list[Obs]) -> tuple[list[Obs], int]:
    """Agrega o corrige observaciones. Clave = (serie, fecha).
    Si el valor cambió, el nuevo reemplaza al viejo (la versión vieja queda en git)."""
    idx = {(o.serie, o.fecha): o for o in existentes}
    cambios = 0
    for n in nuevas:
        k = (n.serie, n.fecha)
        viejo = idx.get(k)
        if viejo is None or abs(viejo.valor - n.valor) > 1e-9:
            idx[k] = n
            cambios += 1
    return list(idx.values()), cambios


def por_serie(obs: list[Obs]) -> dict[str, list[Obs]]:
    d: dict[str, list[Obs]] = {}
    for o in obs:
        d.setdefault(o.serie, []).append(o)
    for v in d.values():
        v.sort(key=lambda o: o.fecha)
    return d
