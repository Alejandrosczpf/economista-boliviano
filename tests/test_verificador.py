"""Pruebas del verificador de informes: ninguna cifra sin respaldo, y cada cifra con su tema."""
import os
import tempfile
from datetime import date

from engine.pulso import _md_a_html, informe_publicable
from engine.verificador import numeros, verificar_informe

FICHA = {"fecha": "2026-11-25", "estado": "vigilancia", "hechos": [
    {"id": "indice", "valor": 47.8, "texto": "47,8 de 100", "claves": ["indice", "riesgo"]},
    {"id": "escala_indice", "valor": 100, "texto": "100", "claves": ["indice", "100"]},
    {"id": "inflacion_12m", "valor": 7.08, "texto": "7,08 %", "claves": ["inflacion", "precios"]},
    {"id": "rin_var_12m", "valor": 59.64, "texto": "59,64 %", "claves": ["reserva"]},
    {"id": "rin_neta", "valor": 3964.88, "texto": "3.965 millones", "claves": ["reserva"]},
    {"id": "pib_proy", "valor": -2.5, "texto": "-2,50 %", "claves": ["crecimiento", "pib", "economia", "contrac"]},
    {"id": "embi", "valor": 494, "texto": "494 puntos", "claves": ["riesgo pais", "embi"]},
    {"id": "periodo_12_meses", "valor": 12, "texto": "12 meses", "claves": ["12 meses", "doce meses"]},
]}

BUENO = """## Informe de la semana

El índice de riesgo está en 47,8 de 100, en vigilancia, al 25 de noviembre de 2026.
La inflación a 12 meses es de 7,08 %; las reservas netas suben 59,6 % en un año y llegan a 3.965 millones.
Se espera una contracción de la economía de 2,5 % en 2026. El riesgo país está en 494 puntos.
"""


def _problemas(texto):
    return verificar_informe(texto, FICHA)


def test_informe_con_cifras_correctas_pasa():
    assert _problemas(BUENO) == []


def test_cifra_inventada_se_bloquea():
    # 5,7 fue la inflación de septiembre: con la lista vieja (todo el historial) pasaba; ya no
    p = _problemas("La inflación bajó a 5,7 % en el año.")
    assert p and p[0][0] == "5,7" and "ninguna cifra" in p[0][1]


def test_cifra_real_con_otro_tema_se_bloquea():
    # 59,6 es el cambio de las RESERVAS, no la inflación
    p = _problemas("La inflación llegó a 59,6 % en un año.")
    assert p and "no nombra ese tema" in p[0][1]


def test_redondeo_segun_como_esta_escrita_la_cifra():
    assert _problemas("El índice está en 48 de 100.") == []        # 47,8 redondeado a entero
    assert _problemas("El índice está en 47,9 de 100.") != []      # con un decimal debe ser 47,8


def test_periodo_solo_vale_junto_a_su_unidad():
    assert _problemas("La inflación a 12 meses es de 7,08 %.") == []
    assert _problemas("El riesgo país subió 12 puntos.") != []   # 12 suelto no es un dato


def test_fechas_y_anios_no_son_cifras():
    assert [c for c, _, _ in numeros("Al 25 de noviembre de 2026, o el 25/11, o el 3-nov.")] == []


def test_signo_menos_tipografico_y_caidas():
    assert _problemas("El crecimiento esperado es −2,5 %.") == []
    assert _problemas("La economía tendría una contracción de 2,5 %.") == []


def test_miles_con_punto_no_cortan_la_oracion():
    assert _problemas("Las reservas netas llegan a 3.965 millones de dólares.") == []


def test_el_markdown_se_escapa():
    html = _md_a_html("## Título\n\nTexto con **negrita** y <script>alert(1)</script>\n\n- uno\n- dos")
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert "<h3>Título</h3>" in html and "<b>negrita</b>" in html and "<li>uno</li>" in html


def _carpeta_con(texto):
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "2026-11-25.md"), "w", encoding="utf-8") as f:
        f.write(texto)
    return d


def test_la_ficha_de_un_dia_no_se_reescribe():
    import engine.hechos as H
    original = H.CARPETA
    H.CARPETA = tempfile.mkdtemp()
    try:
        H.guardar({"fecha": "2026-11-25", "hechos": [{"id": "x", "valor": 1.0}]})
        H.guardar({"fecha": "2026-11-25", "hechos": [{"id": "x", "valor": 2.0}]})  # segunda corrida del día
        assert H.leer("2026-11-25")["hechos"][0]["valor"] == 1.0
    finally:
        H.CARPETA = original


def test_solo_se_publica_el_informe_verificado(monkeypatch=None):
    import engine.hechos as H
    original = H.leer
    H.leer = lambda fecha: FICHA if str(fecha) == "2026-11-25" else None
    try:
        ok = informe_publicable(_carpeta_con(BUENO), hoy=date(2026, 11, 26))
        assert ok and ok["fecha"] == "2026-11-25" and ok["cifras"] >= 6
        malo = informe_publicable(_carpeta_con(BUENO + "\nLa inflación llegó a 9,9 %.\n"), hoy=date(2026, 11, 26))
        assert malo is None                                    # una sola cifra mala bloquea todo
        viejo = informe_publicable(_carpeta_con(BUENO), hoy=date(2026, 12, 20))
        assert viejo is None                                   # más de 14 días: no se muestra
    finally:
        H.leer = original
