"""Arma site/pulso.json: lo que el tablero muestra al abrirse."""
from __future__ import annotations

import json
import os
from datetime import date

from engine.motor import (INICIO_FLOTACION, PESOS, UMBRALES, evaluar, indicadores_actuales, regimen_en)
from pipeline.store import RAIZ

COLOR = {0.0: "verde", 0.5: "amarillo", 1.0: "rojo", None: "gris"}

# Capa educativa: qué es, cómo leerlo, qué significa para una familia.
EXPLICA = {
    "inflacion_12m": dict(titulo="Inflación a 12 meses", unidad="%",
        que="Cuánto subieron los precios de la canasta familiar en el último año.",
        lectura="Verde hasta 5 %, amarillo hasta 12 %, rojo por encima.",
        familia="Con 7 % anual, lo que hoy cuesta Bs 100 costará unos Bs 107 en un año."),
    "inflacion_mensual": dict(titulo="Inflación del último mes", unidad="%",
        que="Subida de precios en un solo mes: anticipa hacia dónde va la inflación anual.",
        lectura="Más de 0,8 % al mes equivale a más de 10 % al año.",
        familia="Un mes de 2 % se siente en el mercado esa misma semana."),
    "rin_var_12m": dict(titulo="Reservas: cambio en un año", unidad="%",
        que="Cuánto crecieron o cayeron las reservas internacionales NETAS del BCB (oro y divisas menos obligaciones) en 12 meses.",
        lectura="Caer más de 15 % en un año es la señal clásica antes de una crisis cambiaria.",
        familia="Reservas que crecen dan respaldo para importar combustible, medicinas y alimentos."),
    "liquidez_rin": dict(titulo="Reservas líquidas", unidad="% del total",
        que="Parte de las reservas brutas que está en divisas listas para usarse (no en oro).",
        lectura="Bolivia guarda la mayor parte en oro: menos de 25 % en divisas es poco margen.",
        familia="El oro no paga importaciones directamente: hay que venderlo primero."),
    "deficit_fiscal": dict(titulo="Déficit fiscal", unidad="% del PIB",
        que="Cuánto gasta el Estado por encima de lo que recauda, como parte de la economía.",
        lectura="Más de 7 % del PIB por varios años lleva a deuda cara o a imprimir dinero.",
        familia="Un déficit que se financia imprimiendo billetes termina en precios más altos."),
    "brecha": dict(titulo="Brecha cambiaria", unidad="%",
        que="Diferencia entre el dólar paralelo y el dólar oficial.",
        lectura="Con flotación, una brecha cercana a cero indica que la gente cree en el nuevo régimen.",
        familia="Si la brecha vuelve a abrirse, conseguir dólares se encarece otra vez."),
    "depreciacion_30d": dict(titulo="Dólar oficial: cambio en un mes", unidad="%",
        que="Cuánto subió (o bajó) el dólar oficial en los últimos ~30 días.",
        lectura="Con flotación, moverse es normal; más de 5 % en un mes indica presión.",
        familia="Un dólar que sube rápido encarece lo importado en pocas semanas."),
    "embi": dict(titulo="Riesgo país", unidad="puntos básicos",
        que="Interés extra que los inversionistas exigen a Bolivia frente a EE. UU. (100 pb = 1 %).",
        lectura="Menos de 400 es aceptable; más de 800 deja al país casi sin crédito externo.",
        familia="Crédito externo caro significa menos dinero para obras y más presión sobre el dólar."),
    "pib_proy": dict(titulo="Crecimiento esperado del año", unidad="%",
        que="Promedio de lo que proyectan FMI, BCB y Banco Mundial para la economía este año.",
        lectura="Por debajo de 0 % es recesión: la economía produce menos que el año anterior.",
        familia="Recesión suele traer menos empleo formal y menos ingresos en el comercio."),
}

SERIES_GRAFICO = ["tco", "paralelo", "rin", "inflacion_12m", "embi"]


def construir(series: dict, contratos: dict, salud: dict, hoy: date) -> dict:
    regimen = regimen_en(hoy)
    valores, detalle = indicadores_actuales(series, contratos, hoy)
    res = evaluar(valores, regimen)
    tarjetas = []
    for ind in PESOS[regimen]:
        d = detalle.get(ind, {})
        s = res.senales.get(ind)
        tarjetas.append({"id": ind, **EXPLICA[ind], "valor": d.get("valor"), "fecha": d.get("fecha"),
                         "fuente": d.get("fuente"), "url": d.get("url"), "nota": d.get("nota"),
                         "semaforo": COLOR[s], "peso": PESOS[regimen][ind],
                         "puntos": res.contribuciones.get(ind, 0), "umbrales": UMBRALES[ind]})
    hist = {k: [{"fecha": o.fecha, "valor": o.valor} for o in series.get(k, [])] for k in SERIES_GRAFICO}
    ultimo = lambda k: (series[k][-1].valor if series.get(k) else None)  # noqa: E731
    return {
        "generado": hoy.isoformat(),
        "regimen": regimen,
        "regimen_desde": INICIO_FLOTACION.isoformat(),
        "indice": res.indice,
        "estado": res.estado,
        "no_votan": res.no_votan,
        "tarjetas": tarjetas,
        "cifras": {"tco": ultimo("tco"), "rin": ultimo("rin"), "embi": ultimo("embi"),
                   "inflacion_12m": ultimo("inflacion_12m")},
        "historia": hist,
        "salud": salud,
    }


def guardar(pulso: dict, ruta: str | None = None) -> str:
    ruta = ruta or os.path.join(RAIZ, "site", "pulso.json")
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(pulso, f, ensure_ascii=False, indent=1)
    # La página lleva los datos adentro: un solo archivo que se abre sin servidor.
    plantilla = os.path.join(RAIZ, "site", "plantilla.html")
    if os.path.exists(plantilla):
        html = open(plantilla, encoding="utf-8").read()
        datos = json.dumps(pulso, ensure_ascii=False).replace("</", "<\\/")
        with open(os.path.join(RAIZ, "site", "index.html"), "w", encoding="utf-8") as f:
            f.write(html.replace("/*PULSO*/", datos))
    return ruta
