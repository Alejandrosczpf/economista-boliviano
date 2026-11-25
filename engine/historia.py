"""Prueba retrospectiva: el índice año por año desde 1980, con series OFICIALES guardadas en el repositorio.

Con qué se calcula cada indicador en un año Y (régimen fijo, el de Bolivia hasta junio de 2026):
- inflacion_12m:  inflación a fin de año, FMI WEO (PCPIEPCH).
- rin_var_12m:    RIN neta del BCB a diciembre (Excel oficial, desde 2002) frente a diciembre anterior.
                  Antes de 2003: reservas totales del Banco Mundial (brutas, con oro), marcado en la fuente.
- liquidez_rin:   divisas / reservas brutas a diciembre (Excel del BCB, desde 2002).
- deficit_fiscal: menos el balance del gobierno general, FMI WEO (GGXCNL_NGDP). OJO: el MEFP publica el déficit
                  del sector público no financiero, que en Bolivia suele ser algo mayor.
- brecha:         paralelo (paralelo.bo, desde ago-2024) frente al oficial de venta Bs 6,96 a fin de año.
                  Para 1985 se usa una aproximación documentada (BRECHA_APROX); otros años no votan.
- pib_proy:       crecimiento REAL observado del año (FMI WEO), como sustituto de la proyección.
- inflacion_mensual y embi: no hay serie anual comparable; no votan.

Ningún valor se inventa: lo que falta no vota, igual que en el motor diario.
"""
from __future__ import annotations

from datetime import date

from engine.motor import PESOS, evaluar

# Aproximaciones documentadas (no hay serie oficial del paralelo para esos años).
BRECHA_APROX = {
    1985: (200.0, "aprox.: en 1985, antes de la estabilización de agosto, el dólar paralelo valía varias veces "
                  "el oficial (Sachs 1987, 'The Bolivian Hyperinflation and Stabilization'); cualquier valor "
                  "mayor a 10 % ya es rojo"),
}

OFICIAL_FIJO = 6.96  # venta, desde nov-2011 hasta jun-2026

# Episodios conocidos, para leer el resultado (no entran al cálculo).
EPISODIOS = {
    1984: "hiperinflación", 1985: "hiperinflación (pico) y estabilización",
    2002: "corrida de depósitos y crisis política", 2003: "crisis política (febrero y octubre)",
    2015: "caída del precio del gas: pérdida de reservas", 2016: "caída del precio del gas: pérdida de reservas",
    2019: "crisis política; déficit gemelos", 2020: "pandemia", 2023: "escasez de dólares", 2024: "escasez de dólares y combustible",
    2025: "inflación más alta en 36 años",
}


def _a_dic(serie: list, anio: int):
    return next((o for o in serie if o.fecha == f"{anio}-12-31"), None) if serie else None


def indicadores_anio(series: dict, anio: int) -> tuple[dict, dict]:
    """(valores, fuentes) del año. Un indicador sin dato no aparece."""
    v, f = {}, {}
    inf = _a_dic(series.get("fmi_weo_inflacion_fin"), anio)
    if inf:
        v["inflacion_12m"], f["inflacion_12m"] = inf.valor, "FMI WEO, inflación a fin de año"

    rin, rin_ant = _a_dic(series.get("rin"), anio), _a_dic(series.get("rin"), anio - 1)
    wb, wb_ant = _a_dic(series.get("wb_reservas"), anio), _a_dic(series.get("wb_reservas"), anio - 1)
    if rin and rin_ant and rin_ant.valor > 0:
        v["rin_var_12m"] = 100 * (rin.valor / rin_ant.valor - 1)
        f["rin_var_12m"] = "BCB, RIN neta a diciembre"
    elif wb and wb_ant and wb_ant.valor > 0:
        v["rin_var_12m"] = 100 * (wb.valor / wb_ant.valor - 1)
        f["rin_var_12m"] = "Banco Mundial, reservas totales (brutas, con oro)"

    div, bru = _a_dic(series.get("rin_divisas"), anio), _a_dic(series.get("rin_brutas"), anio)
    if div and bru and bru.valor > 0:
        v["liquidez_rin"], f["liquidez_rin"] = 100 * div.valor / bru.valor, "BCB, divisas / reservas brutas a diciembre"

    bal = _a_dic(series.get("fmi_weo_balance"), anio)
    if bal:
        v["deficit_fiscal"], f["deficit_fiscal"] = -bal.valor, "FMI WEO, gobierno general"

    par = [o for o in series.get("paralelo", []) if o.fecha[:4] == str(anio)]
    if par and par[-1].fecha >= f"{anio}-12-01" and anio < 2026:
        v["brecha"] = 100 * (par[-1].valor / OFICIAL_FIJO - 1)
        f["brecha"] = f"paralelo.bo ({par[-1].fecha}) frente a Bs {OFICIAL_FIJO}"
    elif anio in BRECHA_APROX:
        v["brecha"], f["brecha"] = BRECHA_APROX[anio]

    pib = _a_dic(series.get("fmi_weo_pib"), anio)
    if pib:
        v["pib_proy"], f["pib_proy"] = pib.valor, "FMI WEO, crecimiento real observado (sustituto de la proyección)"
    return v, f


def evaluar_anio(series: dict, anio: int):
    valores, _ = indicadores_anio(series, anio)
    return evaluar(valores, "fijo")


def prueba_retrospectiva(series: dict, desde: int = 1980, hasta: int | None = None) -> list[dict]:
    hasta = hasta or date.today().year - 1
    filas = []
    for anio in range(desde, hasta + 1):
        valores, fuentes = indicadores_anio(series, anio)
        if not valores:
            continue
        r = evaluar(valores, "fijo")
        filas.append({"anio": anio, "indice": r.indice, "estado": r.estado, "votan": len(r.senales),
                      "de": len(PESOS["fijo"]), "senales": r.senales, "valores": {k: round(x, 1) for k, x in valores.items()},
                      "fuentes": fuentes, "episodio": EPISODIOS.get(anio, "")})
    return filas


def informe(filas: list[dict]) -> str:
    """reports/historia.md: la tabla año por año y cómo leerla."""
    icono = {"calma": "🟢", "vigilancia": "🟡", "alerta": "🔴"}
    L = ["# Prueba retrospectiva del índice (1980 en adelante)", "",
         "Índice calculado año por año con series oficiales (FMI WEO, BCB, Banco Mundial, paralelo.bo), con las "
         "reglas del régimen fijo. Lo que no tiene dato no vota. Detalle de fuentes en `engine/historia.py`.", "",
         "| Año | Índice | Estado | Votan | Inflación fin de año | Reservas (var. %) | Déficit | Crec. PIB | Episodio |",
         "|---|---|---|---|---|---|---|---|---|"]
    for r in filas:
        v = r["valores"]
        g = lambda k: "—" if k not in v else f"{v[k]:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")  # noqa: E731
        L.append(f"| {r['anio']} | {r['indice']:.0f} | {icono[r['estado']]} {r['estado']} | {r['votan']}/{r['de']} "
                 f"| {g('inflacion_12m')} | {g('rin_var_12m')} | {g('deficit_fiscal')} | {g('pib_proy')} | {r['episodio']} |")
    L += ["", "Las reservas antes de 2003 son las totales del Banco Mundial (brutas, con oro); desde 2003, la RIN "
          "neta del BCB. El déficit es el del gobierno general según el FMI.", ""]
    return "\n".join(L)
