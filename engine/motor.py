"""Motor de riesgo del Economista Boliviano, recalibrado al régimen de flotación.

Método: señales tipo KLR (Kaminsky-Lizondo-Reinhart). Cada indicador emite
0 (verde), 0,5 (amarillo) o 1 (rojo). El índice es el promedio ponderado de las
señales DISPONIBLES (0-100). Un indicador sin dato fresco no vota: no se inventa.

Cambio de régimen (29-jun-2026, fin del Bs 6,96):
- Con dólar FIJO, la brecha cambiaria es la alarma mayor y la caída de reservas
  es la defensa del tipo de cambio.
- Con dólar FLOTANTE, depreciarse es ajuste normal; la alarma es la PRESIÓN
  cambiaria (depreciación rápida + pérdida de reservas). La brecha pasa a ser un
  termómetro de confianza en el nuevo régimen.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

INICIO_FLOTACION = date(2026, 6, 29)

# Umbrales: (amarillo_desde, rojo_desde). "mayor=True" significa que valores altos son malos.
UMBRALES = {
    "inflacion_12m":     dict(amarillo=5, rojo=12, mayor=True),
    "inflacion_mensual": dict(amarillo=0.8, rojo=1.5, mayor=True),     # 0,8% mensual ≈ 10% anualizado
    "rin_var_12m":       dict(amarillo=-5, rojo=-15, mayor=False),     # % de cambio anual de reservas
    "liquidez_rin":      dict(amarillo=40, rojo=25, mayor=False),      # % de reservas en divisas
    "deficit_fiscal":    dict(amarillo=4, rojo=7, mayor=True),         # % del PIB
    "brecha":            dict(amarillo=3, rojo=10, mayor=True),        # % paralelo sobre oficial
    "embi":              dict(amarillo=400, rojo=800, mayor=True),     # puntos básicos
    "pib_proy":          dict(amarillo=1.5, rojo=0, mayor=False),      # % crecimiento esperado
    "depreciacion_30d":  dict(amarillo=2, rojo=5, mayor=True),         # % en ~30 días (solo flotación)
}

# Pesos inspirados en la relación ruido/señal de la literatura de alertas tempranas:
# reservas y tipo de cambio son los mejores predictores.
PESOS = {
    "fijo":      {"inflacion_12m": 1, "inflacion_mensual": 0.5, "rin_var_12m": 2, "liquidez_rin": 1,
                  "deficit_fiscal": 1.5, "brecha": 2, "embi": 1, "pib_proy": 1},
    "flotante":  {"inflacion_12m": 1, "inflacion_mensual": 1, "rin_var_12m": 2, "liquidez_rin": 1,
                  "deficit_fiscal": 1.5, "brecha": 1.5, "embi": 1, "pib_proy": 1, "depreciacion_30d": 1.5},
}

ESTADOS = [(0, 35, "calma"), (35, 60, "vigilancia"), (60, 101, "alerta")]

# De qué series se alimenta cada indicador (ver indicadores_actuales).
# Lo usan los avisos para decir qué indicador deja de votar cuando una serie se vence.
INSUMOS = {
    "inflacion_12m": ["inflacion_12m"],
    "inflacion_mensual": ["inflacion_mensual"],
    "rin_var_12m": ["rin"],
    "liquidez_rin": ["rin_divisas", "rin_brutas"],
    "deficit_fiscal": ["deficit_fiscal"],
    "brecha": ["paralelo", "tco"],
    "depreciacion_30d": ["tco"],
    "embi": ["embi"],
    "pib_proy": ["pib_proy_fmi", "pib_proy_bcb", "pib_proy_bm"],
}


def senal(indicador: str, valor: float | None) -> float | None:
    if valor is None:
        return None
    u = UMBRALES[indicador]
    if u["mayor"]:
        return 1.0 if valor >= u["rojo"] else 0.5 if valor >= u["amarillo"] else 0.0
    return 1.0 if valor <= u["rojo"] else 0.5 if valor <= u["amarillo"] else 0.0


def estado(indice: float) -> str:
    for lo, hi, nombre in ESTADOS:
        if lo <= indice < hi:
            return nombre
    return "alerta"


@dataclass
class Resultado:
    indice: float
    estado: str
    regimen: str
    senales: dict = field(default_factory=dict)       # indicador -> señal (0/0.5/1)
    valores: dict = field(default_factory=dict)       # indicador -> valor usado
    no_votan: list = field(default_factory=list)      # indicadores sin dato fresco
    contribuciones: dict = field(default_factory=dict)


def evaluar(valores: dict[str, float | None], regimen: str) -> Resultado:
    pesos = PESOS[regimen]
    num = den = 0.0
    senales, contrib, no_votan = {}, {}, []
    for ind, w in pesos.items():
        s = senal(ind, valores.get(ind))
        if s is None:
            no_votan.append(ind)
            continue
        senales[ind] = s
        num += w * s
        den += w
        contrib[ind] = w * s
    indice = round(100 * num / den, 1) if den else 0.0
    # contribución en puntos del índice
    contrib = {k: round(100 * v / den, 1) for k, v in contrib.items()} if den else {}
    return Resultado(indice, estado(indice), regimen, senales,
                     {k: valores.get(k) for k in pesos}, no_votan, contrib)


def regimen_en(dia: date) -> str:
    return "flotante" if dia >= INICIO_FLOTACION else "fijo"


# ---------- Derivar indicadores desde las series observadas ----------

def _ultimo(serie, hoy, limite_dias):
    """Último dato si es fresco; si no, None (no vota)."""
    if not serie:
        return None
    u = serie[-1]
    return u if (hoy - u.dia).days <= limite_dias else None


def _anterior(serie, fecha: date, dias_min: int, dias_max: int):
    """Dato más cercano entre dias_min y dias_max antes de 'fecha'."""
    candidatos = [o for o in serie if dias_min <= (fecha - o.dia).days <= dias_max]
    if not candidatos:
        return None
    objetivo = fecha - timedelta(days=(dias_min + dias_max) // 2)
    return min(candidatos, key=lambda o: abs((o.dia - objetivo).days))


def es(v: float, d: int = 2) -> str:
    """Número en formato boliviano: 3.932,8"""
    t = f"{v:,.{d}f}"
    return t.replace(",", "X").replace(".", ",").replace("X", ".")


def fe(s: str) -> str:
    a, m, d = s.split("-")
    return f"{int(d)} {['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic'][int(m)-1]} {a}"


def indicadores_actuales(series: dict, contratos: dict, hoy: date) -> tuple[dict, dict]:
    """Devuelve (valores, detalle) para el día 'hoy'."""
    lim = {k: c["frescura_dias"] for k, c in contratos.items()}
    v: dict[str, float | None] = {}
    det: dict[str, dict] = {}

    def reg(nombre, valor, base, nota=""):
        v[nombre] = None if valor is None else round(valor, 2)
        det[nombre] = {"valor": v[nombre], "fecha": base.fecha if base else None,
                       "fuente": base.fuente if base else None, "url": base.url if base else None, "nota": nota}

    inf = _ultimo(series.get("inflacion_12m"), hoy, lim["inflacion_12m"])
    reg("inflacion_12m", inf.valor if inf else None, inf)
    im = _ultimo(series.get("inflacion_mensual"), hoy, lim["inflacion_mensual"])
    reg("inflacion_mensual", im.valor if im else None, im)

    rin = _ultimo(series.get("rin"), hoy, lim["rin"])
    if rin:
        prev = _anterior(series["rin"], rin.dia, 300, 430)
        var = (rin.valor / prev.valor - 1) * 100 if prev else None
        reg("rin_var_12m", var, rin, f"frente a {es(prev.valor, 0)} millones ({fe(prev.fecha)})" if prev else "sin dato de hace un año")
    else:
        reg("rin_var_12m", None, None)

    # Liquidez: divisas sobre reservas BRUTAS del mismo mes (las divisas son un componente de las brutas;
    # dividir por las netas mezclaría conceptos).
    div = _ultimo(series.get("rin_divisas"), hoy, lim["rin_divisas"])
    if div and series.get("rin_brutas"):
        base = min(series["rin_brutas"], key=lambda o: abs((o.dia - div.dia).days))
        if abs((base.dia - div.dia).days) <= 20:
            reg("liquidez_rin", 100 * div.valor / base.valor, div,
                f"{es(div.valor, 0)} de {es(base.valor, 0)} millones de reservas brutas")
        else:
            reg("liquidez_rin", None, None)
    else:
        reg("liquidez_rin", None, None)

    df = _ultimo(series.get("deficit_fiscal"), hoy, lim["deficit_fiscal"])
    reg("deficit_fiscal", df.valor if df else None, df)

    tco = _ultimo(series.get("tco"), hoy, lim["tco"])
    par = _ultimo(series.get("paralelo"), hoy, lim["paralelo"])
    if tco and par:
        reg("brecha", (par.valor / tco.valor - 1) * 100, par, f"paralelo {es(par.valor)} vs oficial {es(tco.valor)}")
    else:
        up = series.get("paralelo", [None])[-1]
        nota = (f"último paralelo: Bs {es(up.valor)} del {fe(up.fecha)}, con {(hoy - up.dia).days} días; "
                f"se necesita uno de menos de {lim['paralelo']}") if up else "no hay datos del paralelo"
        reg("brecha", None, up, nota)

    if tco:
        prev = _anterior(series["tco"], tco.dia, 25, 40)
        reg("depreciacion_30d", (tco.valor / prev.valor - 1) * 100 if prev else None, tco,
            f"de Bs {es(prev.valor)} ({fe(prev.fecha)}) a Bs {es(tco.valor)}" if prev else "sin dato de hace ~30 días")
    else:
        reg("depreciacion_30d", None, None)

    e = _ultimo(series.get("embi"), hoy, lim["embi"])
    reg("embi", e.valor if e else None, e)

    # Proyección de PIB: la más reciente entre FMI, BCB y BM (las tres compiten; ver 10.3)
    proys = [s[-1] for k in ("pib_proy_fmi", "pib_proy_bcb", "pib_proy_bm")
             if (s := series.get(k)) and (hoy - s[-1].dia).days <= lim[k]]
    if proys:
        prom = sum(p.valor for p in proys) / len(proys)
        reg("pib_proy", prom, max(proys, key=lambda p: p.fecha),
            "promedio de " + "; ".join(f"{p.fuente}: {es(p.valor)} %" for p in proys))
    else:
        reg("pib_proy", None, None)
    return v, det


# ---------- Episodios históricos para pruebas de regresión ----------
# Datos anuales. "aprox" = valor de referencia a confirmar con la serie oficial
# cuando el recolector histórico esté completo; las pruebas solo exigen el ORDEN
# correcto de los estados, no decimales.
HISTORIA = {
    1985: dict(inflacion_12m=8170, deficit_fiscal=10, brecha=200, fuente="aprox: hiperinflación 1984-85"),
    2014: dict(inflacion_12m=5.2, rin_var_12m=4.8, deficit_fiscal=3.4, brecha=0, fuente="aprox: auge del gas"),
    2015: dict(inflacion_12m=3.0, rin_var_12m=-13.7, deficit_fiscal=6.9, brecha=0, fuente="aprox"),
    2016: dict(inflacion_12m=4.0, rin_var_12m=-22.8, deficit_fiscal=7.2, brecha=0, fuente="aprox: caída del precio del gas"),
    2019: dict(inflacion_12m=1.5, rin_var_12m=-27.7, deficit_fiscal=7.2, brecha=0, fuente="aprox; RIN BCB"),
    2022: dict(inflacion_12m=3.1, rin_var_12m=-20.1, deficit_fiscal=7.1, brecha=0, fuente="RIN BCB 4752→3796"),
    2023: dict(inflacion_12m=2.1, rin_var_12m=-55.0, deficit_fiscal=10.9, brecha=8, fuente="RIN BCB 3796→1709"),
    2024: dict(inflacion_12m=9.97, rin_var_12m=15.7, deficit_fiscal=10.4, brecha=100, fuente="RIN BCB 1709→1977"),
}


def evaluar_anio(anio: int) -> Resultado:
    d = {k: v for k, v in HISTORIA[anio].items() if k != "fuente"}
    return evaluar(d, "fijo")
