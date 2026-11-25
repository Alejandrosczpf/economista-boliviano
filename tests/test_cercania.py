"""Pruebas de "a un paso de cambiar": distancias a los umbrales del motor e índice si cambiara."""
from engine.cercania import calcular
from engine.hechos import construir
from engine.motor import evaluar, senal


def _t(id_, valor, sem, peso, titulo="x", unidad="%"):
    return {"id": id_, "valor": valor, "semaforo": sem, "peso": peso, "titulo": titulo, "unidad": unidad,
            "fecha": "2026-11-25"}


# caso real del 25-nov-2026 (régimen flotante), reducido a tres indicadores
PUL = {"indice": None, "estado": "vigilancia", "generado": "2026-11-25", "regimen": "flotante", "tarjetas": [
    _t("brecha", 1.44, "verde", 1.5, "Brecha cambiaria"),
    _t("embi", 494, "amarillo", 1, "Riesgo país", "puntos básicos"),
    _t("liquidez_rin", 21.57, "rojo", 1, "Reservas líquidas", "% del total"),
    _t("deficit_fiscal", None, "gris", 1.5, "Déficit fiscal")]}
PUL["indice"] = evaluar({"brecha": 1.44, "embi": 494, "liquidez_rin": 21.57}, "flotante").indice


def _r(id_, direccion):
    return next(r for r in calcular(PUL) if r["id"] == id_ and r["direccion"] == direccion)


def test_distancias_a_los_umbrales_del_motor():
    assert (_r("brecha", "peor")["umbral"], _r("brecha", "peor")["distancia"]) == (3, 1.56)
    assert (_r("embi", "mejor")["umbral"], _r("embi", "mejor")["distancia"]) == (400, 94.0)
    assert (_r("liquidez_rin", "mejor")["umbral"], _r("liquidez_rin", "mejor")["distancia"]) == (25, 3.43)


def test_cruzar_el_umbral_cambia_de_verdad_la_senal():
    # coherencia con el motor: en el umbral (o pasándolo) la señal es la que dice "pasaría a"
    assert senal("brecha", 3) == 0.5 and senal("embi", 399) == 0.0 and senal("liquidez_rin", 25.01) == 0.5


def test_indice_si_cambiara_coincide_con_el_motor():
    esperado = evaluar({"brecha": 3, "embi": 494, "liquidez_rin": 21.57}, "flotante").indice
    assert _r("brecha", "peor")["indice_si_cambia"] == esperado


def test_extremos_y_sin_voto():
    ids = {(r["id"], r["direccion"]) for r in calcular(PUL)}
    assert ("brecha", "mejor") not in ids           # ya está en verde
    assert ("liquidez_rin", "peor") not in ids      # ya está en rojo
    assert not any(r["id"] == "deficit_fiscal" for r in calcular(PUL))  # no vota


def test_a_un_paso_es_menos_de_un_cuarto_de_la_franja():
    assert _r("brecha", "peor")["cerca"]             # 1,56 de una franja de 7 = 0,22
    assert not _r("embi", "peor")["cerca"]           # 306 de una franja de 400 = 0,77


def test_la_ficha_trae_los_hechos_a_un_paso():
    pul = dict(PUL, a_un_paso=calcular(PUL), semana=None)
    ids = {h["id"] for h in construir(pul, {})["hechos"]}
    assert {"distancia_brecha_peor", "umbral_brecha_peor", "indice_si_brecha_peor"} <= ids
    assert "distancia_embi_peor" not in ids          # lo que no está cerca no entra
