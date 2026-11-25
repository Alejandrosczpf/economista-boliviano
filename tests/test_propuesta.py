"""Pruebas de la revisión de propuestas de datos manuales."""
from datetime import date

from pipeline.propuesta import informe, pendientes, revisar_filas

HOY = date(2026, 11, 25)


def _f(serie="embi", fecha="2026-11-20", valor="480", fuente="JP Morgan vía Bloomberg Línea",
       url="https://www.bloomberglinea.com/ejemplo", nota=""):
    return {"serie": serie, "fecha": fecha, "valor": valor, "fuente": fuente, "url": url, "nota": nota}


def _problemas(fila):
    [(_, p)] = revisar_filas([fila], [], HOY)
    return p


def test_fila_correcta_pasa():
    assert _problemas(_f()) == []


def test_sin_fuente_o_sin_enlace_no_pasa():
    assert "falta la fuente" in _problemas(_f(fuente=""))
    assert any("enlace" in p for p in _problemas(_f(url="")))
    assert any("enlace" in p for p in _problemas(_f(url="bloomberglinea.com/x")))


def test_serie_automatica_no_se_carga_a_mano():
    assert any("recolector" in p for p in _problemas(_f(serie="tco", valor="11.9")))


def test_fecha_futura_y_valor_no_numerico():
    assert any("futura" in p for p in _problemas(_f(fecha="2026-12-31")))
    assert any("numérico" in p for p in _problemas(_f(valor="cuatrocientos")))


def test_salto_increible_no_pasa():
    # EMBI de 494 a 4900 en dos semanas: error de tipeo típico
    assert any("salto" in p or "máximo" in p for p in _problemas(_f(valor="4900")))


def test_filas_sin_cambios_no_se_revisan():
    fila = _f()
    assert revisar_filas([fila], [dict(fila)], HOY) == []


def test_informe_marca_cada_fila():
    texto = informe(revisar_filas([_f(), _f(fecha="2026-11-21", fuente="")], [], HOY))
    assert "1 de 2 filas pasan" in texto and "✅" in texto and "❌" in texto


def test_pendientes_solo_series_manuales_y_ordenadas_por_urgencia():
    p = pendientes(HOY)
    assert p and all(x["serie"] not in ("tco", "paralelo", "rin", "inflacion_12m") for x in p)
    venc = [x["vence_en_dias"] for x in p if x["vence_en_dias"] is not None]
    assert venc == sorted(venc)
