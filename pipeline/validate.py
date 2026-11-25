"""Contratos de datos y cuarentena.

Regla: ningún dato entra al cálculo si rompe su contrato.
- fuera del rango físicamente posible (min/max)
- salto increíble frente al dato anterior (max_salto_pct o max_salto_pts)
- serie desconocida o fecha inválida / futura
Los rechazados se guardan en data/cuarentena.csv con el motivo, para revisión humana.
"""
from __future__ import annotations

import csv
import os
from datetime import date
from math import sqrt

from pipeline.store import CUARENTENA, Obs


def revisar(nuevas: list[Obs], previas: dict[str, list[Obs]], contratos: dict,
            hoy: date | None = None) -> tuple[list[Obs], list[tuple[Obs, str]]]:
    hoy = hoy or date.today()
    aceptadas: list[Obs] = []
    rechazadas: list[tuple[Obs, str]] = []
    # se procesan en orden cronológico para comparar cada dato con el anterior aceptado
    ultimo: dict[str, Obs] = {s: v[-1] for s, v in previas.items() if v}
    historia = {s: list(v) for s, v in previas.items()}
    for o in sorted(nuevas, key=lambda x: (x.serie, x.fecha)):
        motivo = _motivo(o, contratos, historia.get(o.serie, []), hoy)
        if motivo:
            rechazadas.append((o, motivo))
        else:
            aceptadas.append(o)
            historia.setdefault(o.serie, []).append(o)
            historia[o.serie].sort(key=lambda x: x.fecha)
            ultimo[o.serie] = historia[o.serie][-1]
    return aceptadas, rechazadas


def _motivo(o: Obs, contratos: dict, historia: list[Obs], hoy: date) -> str | None:
    c = contratos.get(o.serie)
    if c is None:
        return f"serie desconocida '{o.serie}'"
    try:
        d = o.dia
    except ValueError:
        return f"fecha inválida '{o.fecha}'"
    if d > hoy:
        return f"fecha futura {o.fecha}"
    if o.valor != o.valor:  # NaN
        return "valor vacío (NaN)"
    if c.get("min") is not None and o.valor < c["min"]:
        return f"valor {o.valor} menor al mínimo posible {c['min']}"
    if c.get("max") is not None and o.valor > c["max"]:
        return f"valor {o.valor} mayor al máximo posible {c['max']}"
    # dato anterior a esta fecha (ignora el mismo día: sería una corrección)
    previos = [h for h in historia if h.fecha < o.fecha]
    if previos and o.fecha not in c.get("quiebres", []):
        p = previos[-1]
        # El salto permitido crece con el tiempo transcurrido (como un paseo aleatorio: raíz del tiempo).
        dias = max((o.dia - p.dia).days, 1)
        factor = max(1.0, sqrt(dias / BASE_DIAS.get(c["frecuencia"], 30)))
        if c.get("max_salto_pct") and p.valor != 0:
            salto = abs(o.valor / p.valor - 1) * 100
            limite = c["max_salto_pct"] * factor
            if salto > limite:
                return (f"salto de {salto:.1f}% en {dias} días frente a {p.valor} ({p.fecha}); "
                        f"máximo creíble {limite:.1f}%")
        if c.get("max_salto_pts") is not None:
            salto = abs(o.valor - p.valor)
            limite = c["max_salto_pts"] * factor
            if salto > limite:
                return (f"salto de {salto:.2f} puntos en {dias} días frente a {p.valor} ({p.fecha}); "
                        f"máximo creíble {limite:.2f}")
    return None


BASE_DIAS = {"diaria": 1, "semanal": 7, "mensual": 30, "trimestral": 91, "semestral": 182, "anual": 365}


def guardar_cuarentena(rechazadas: list[tuple[Obs, str]], ruta: str = CUARENTENA) -> None:
    if not rechazadas:
        return
    nuevo = not os.path.exists(ruta)
    with open(ruta, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if nuevo:
            w.writerow(["capturado", "serie", "fecha", "valor", "fuente", "motivo"])
        for o, m in rechazadas:
            w.writerow([o.capturado, o.serie, o.fecha, o.valor, o.fuente, m])


def frescura(series: dict[str, list[Obs]], contratos: dict, hoy: date | None = None) -> list[dict]:
    """Edad del último dato de cada serie frente a su límite."""
    hoy = hoy or date.today()
    out = []
    for sid, c in contratos.items():
        v = series.get(sid)
        if not v:
            out.append({"serie": sid, "nombre": c["nombre"], "estado": "sin datos", "ultimo": None, "edad_dias": None,
                        "limite_dias": c["frescura_dias"]})
            continue
        u = v[-1]
        edad = (hoy - u.dia).days
        out.append({"serie": sid, "nombre": c["nombre"], "ultimo": u.fecha, "edad_dias": edad,
                    "limite_dias": c["frescura_dias"],
                    "estado": "fresco" if edad <= c["frescura_dias"] else "viejo"})
    return out
