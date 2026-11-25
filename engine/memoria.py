"""Memoria del índice: qué dijo el sistema cada día desde el inicio de la flotación.

data/indice.csv guarda una fila por día, con dos orígenes:
- "en vivo": lo que el robot calculó ese día. Queda congelado: es el registro de lo que se dijo.
- "reconstruido": días anteriores al robot (o sin corrida, como los fines de semana),
  calculados con los datos que ya se conocían ese día. Se recalculan en cada corrida,
  así un dato histórico cargado después mejora la reconstrucción.

Regla contra el sesgo de mirar al futuro: un dato con fecha F de una serie con
rezago_dias R (ver config/series.json) solo cuenta desde el día F + R, que es
cuando se publicó. Ejemplo: la inflación de octubre (31-oct) cuenta desde el 7-nov.

Regla de mayoría: un día en que vota menos de la mitad de los indicadores no es
"suficiente". El índice de ese día existe, pero no se dibuja ni cuenta como cambio
de estado. Con pocos votos, el índice depende más de QUÉ indicadores votaron que de
la economía. Ejemplo: el 29-jun solo votaban el déficit y el PIB, ambos en rojo,
y el índice daba 100.
"""
from __future__ import annotations

import csv
import os
from datetime import date, timedelta

from engine.motor import INICIO_FLOTACION, PESOS, evaluar, indicadores_actuales, regimen_en
from pipeline.store import RAIZ

RUTA = os.path.join(RAIZ, "data", "indice.csv")
INDICADORES = list(PESOS["flotante"])  # incluye todos los del régimen fijo
CAMPOS = ["fecha", "indice", "estado", "regimen", "votan", "de", "origen"] + INDICADORES
EN_VIVO, RECONSTRUIDO = "en vivo", "reconstruido"


def conocido_en(series: dict, contratos: dict, dia: date) -> dict:
    """Solo los datos que ya se habían publicado el día 'dia'."""
    out = {}
    for sid, obs in series.items():
        rezago = timedelta(days=contratos.get(sid, {}).get("rezago_dias", 0))
        vistas = [o for o in obs if o.dia + rezago <= dia]
        if vistas:
            out[sid] = vistas
    return out


def calcular_dia(series: dict, contratos: dict, dia: date, origen: str) -> dict:
    """Fila del índice para 'dia'. En vivo usa todo lo guardado; reconstruido, solo lo ya publicado."""
    datos = series if origen == EN_VIVO else conocido_en(series, contratos, dia)
    regimen = regimen_en(dia)
    valores, _ = indicadores_actuales(datos, contratos, dia)
    res = evaluar(valores, regimen)
    fila = {"fecha": dia.isoformat(), "indice": res.indice, "estado": res.estado, "regimen": regimen,
            "votan": len(res.senales), "de": len(PESOS[regimen]), "origen": origen}
    for ind in INDICADORES:
        s = res.senales.get(ind)
        fila[ind] = "" if s is None else s
    return fila


def leer(ruta: str = RUTA) -> list[dict]:
    if not os.path.exists(ruta):
        return []
    with open(ruta, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def escribir(filas: list[dict], ruta: str = RUTA) -> None:
    with open(ruta, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS, extrasaction="ignore")
        w.writeheader()
        for fila in sorted(filas, key=lambda r: r["fecha"]):
            w.writerow(fila)


def actualizar(previas: list[dict], series: dict, contratos: dict, hoy: date,
               desde: date = INICIO_FLOTACION) -> list[dict]:
    """Conserva las filas en vivo de días anteriores, escribe la de hoy en vivo
    y reconstruye todos los demás días desde 'desde'."""
    vivas = {r["fecha"]: r for r in previas if r.get("origen") == EN_VIVO and r["fecha"] < hoy.isoformat()}
    filas = []
    d = desde
    while d < hoy:
        filas.append(vivas.get(d.isoformat()) or calcular_dia(series, contratos, d, RECONSTRUIDO))
        d += timedelta(days=1)
    filas.append(calcular_dia(series, contratos, hoy, EN_VIVO))
    return filas


def suficiente(fila: dict) -> bool:
    """Vota la mayoría de los indicadores (5 de 9 en flotación)."""
    return 2 * int(fila["votan"]) > int(fila["de"])


def cambios_de_estado(filas: list[dict]) -> list[dict]:
    """Cambios entre días con datos suficientes (los días intermedios con pocos votos se saltan)."""
    out, previo = [], None
    for r in sorted((r for r in filas if suficiente(r)), key=lambda r: r["fecha"]):
        if previo is not None and r["estado"] != previo["estado"]:
            out.append({"fecha": r["fecha"], "de": previo["estado"], "a": r["estado"],
                        "indice": float(r["indice"])})
        previo = r
    return out


def para_pulso(filas: list[dict]) -> dict:
    """Lo que el gráfico del Pulso necesita."""
    puntos = [{"fecha": r["fecha"], "valor": float(r["indice"]), "estado": r["estado"],
               "votan": int(r["votan"]), "de": int(r["de"]), "origen": r["origen"], "suficiente": suficiente(r)}
              for r in sorted(filas, key=lambda r: r["fecha"])]
    vivos = [p["fecha"] for p in puntos if p["origen"] == EN_VIVO]
    return {"puntos": puntos, "cambios": cambios_de_estado(filas), "robot_desde": vivos[0] if vivos else None}
