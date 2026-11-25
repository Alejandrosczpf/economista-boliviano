"""Arma site/pulso.json: lo que el tablero muestra al abrirse."""
from __future__ import annotations

import json
import os
from datetime import date

from engine.motor import (INICIO_FLOTACION, PESOS, UMBRALES, es, evaluar, fe, indicadores_actuales, regimen_en)
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
        "suficiente": res.suficiente,
        "no_votan": res.no_votan,
        "tarjetas": tarjetas,
        "cifras": {"tco": ultimo("tco"), "rin": ultimo("rin"), "embi": ultimo("embi"),
                   "inflacion_12m": ultimo("inflacion_12m")},
        "historia": hist,
        "salud": salud,
    }


QUE_SIGNIFICA = {
    "calma": "la economía no muestra señales de crisis",
    "vigilancia": "hay señales de tensión que conviene seguir de cerca, aunque no las de una crisis inminente",
    "alerta": "las señales se parecen a las de los años previos a una crisis, como 2022 antes de la escasez de dólares",
}


# Cada indicador dicho en lenguaje simple ({v} = su valor en formato boliviano). Sirven para lo bueno y lo malo.
CORTO = {
    "inflacion_12m": "la inflación anual ({v} %)",
    "inflacion_mensual": "la inflación del último mes ({v} %)",
    "rin_var_12m": "las reservas netas del BCB, que cambiaron {v} % en un año",
    "liquidez_rin": "la parte de las reservas en divisas listas para usar ({v} % del total)",
    "deficit_fiscal": "el déficit del Estado ({v} % del PIB)",
    "brecha": "la diferencia entre el dólar paralelo y el oficial ({v} %)",
    "depreciacion_30d": "el dólar oficial, que cambió {v} % en un mes",
    "embi": "el riesgo país ({v} puntos)",
    "pib_proy": "el crecimiento esperado de la economía ({v} %)",
}


def _dato(t: dict) -> str:
    v = t["valor"]
    return CORTO[t["id"]].format(v=es(v, 0 if abs(v) >= 100 else 1))


def resumen(pul: dict) -> list[str]:
    """'En pocas palabras': tres o cuatro frases en lenguaje simple, armadas solo con los datos del día."""
    t = pul["tarjetas"]
    rojos = sorted((x for x in t if x["semaforo"] == "rojo"), key=lambda x: -x["puntos"])
    amarillos = sorted((x for x in t if x["semaforo"] == "amarillo"), key=lambda x: -x["puntos"])
    verdes = [x for x in t if x["semaforo"] == "verde"]
    sin = [x for x in t if x["semaforo"] == "gris"]
    frases = [f"El índice de riesgo está en {es(pul['indice'], 0)} de 100, en {pul['estado']}: "
              f"{QUE_SIGNIFICA[pul['estado']]}."]
    if rojos:
        frases.append("Lo que más preocupa: " + "; ".join(_dato(x) for x in rojos[:3]) + "."
                      + (f" También en amarillo: {'; '.join(_dato(x) for x in amarillos[:2])}." if amarillos else ""))
    if verdes:
        frases.append("Lo que ayuda: " + "; ".join(_dato(x) for x in verdes) + ".")
    s = pul.get("semana")
    if s:
        d = s["indice_hoy"] - s["indice_antes"]
        mov = ("no cambió" if abs(d) < 0.05 else f"{'subió' if d > 0 else 'bajó'} {es(abs(d), 1)} puntos")
        frases.append(f"En la última semana el índice {mov}"
                      + (f" y pasó de {s['estado_antes']} a {s['estado_hoy']}." if s["estado_antes"] != s["estado_hoy"] else "."))
    if sin:
        frases.append(f"Sin dato reciente (no cuentan hoy): {', '.join(x['titulo'].lower() for x in sin)}.")
    return frases


def _pct(a: float, b: float) -> float:
    return (a / b - 1) * 100


def notas_graficos(series: dict) -> dict:
    """Las notas de los gráficos, escritas con los datos de hoy (antes eran texto fijo y envejecían)."""
    n = {}
    tco, par = series.get("tco"), series.get("paralelo")
    if tco and par:
        b = _pct(par[-1].valor, tco[-1].valor)
        lado = "por encima" if b > 0 else "por debajo"
        desde = next((o for o in tco if o.fecha >= INICIO_FLOTACION.isoformat()), tco[0])
        n["dolar"] = (f"El paralelo (Bs {es(par[-1].valor)}) está {es(abs(b), 1)} % {lado} del oficial "
                      f"(Bs {es(tco[-1].valor)}). Desde el inicio de la flotación, el oficial "
                      f"{'subió' if tco[-1].valor >= desde.valor else 'bajó'} {es(abs(_pct(tco[-1].valor, desde.valor)), 1)} %. "
                      "Paralelo: mediana diaria del USDT en plataformas P2P, según paralelo.bo (CC-BY 4.0).")
    rin = series.get("rin")
    if rin:
        u = rin[-1]
        hace_un_anio = next((o for o in reversed(rin) if o.fecha <= f"{int(u.fecha[:4]) - 1}{u.fecha[4:]}"), None)
        minimo = min(rin, key=lambda o: o.valor)
        n["rin"] = (f"Última: {es(u.valor, 0)} millones de dólares ({fe(u.fecha)})"
                    + (f", {es(abs(_pct(u.valor, hace_un_anio.valor)), 1)} % {'más' if u.valor >= hace_un_anio.valor else 'menos'} que un año antes"
                       if hace_un_anio else "")
                    + f". El mínimo desde 2002 fue {es(minimo.valor, 0)} millones ({fe(minimo.fecha)}). "
                      "Son reservas NETAS: la prensa suele citar las brutas, que son mayores.")
    inf = series.get("inflacion_12m")
    if inf:
        u = inf[-1]
        pico = max(inf, key=lambda o: o.valor)
        n["inflacion"] = (f"Última: {es(u.valor)} % a 12 meses ({fe(u.fecha)}). "
                          f"El máximo de este gráfico fue {es(pico.valor)} % ({fe(pico.fecha)}).")
    embi = series.get("embi")
    if embi:
        n["embi"] = (f"Último dato: {es(embi[-1].valor, 0)} puntos ({fe(embi[-1].fecha)}). "
                     "Son puntos sueltos tomados de la prensa: no hay una serie diaria pública.")
    return n


INFORMES = os.path.join(RAIZ, "informes")


def _md_a_html(md: str) -> str:
    """Markdown mínimo y seguro (se escapa todo el HTML): ## títulos, listas con '- ', **negrita**, párrafos."""
    import html as H
    import re
    out, lista, parrafo = [], False, []

    def linea(t):
        return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", H.escape(t))

    def cerrar_parrafo():
        if parrafo:
            out.append(f"<p>{linea(' '.join(parrafo))}</p>")
            parrafo.clear()
    for crudo in md.splitlines():
        t = crudo.strip()
        if t.startswith("- "):
            cerrar_parrafo()
            if not lista:
                out.append("<ul>")
                lista = True
            out.append(f"<li>{linea(t[2:])}</li>")
            continue
        if lista:
            out.append("</ul>")
            lista = False
        if not t:
            cerrar_parrafo()
        elif t.startswith("#"):
            cerrar_parrafo()
            out.append(f"<h4>{linea(t.lstrip('#').strip())}</h4>")
        else:
            parrafo.append(t)
    cerrar_parrafo()
    if lista:
        out.append("</ul>")
    return "\n".join(out)


def informe_publicable(carpeta: str = INFORMES, hoy: date | None = None, max_dias: int = 14) -> dict | None:
    """El informe más reciente (informes/AAAA-MM-DD.md) si tiene 14 días o menos y TODAS sus cifras pasan el
    verificador contra la ficha de hechos de su fecha. Si no pasa, no se publica (y se avisa en la consola)."""
    from engine import hechos as H
    from engine.verificador import numeros, verificar_informe
    hoy = hoy or date.today()
    if not os.path.isdir(carpeta):
        return None
    archivos = sorted(f for f in os.listdir(carpeta) if len(f) == 13 and f.endswith(".md") and f[:4].isdigit())
    if not archivos:
        return None
    nombre = archivos[-1]
    fecha = nombre[:10]
    if (hoy - date.fromisoformat(fecha)).days > max_dias:
        return None
    texto = open(os.path.join(carpeta, nombre), encoding="utf-8").read()
    ficha = H.leer(fecha)
    if ficha is None:
        print(f"  informe {nombre}: sin ficha de hechos de esa fecha; no se publica")
        return None
    malos = verificar_informe(texto, ficha)
    if malos:
        print(f"  informe {nombre}: BLOQUEADO, {len(malos)} cifras sin respaldo: {', '.join(c for c, _ in malos)}")
        return None
    return {"fecha": fecha, "html": _md_a_html(texto), "cifras": len(numeros(texto))}


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
