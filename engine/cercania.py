"""A un paso de cambiar: cuánto le falta a cada indicador para cambiar de color, y qué le pasaría al índice.

No es una predicción: son distancias a umbrales que ya están publicados (engine/motor.py, UMBRALES).
- Para cada indicador que vota se calcula el umbral siguiente hacia PEOR y hacia MEJOR, y la distancia.
- La cercanía se mide en fracciones de la franja amarilla (|rojo − amarillo|), para comparar indicadores
  con unidades distintas (%, puntos básicos, % del PIB). "A un paso" = menos de CERCA de esa franja.
- El índice si cambiara: se recalcula con la señal nueva (y la histéresis del estado actual).
"""
from __future__ import annotations

from engine.motor import UMBRALES, estado_con_memoria

CERCA = 0.25  # fracción de la franja amarilla
ORDEN = [0.0, 0.5, 1.0]  # verde, amarillo, rojo
NOMBRE = {0.0: "verde", 0.5: "amarillo", 1.0: "rojo"}


def _umbral_hacia(u: dict, senal: float, direccion: str) -> float | None:
    """Valor que hay que cruzar para pasar a la señal vecina. 'peor' sube de señal; 'mejor', baja."""
    if direccion == "peor":
        return {0.0: u["amarillo"], 0.5: u["rojo"]}.get(senal)
    return {1.0: u["rojo"], 0.5: u["amarillo"]}.get(senal)


def calcular(pul: dict) -> list[dict]:
    """pul: el Pulso del día (tarjetas con valor, semáforo y peso). Devuelve un registro por (indicador, dirección),
    de más cercano a más lejano."""
    votan = [t for t in pul["tarjetas"] if t["semaforo"] != "gris" and t["valor"] is not None]
    senales = {t["id"]: {"verde": 0.0, "amarillo": 0.5, "rojo": 1.0}[t["semaforo"]] for t in votan}
    pesos = {t["id"]: t["peso"] for t in votan}
    total = sum(pesos.values())

    def indice_con(cambio: dict) -> float:
        s = {**senales, **cambio}
        return round(100 * sum(pesos[k] * s[k] for k in s) / total, 1)

    out = []
    for t in votan:
        ind, v, s = t["id"], t["valor"], senales[t["id"]]
        u = UMBRALES[ind]
        franja = abs(u["rojo"] - u["amarillo"])
        for direccion in ("peor", "mejor"):
            umbral = _umbral_hacia(u, s, direccion)
            if umbral is None:
                continue  # ya está en el extremo (verde no mejora, rojo no empeora)
            distancia = abs(v - umbral)
            nueva = ORDEN[ORDEN.index(s) + (1 if direccion == "peor" else -1)]
            nuevo_indice = indice_con({ind: nueva})
            out.append({
                "id": ind, "titulo": t["titulo"], "unidad": t["unidad"], "valor": v,
                "senal": NOMBRE[s], "direccion": direccion, "pasaria_a": NOMBRE[nueva],
                "umbral": umbral, "distancia": round(distancia, 2),
                "cercania": round(distancia / franja, 2) if franja else None,
                "cerca": franja > 0 and distancia / franja <= CERCA,
                "indice_si_cambia": nuevo_indice,
                "cambio_indice": round(nuevo_indice - pul["indice"], 1),
                "estado_si_cambia": estado_con_memoria(nuevo_indice, pul["estado"]),
            })
    return sorted(out, key=lambda r: (r["cercania"] if r["cercania"] is not None else 99))
