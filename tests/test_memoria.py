"""Pruebas de la memoria del índice: reconstrucción sin datos del futuro y registro en vivo."""
from datetime import date

from engine.memoria import (EN_VIVO, RECONSTRUIDO, actualizar, calcular_dia, cambios_de_estado,
                            conocido_en, suficiente)
from pipeline.store import Obs, cargar_contratos, leer, por_serie

C = cargar_contratos()
SERIES = por_serie(leer())  # los datos reales del repositorio


def test_la_reconstruccion_no_usa_datos_del_futuro():
    dia = date(2026, 10, 1)
    antes = calcular_dia(SERIES, C, dia, RECONSTRUIDO)
    # se agregan datos posteriores a ese día: el resultado de ese día no puede cambiar
    futuro = {k: list(v) for k, v in SERIES.items()}
    futuro["tco"] = futuro["tco"] + [Obs("tco", "2026-10-02", 30.0)]
    futuro["inflacion_12m"] = futuro["inflacion_12m"] + [Obs("inflacion_12m", "2026-10-15", 90.0)]
    assert calcular_dia(futuro, C, dia, RECONSTRUIDO) == antes


def test_un_dato_cuenta_recien_cuando_se_publico():
    # la inflación de octubre (31-oct) la publica el INE ~7 días después
    s = {"inflacion_12m": [Obs("inflacion_12m", "2026-10-31", 7.08)]}
    assert conocido_en(s, C, date(2026, 11, 6)) == {}
    assert len(conocido_en(s, C, date(2026, 11, 7))["inflacion_12m"]) == 1


def test_en_vivo_usa_todo_lo_guardado():
    s = {"inflacion_12m": [Obs("inflacion_12m", "2026-10-31", 7.08)]}
    assert calcular_dia(s, C, date(2026, 11, 1), EN_VIVO)["inflacion_12m"] == 0.5
    assert calcular_dia(s, C, date(2026, 11, 1), RECONSTRUIDO)["inflacion_12m"] == ""


def test_lo_dicho_en_vivo_queda_congelado():
    hoy = date(2026, 7, 3)
    dicho = {"fecha": "2026-07-01", "indice": "12.3", "estado": "calma", "regimen": "flotante",
             "votan": "6", "de": "9", "origen": EN_VIVO}
    filas = actualizar([dicho], SERIES, C, hoy)
    por_dia = {f["fecha"]: f for f in filas}
    assert por_dia["2026-07-01"] is dicho                      # no se recalcula
    assert por_dia["2026-06-30"]["origen"] == RECONSTRUIDO     # el resto, sí
    assert por_dia["2026-07-03"]["origen"] == EN_VIVO          # hoy, en vivo
    assert [f["fecha"] for f in filas] == ["2026-06-29", "2026-06-30", "2026-07-01", "2026-07-02", "2026-07-03"]


def test_dias_con_pocos_votos_no_cuentan_como_cambio_de_estado():
    f = lambda d, e, v: {"fecha": d, "estado": e, "indice": "50", "votan": str(v), "de": "9"}  # noqa: E731
    filas = [f("2026-07-01", "vigilancia", 7), f("2026-07-02", "alerta", 2), f("2026-07-03", "vigilancia", 7)]
    assert not suficiente(filas[1])
    assert cambios_de_estado(filas) == []
