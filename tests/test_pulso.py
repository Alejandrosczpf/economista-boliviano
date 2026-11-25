"""Pruebas de los textos para el lector: resumen, qué cambió en la semana y notas de los gráficos."""
from engine.memoria import resumen_semana
from engine.pulso import notas_graficos, resumen
from pipeline.store import Obs


def _fila(fecha, indice, estado, **senales):
    f = {"fecha": fecha, "indice": str(indice), "estado": estado, "votan": "9", "de": "9"}
    f.update({k: str(v) for k, v in senales.items()})
    return f


def test_semana_detecta_cambios_de_color_y_de_estado():
    filas = [_fila("2026-11-18", 58.0, "vigilancia", brecha=0.0, embi=0.5),
             _fila("2026-11-25", 61.0, "alerta", brecha=1.0, embi=0.5)]
    s = resumen_semana(filas)
    assert (s["estado_antes"], s["estado_hoy"]) == ("vigilancia", "alerta")
    assert s["cambios"] == [{"id": "brecha", "antes": 0.0, "despues": 1.0}]


def test_semana_sin_historia_suficiente():
    assert resumen_semana([_fila("2026-11-25", 50, "vigilancia")]) is None


def _tarjeta(id_, titulo, valor, unidad, semaforo, puntos=0):
    return {"id": id_, "titulo": titulo, "valor": valor, "unidad": unidad, "semaforo": semaforo, "puntos": puntos}


def test_resumen_en_lenguaje_simple_con_los_datos_del_dia():
    pul = {"indice": 47.8, "estado": "vigilancia", "semana": None, "tarjetas": [
        _tarjeta("deficit_fiscal", "Déficit fiscal", 11.0, "% del PIB", "rojo", 13),
        _tarjeta("brecha", "Brecha cambiaria", 1.44, "%", "verde"),
        _tarjeta("embi", "Riesgo país", 494, "puntos básicos", "amarillo", 4),
        _tarjeta("liquidez_rin", "Reservas líquidas", None, "% del total", "gris")]}
    f = resumen(pul)
    assert f[0].startswith("El índice de riesgo está en 48 de 100, en vigilancia")
    assert "el déficit del Estado (11,0 % del PIB)" in f[1] and "el riesgo país (494 puntos)" in f[1]
    assert "la diferencia entre el dólar paralelo y el oficial (1,4 %)" in f[2]
    assert "reservas líquidas" in f[-1]  # lo que no votó se dice, no se esconde


def test_notas_de_graficos_salen_de_los_datos():
    s = {"tco": [Obs("tco", "2026-06-29", 9.73), Obs("tco", "2026-11-25", 11.83)],
         "paralelo": [Obs("paralelo", "2026-11-24", 12.0)],
         "rin": [Obs("rin", "2023-02-28", 725.0), Obs("rin", "2025-10-31", 2483.6), Obs("rin", "2026-10-31", 3964.9)]}
    n = notas_graficos(s)
    assert "1,4 % por encima del oficial" in n["dolar"] and "subió 21,6 %" in n["dolar"]
    assert "3.965 millones" in n["rin"] and "59,6 % más" in n["rin"] and "725 millones" in n["rin"]
    assert "inflacion" not in n  # sin datos no se escribe nota
