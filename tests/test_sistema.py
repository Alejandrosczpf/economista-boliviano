"""Pruebas del sistema. Correr con: python -m pytest -q"""
from datetime import date
import json
import os

from collectors.fuentes import (AGENTE, FallaParcial, _por_indicador, parsear_bm, parsear_fmi,
                                parsear_fmi_sdmx, parsear_tco)
from engine.motor import evaluar, evaluar_anio, regimen_en, senal
from engine.verificador import verificar, numeros
from pipeline.store import Obs, cargar_contratos
from pipeline.validate import revisar

C = cargar_contratos()
HOY = date(2026, 11, 25)
FIX = os.path.join(os.path.dirname(__file__), "fixtures")


# ---------- Contratos y cuarentena ----------

def _rev(nuevas, previas=None):
    return revisar(nuevas, previas or {}, C, HOY)


def test_rechaza_fuera_de_rango():
    ok, malos = _rev([Obs("tco", "2026-11-20", 116.9)])  # error típico de coma
    assert not ok and "mayor al máximo" in malos[0][1]


def test_rechaza_salto_increible_en_un_dia():
    previas = {"tco": [Obs("tco", "2026-11-19", 11.8)]}
    ok, malos = _rev([Obs("tco", "2026-11-20", 15.9)], previas)
    assert not ok and "salto" in malos[0][1]


def test_acepta_salto_creible_con_tiempo():
    # +11,5 % en 21 días al inicio de la flotación: real, no error
    previas = {"tco": [Obs("tco", "2026-06-29", 9.73)]}
    ok, malos = _rev([Obs("tco", "2026-07-20", 10.85)], previas)
    assert ok and not malos


def test_quiebre_de_regimen_permitido():
    previas = {"tco": [Obs("tco", "2026-06-26", 6.96)]}
    ok, _ = _rev([Obs("tco", "2026-06-29", 9.73)], previas)
    assert ok  # 2026-06-29 está declarado como quiebre conocido


def test_rechaza_fecha_futura_y_serie_desconocida():
    _, malos = _rev([Obs("tco", "2027-01-01", 11.8), Obs("inventada", "2026-11-01", 1)])
    assert len(malos) == 2


def test_un_rechazo_no_bloquea_los_siguientes():
    previas = {"tco": [Obs("tco", "2026-11-18", 11.8)]}
    ok, malos = _rev([Obs("tco", "2026-11-19", 1.18), Obs("tco", "2026-11-20", 11.82)], previas)
    assert [o.valor for o in ok] == [11.82] and len(malos) == 1


# ---------- Motor: pruebas de regresión histórica ----------
# Ningún cambio de fórmula se acepta si el sistema deja de reconocer estas crisis.

def test_hiperinflacion_1985_es_alerta():
    assert evaluar_anio(1985).estado == "alerta"


def test_auge_2014_es_calma():
    assert evaluar_anio(2014).estado == "calma"


def test_caida_del_gas_2016_enciende_vigilancia():
    assert evaluar_anio(2016).estado in ("vigilancia", "alerta")


def test_crisis_de_dolares_2023_y_2024_son_alerta():
    assert evaluar_anio(2023).estado == "alerta"
    assert evaluar_anio(2024).estado == "alerta"


def test_2019_ya_mostraba_vigilancia_antes_de_la_crisis():
    assert evaluar_anio(2019).indice > evaluar_anio(2014).indice + 30


def test_regimen_cambia_el_29_de_junio_de_2026():
    assert regimen_en(date(2026, 6, 28)) == "fijo"
    assert regimen_en(date(2026, 6, 29)) == "flotante"


def test_en_flotacion_depreciarse_poco_no_es_alarma():
    assert senal("depreciacion_30d", 1.0) == 0.0
    assert senal("depreciacion_30d", 6.0) == 1.0


def test_sin_dato_no_vota_ni_se_inventa():
    r = evaluar({"inflacion_12m": 20}, "flotante")
    assert r.indice == 100 and "brecha" in r.no_votan


def test_reservas_que_crecen_no_suman_riesgo():
    assert senal("rin_var_12m", 21.9) == 0.0
    assert senal("rin_var_12m", -20) == 1.0


# ---------- Recolectores (con páginas guardadas, sin internet) ----------

def test_parsea_pagina_del_bcb():
    pagina = open(os.path.join(FIX, "bcb_tco.html"), encoding="utf-8").read()
    o = parsear_tco(pagina)
    assert (o.serie, o.fecha, o.valor) == ("tco", "2026-11-25", 11.83)


def test_bcb_sin_del_usa_la_vigencia_no_la_fecha_de_corte():
    # formato real del 25-nov-2026: antes se guardaba con la fecha de corte (un día antes)
    pagina = open(os.path.join(FIX, "bcb_tco_2026-11-25.html"), encoding="utf-8").read()
    assert parsear_tco(pagina).fecha == "2026-11-25"


def test_bcb_sin_vigencia_falla_en_vez_de_adivinar():
    pagina = "<p>Bs 11,83/$us</p><p>FECHA DE CORTE: MARTES 24 DE NOVIEMBRE DE 2026</p>"
    try:
        parsear_tco(pagina)
        assert False, "debía fallar"
    except ValueError as e:
        assert "vigencia" in str(e)


def test_parsea_banco_mundial():
    cuerpo = json.dumps([{"page": 1}, [{"date": "2024", "value": 5.1}, {"date": "2023", "value": None}]])
    obs = parsear_bm("wb_inflacion", cuerpo)
    assert len(obs) == 1 and obs[0].fecha == "2024-12-31"


def test_fmi_separa_historia_de_proyecciones():
    cuerpo = json.dumps({"values": {"NGDP_RPCH": {"BOL": {"2024": 0.7, "2026": -3.0}}}})
    obs = parsear_fmi("fmi_weo_pib", cuerpo, hasta_anio=2025)
    assert [o.fecha for o in obs] == ["2024-12-31"]


def test_parsea_api_nueva_del_fmi():
    # respuesta real de api.imf.org (WEO oct-2026), recortada a 2020-2027
    cuerpo = open(os.path.join(FIX, "fmi_sdmx_bol_pib.json"), encoding="utf-8").read()
    obs = parsear_fmi_sdmx("fmi_weo_pib", cuerpo, hasta_anio=2025)
    assert [o.fecha[:4] for o in obs] == [str(a) for a in range(2020, 2026)]
    assert round(obs[0].valor, 1) == -12.7  # pandemia 2020
    assert all(o.fuente == "FMI WEO" for o in obs)


def test_identificacion_solo_ascii():
    # con una tilde en el User-Agent, el Banco Mundial responde 403 (pasó en la 1.ª corrida)
    assert AGENTE.isascii()


def test_un_indicador_caido_no_borra_los_demas():
    def bien():
        return [Obs("wb_inflacion", "2024-12-31", 5.1)]

    def mal():
        raise RuntimeError("HTTP Error 403")

    try:
        _por_indicador({"wb_inflacion": bien, "wb_pib_crec": mal})
        assert False, "debía avisar la falla parcial"
    except FallaParcial as e:
        assert len(e.obs) == 1 and "wb_pib_crec" in e.errores


# ---------- Verificador de cifras ----------

def test_verificador_detecta_cifra_inventada():
    texto = "Las reservas suben a 3.932,8 millones y el dólar oficial está en Bs 11,83; el riesgo país en 610 puntos."
    assert verificar(texto, [3932.8, 11.83, 494]) == ["610"]


def test_verificador_ignora_anios():
    assert numeros("En 2026, como en 1985") == []
