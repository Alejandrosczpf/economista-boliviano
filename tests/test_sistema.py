"""Pruebas del sistema. Correr con: python -m pytest -q"""
from datetime import date
import json
import os

from collectors.fuentes import (AGENTE, FallaParcial, _por_indicador, es_comunicado_ipc, parsear_bm,
                                parsear_comunicado_ipc, parsear_fmi, parsear_fmi_sdmx, parsear_paralelo,
                                parsear_rin_xlsx, parsear_tco, parsear_tco_periodos, verificar_ipc)
from engine.motor import evaluar, evaluar_anio, indicadores_actuales, regimen_en, senal
from engine.verificador import verificar, numeros
from pipeline.store import Obs, cargar_aprobados, cargar_contratos, deduplicar
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


def test_dato_aprobado_se_salta_el_control_de_salto():
    # episodio real de sep-2026: +9,9 % en un día, revisado y aprobado en data/manual/aprobados.csv
    previas = {"tco": [Obs("tco", "2026-09-18", 10.01)]}
    nuevo = Obs("tco", "2026-09-19", 11.0)
    assert not _rev([nuevo], previas)[0]
    ok, malos = revisar([nuevo], previas, C, HOY, aprobados={("tco", "2026-09-19", 11.0)})
    assert ok and not malos


def test_aprobar_no_salta_el_rango_posible():
    ok, malos = revisar([Obs("tco", "2026-11-20", 116.9)], {}, C, HOY, aprobados={("tco", "2026-11-20", 116.9)})
    assert not ok and "mayor al máximo" in malos[0][1]


def test_la_aprobacion_es_para_ese_valor_exacto():
    previas = {"tco": [Obs("tco", "2026-09-18", 10.01)]}
    ok, _ = revisar([Obs("tco", "2026-09-19", 11.5)], previas, C, HOY, aprobados={("tco", "2026-09-19", 11.0)})
    assert not ok  # si la fuente cambia el valor, hay que revisarlo de nuevo


def test_los_aprobados_del_repositorio_se_leen():
    assert ("tco", "2026-09-19", 11.0) in cargar_aprobados()


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


def _tabla_bcb():
    return open(os.path.join(FIX, "bcb_tco_periodos.html"), encoding="utf-8").read()


def test_tabla_del_bcb_trae_cada_dia_y_salta_el_tipo_fijo():
    # respuesta real: 25 y 26-jun son compra/venta del tipo fijo; desde el 27-jun, un solo TCO por día
    obs = parsear_tco_periodos(_tabla_bcb())
    assert [(o.fecha, o.valor) for o in obs] == [
        ("2026-06-27", 9.73), ("2026-06-28", 9.73), ("2026-06-29", 9.73),
        ("2026-06-30", 9.76), ("2026-07-01", 9.76), ("2026-07-02", 9.78)]


def test_tabla_del_bcb_vacia_falla():
    try:
        parsear_tco_periodos("<table><tr><td>Nro</td><td>Fecha</td></tr></table>")
        assert False, "debía fallar"
    except ValueError as e:
        assert "ninguna fila" in str(e)


def _bcb_con(respuestas):
    """Reemplaza _get por respuestas guardadas (o errores) según la URL."""
    import collectors.fuentes as F

    def falso(url, *a, **k):
        r = respuestas["periodos" if "periodos" in url else "dia"]
        if isinstance(r, Exception):
            raise r
        return r
    original, F._get = F._get, falso
    try:
        return F.bcb_tco(hoy=date(2026, 7, 2))
    finally:
        F._get = original


def test_bcb_tabla_y_pagina_del_dia_que_coinciden():
    dia = "<p>Bs 9,78/$us</p><p>VIGENCIA: JUEVES 2 DE JULIO DE 2026</p>"
    obs = _bcb_con({"periodos": _tabla_bcb(), "dia": dia})
    assert len(obs) == 6 and obs[-1].valor == 9.78


def test_bcb_tabla_y_pagina_del_dia_distintas_avisan():
    dia = "<p>Bs 9,99/$us</p><p>VIGENCIA: JUEVES 2 DE JULIO DE 2026</p>"
    try:
        _bcb_con({"periodos": _tabla_bcb(), "dia": dia})
        assert False, "debía avisar la diferencia"
    except FallaParcial as e:
        assert "no_coinciden" in e.errores and e.obs[-1].valor == 9.78  # se guarda el de la tabla


def test_bcb_si_la_tabla_falla_queda_la_pagina_del_dia():
    dia = "<p>Bs 9,78/$us</p><p>VIGENCIA: JUEVES 2 DE JULIO DE 2026</p>"
    try:
        _bcb_con({"periodos": RuntimeError("HTTP 500"), "dia": dia})
        assert False, "debía avisar la falla parcial"
    except FallaParcial as e:
        assert [o.fecha for o in e.obs] == ["2026-07-02"] and "tabla_periodos" in e.errores


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


def _paralelo_fixture():
    return open(os.path.join(FIX, "paralelo_bo_historico.json"), encoding="utf-8").read()


def test_parsea_paralelo_bo_sin_el_dia_en_curso():
    # respuesta real del 25-nov-2026: el punto de hoy es parcial (13:40 UTC) y no se guarda
    obs = parsear_paralelo(_paralelo_fixture(), hoy=date(2026, 11, 25))
    assert [o.fecha for o in obs] == ["2026-11-20", "2026-11-21", "2026-11-22", "2026-11-23", "2026-11-24"]
    assert obs[-1].valor == 12.0 and obs[-1].serie == "paralelo"
    assert "paralelo.bo" in obs[-1].fuente and obs[-1].url == "https://paralelo.bo"  # atribución CC-BY


def test_paralelo_bo_ilustrativo_no_se_usa():
    d = json.loads(_paralelo_fixture())
    d["illustrative"] = True
    try:
        parsear_paralelo(json.dumps(d), hoy=HOY)
        assert False, "debía rechazar una serie ilustrativa"
    except ValueError as e:
        assert "ilustrativa" in str(e)


def test_paralelo_bo_con_otro_formato_falla():
    d = json.loads(_paralelo_fixture())
    d["resolution"] = "hourly"
    try:
        parsear_paralelo(json.dumps(d), hoy=HOY)
        assert False, "debía rechazar un cambio de formato"
    except ValueError as e:
        assert "formato" in str(e)


def test_misma_serie_y_fecha_de_dos_fuentes_gana_la_ultima():
    # la automática va después de la manual: sin esto, se pisarían en cada corrida
    manual = Obs("paralelo", "2026-10-23", 11.93, "prensa")
    auto = Obs("paralelo", "2026-10-23", 11.99, "paralelo.bo")
    assert deduplicar([manual, auto]) == [auto]


def _comunicados_ine():
    return json.load(open(os.path.join(FIX, "ine_ipc_comunicados.json"), encoding="utf-8"))


def _leidos_ine():
    return [parsear_comunicado_ipc(p) for p in _comunicados_ine()
            if es_comunicado_ipc(p["title"]["rendered"])]


def test_ine_lee_los_comunicados_reales_del_ipc():
    validos, errores = verificar_ipc(_leidos_ine())
    assert not errores
    por_mes = {(c["anio"], c["mes"]): (c["doce"], c["mensual"]) for c in validos}
    assert por_mes == {(2026, 4): (14.18, 0.14), (2026, 5): (12.51, 2.13), (2026, 6): (9.23, 2.15),
                       (2026, 7): (4.93, -2.79), (2026, 8): (5.02, 1.10)}


def test_ine_la_ficha_sin_cifra_no_es_un_comunicado():
    titulos = [p["title"]["rendered"] for p in _comunicados_ine()]
    assert "Índice de Precios al Consumidor mayo 2026" in titulos
    assert not es_comunicado_ipc("Índice de Precios al Consumidor mayo 2026")


def test_ine_signo_cambiado_no_cuadra_con_la_acumulada():
    leidos = _leidos_ine()
    julio = next(c for c in leidos if c["mes"] == 7)
    julio["mensual"] = 2.79  # como si se hubiera perdido el "disminuyó"
    _, errores = verificar_ipc(leidos)
    assert "2026-07" in errores and "no cuadra" in errores["2026-07"]


def test_ine_sin_signo_ni_comprobacion_se_descarta():
    # mayo dice "una variación de 2,13%" sin signo: sin abril no hay acumulada para comprobarlo
    mayo = [c for c in _leidos_ine() if c["mes"] == 5]
    validos, errores = verificar_ipc(mayo)
    assert not validos and "2026-05" in errores


def _rin_xlsx():
    return open(os.path.join(FIX, "bcb_rin_componentes.xlsx"), "rb").read()


def test_excel_de_rin_separa_netas_brutas_y_divisas():
    # Excel real del BCB (actualizado el 11-nov-2026). Sep-2026: brutas 3.932,8 (la cifra de los
    # informes y la prensa), netas 3.781,3, divisas 478,1.
    obs = {(o.serie, o.fecha): o for o in parsear_rin_xlsx(_rin_xlsx())}
    v = lambda s, f: round(obs[(s, f)].valor, 1)  # noqa: E731 - el Excel trae más decimales que los informes
    assert v("rin_brutas", "2026-09-30") == 3932.8
    assert v("rin", "2026-09-30") == 3781.3
    assert v("rin_divisas", "2026-09-30") == 478.1
    assert v("rin", "2023-12-31") == 1708.6                  # el mínimo de la crisis de dólares
    assert obs[("rin", "2026-09-30")].nota == "preliminar"   # el BCB marca (p)
    assert min(f for s, f in obs if s == "rin") == "2002-01-31"  # fin de mes, no inicio


def test_excel_de_rin_con_otras_columnas_falla():
    import io
    import zipfile
    origen = zipfile.ZipFile(io.BytesIO(_rin_xlsx()))
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w") as z:
        for n in origen.namelist():
            datos = origen.read(n)
            if n == "xl/sharedStrings.xml":
                # el encabezado es texto con formato: "  Divisas " + "(2)" en superíndice
                datos = datos.replace('<t xml:space="preserve">  Divisas </t>'.encode(),
                                      '<t xml:space="preserve">  Otros </t>'.encode())
            z.writestr(n, datos)
    try:
        parsear_rin_xlsx(salida.getvalue())
        assert False, "debía detectar el cambio de columnas"
    except ValueError as e:
        assert "columnas" in str(e)


def test_liquidez_usa_reservas_brutas():
    s = {"rin_divisas": [Obs("rin_divisas", "2026-09-30", 478.1)],
         "rin_brutas": [Obs("rin_brutas", "2026-09-30", 3932.8)],
         "rin": [Obs("rin", "2026-09-30", 3781.3)]}
    valores, _ = indicadores_actuales(s, C, date(2026, 10, 25))
    assert valores["liquidez_rin"] == round(100 * 478.1 / 3932.8, 2)


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
