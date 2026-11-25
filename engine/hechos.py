"""Ficha de hechos del día: las únicas cifras que un informe escrito por IA puede citar.

El robot la escribe en cada corrida en data/hechos/AAAA-MM-DD.json (y la guarda en git: la IA no la toca).
Cada hecho tiene:
- valor: el número exacto;
- texto: cómo escribirlo (formato boliviano, con unidad);
- claves: palabras que deben aparecer en la MISMA oración que la cifra (así "la inflación es 59,6 %"
  no pasa aunque 59,6 sea un dato real: es el cambio de las reservas, no la inflación).
"""
from __future__ import annotations

import json
import os
from datetime import date

from engine.motor import es, fe
from pipeline.store import RAIZ

CARPETA = os.path.join(RAIZ, "data", "hechos")

# palabras clave por indicador (sin tildes, en minúsculas: el verificador normaliza igual)
CLAVES = {
    "indice": ["indice", "riesgo"],
    "inflacion_12m": ["inflacion", "precios"],
    "inflacion_mensual": ["inflacion", "precios", "mes"],
    "rin_var_12m": ["reserva"],
    "liquidez_rin": ["reserva", "divisa", "liquid"],
    "deficit_fiscal": ["deficit", "fiscal", "estado", "gasto"],
    "brecha": ["brecha", "paralelo", "oficial", "dolar"],
    "depreciacion_30d": ["dolar", "oficial", "tipo de cambio", "deprecia"],
    "embi": ["riesgo pais", "embi", "bonos"],
    "pib_proy": ["crecimiento", "pib", "economia", "proyeccion", "recesion", "decrec", "contrac"],
}


def _h(id_, valor, texto, claves, fecha=None):
    return {"id": id_, "valor": round(float(valor), 4), "texto": texto, "claves": claves, "fecha": fecha}


def construir(pul: dict, series: dict) -> dict:
    """Arma la ficha con lo que el Pulso muestra hoy."""
    H = [_h("indice", pul["indice"], f"{es(pul['indice'], 1)} de 100", CLAVES["indice"], pul["generado"]),
         _h("escala_indice", 100, "100 (máximo del índice)", ["indice", "100"])]
    for t in pul["tarjetas"]:
        if t["valor"] is None:
            continue
        dec = 0 if abs(t["valor"]) >= 100 else 2
        H.append(_h(t["id"], t["valor"], f"{es(t['valor'], dec)} {t['unidad']}", CLAVES[t["id"]], t["fecha"]))
    # períodos con que se definen los indicadores ("inflación a 12 meses", "en 30 días"): válidos solo junto a su unidad
    H.append(_h("periodo_12_meses", 12, "12 meses", ["12 meses", "doce meses"]))
    H.append(_h("periodo_30_dias", 30, "30 días", ["30 dias", "treinta dias"]))
    votan = sum(1 for t in pul["tarjetas"] if t["semaforo"] != "gris")
    H.append(_h("indicadores_votan", votan, f"{votan} indicadores votaron", ["indicador"]))
    H.append(_h("indicadores_total", len(pul["tarjetas"]), f"{len(pul['tarjetas'])} indicadores", ["indicador"]))

    def ultimo(sid, idh, nombre, unidad, claves, dec=2):
        s = series.get(sid)
        if s:
            H.append(_h(idh, s[-1].valor, f"{nombre}: {es(s[-1].valor, dec)} {unidad} ({fe(s[-1].fecha)})", claves, s[-1].fecha))
    ultimo("tco", "dolar_oficial", "dólar oficial", "Bs", ["dolar", "oficial", "tipo de cambio", "bcb"])
    ultimo("paralelo", "dolar_paralelo", "dólar paralelo", "Bs", ["dolar", "paralelo", "usdt", "digital"])
    ultimo("rin", "rin_neta", "reservas internacionales netas", "millones de USD", ["reserva"], 0)
    ultimo("rin_brutas", "rin_brutas", "reservas internacionales brutas", "millones de USD", ["reserva"], 0)
    for sid, quien in (("pib_proy_fmi", "FMI"), ("pib_proy_bcb", "BCB"), ("pib_proy_bm", "Banco Mundial")):
        ultimo(sid, sid, f"proyección del {quien}", "%", CLAVES["pib_proy"] + [quien.lower()])

    # a un paso de cambiar: la distancia al umbral, el umbral y el índice si cambiara (solo los cercanos)
    for r in pul.get("a_un_paso") or []:
        if not r["cerca"]:
            continue
        clave = f"{r['id']}_{r['direccion']}"
        H.append(_h(f"distancia_{clave}", r["distancia"],
                    f"a {es(r['distancia'], 2)} de pasar a {r['pasaria_a']} ({r['titulo'].lower()})", CLAVES[r["id"]]))
        H.append(_h(f"umbral_{clave}", r["umbral"], f"umbral de {r['pasaria_a']}: {es(r['umbral'], 2)} ({r['titulo'].lower()})",
                    CLAVES[r["id"]] + ["umbral"]))
        H.append(_h(f"indice_si_{clave}", r["indice_si_cambia"],
                    f"el índice pasaría a {es(r['indice_si_cambia'], 1)} si {r['titulo'].lower()} pasara a {r['pasaria_a']}",
                    CLAVES["indice"]))

    s = pul.get("semana")
    if s:
        d = s["indice_hoy"] - s["indice_antes"]
        H.append(_h("indice_semana_antes", s["indice_antes"], f"{es(s['indice_antes'], 1)} hace una semana ({fe(s['desde'])})",
                    CLAVES["indice"] + ["semana"], s["desde"]))
        H.append(_h("indice_cambio_semana", abs(d), f"{'+' if d >= 0 else '−'}{es(abs(d), 1)} puntos en la semana",
                    CLAVES["indice"] + ["semana", "punto", "subi", "baj"]))
        H.append(_h("dias_semana", 7, "7 días", ["dia", "semana"]))
    return {"fecha": pul["generado"], "estado": pul["estado"], "regimen": pul["regimen"], "hechos": H}


def guardar(ficha: dict) -> str:
    """La ficha de cada fecha se escribe UNA sola vez (la primera corrida del día) y queda fija.
    Si se reescribiera en una segunda corrida del mismo día, un informe ya aprobado con esa fecha
    dejaría de coincidir con su ficha y desaparecería de la página. Lo nuevo entra en la ficha del día siguiente."""
    os.makedirs(CARPETA, exist_ok=True)
    ruta = os.path.join(CARPETA, f"{ficha['fecha']}.json")
    if os.path.exists(ruta):
        return ruta
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(ficha, f, ensure_ascii=False, indent=1)
        f.write("\n")
    return ruta


def leer(fecha: str | date) -> dict | None:
    ruta = os.path.join(CARPETA, f"{fecha}.json")
    if not os.path.exists(ruta):
        return None
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)
