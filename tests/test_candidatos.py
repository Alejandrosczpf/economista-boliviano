"""Pruebas de la evaluación de candidatos a nuevos indicadores (sesión 15)."""
from engine.candidatos import (CRISIS, NEUTROS, contexto, evaluar_candidatos, pruebas_historicas_pasan, ruido_senal,
                               senal_candidato)
from pipeline.store import Obs, leer, por_serie

SERIES_REPO = por_serie(leer())


def test_senales_de_los_candidatos():
    assert senal_candidato("cuenta_corriente", -6) == 1.0 and senal_candidato("cuenta_corriente", -3) == 0.5
    assert senal_candidato("cuenta_corriente", 1) == 0.0
    assert senal_candidato("m2_reservas", 16.2) == 1.0 and senal_candidato("m2_reservas", 2) == 0.0


def test_ruido_senal_con_datos_de_ejemplo():
    # rojo en todos los años de crisis y en ninguno de calma: ruido/señal 0
    obs = [Obs("fmi_weo_cuenta_corriente", f"{a}-12-31", -6.0 if a in CRISIS else 1.0) for a in range(1980, 2026)]
    rs = ruido_senal({"fmi_weo_cuenta_corriente": obs}, "cuenta_corriente")
    assert rs["ruido_senal"] == 0.0 and rs["rojos_en_crisis"] == len(CRISIS) and rs["rojos_en_calma"] == 0
    assert rs["anios_calma"] == 46 - len(CRISIS) - len(NEUTROS)


def test_sin_candidatos_las_pruebas_historicas_pasan():
    # misma exigencia que tests/test_sistema.py: la referencia contra la que se compara cada candidato
    assert pruebas_historicas_pasan(SERIES_REPO, ()) == []


def test_entra_solo_si_cumple_las_cuatro_condiciones():
    ev = evaluar_candidatos(SERIES_REPO)
    assert set(ev["candidatos"]) == {"cuenta_corriente", "m2_reservas", "exportaciones_var", "credito_privado_cambio"}
    for r in ev["candidatos"].values():
        assert r["entra"] == all(r["condiciones"].values()) and len(r["condiciones"]) == 4


def test_contexto_solo_trae_los_informativos_que_no_entraron():
    ev = evaluar_candidatos(SERIES_REPO)["candidatos"]
    for c in contexto(SERIES_REPO):
        r = ev[c["id"]]
        assert not r["entra"] and r["ruido_senal"]["ruido_senal"] < 1 and c["semaforo"] in ("verde", "amarillo", "rojo")
