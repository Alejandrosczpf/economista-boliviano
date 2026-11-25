"""Pruebas de la vista previa al compartir y del RSS de informes."""
import os
import tempfile
import xml.etree.ElementTree as ET

from engine.compartir import imagen_og, metas, rss

PUL = {"indice": 47.8, "estado": "vigilancia", "generado": "2026-11-25",
       "resumen": ["El índice de riesgo está en 48 de 100, en vigilancia: hay señales de tensión."]}


def test_vista_previa_dice_el_estado_del_dia():
    m = metas(PUL)
    assert m["titulo"] == "Pulso · Economista Boliviano: índice 48/100, vigilancia (25 nov 2026)"
    assert m["descripcion"].startswith("El índice de riesgo está en 48 de 100")
    assert m["imagen"].endswith("og.png?v=2026-11-25")  # la fecha evita que WhatsApp muestre la imagen de otro día


def test_descripcion_larga_se_corta_sin_partir_palabras():
    largo = dict(PUL, resumen=["palabra " * 60])
    d = metas(largo)["descripcion"]
    assert len(d) <= 200 and d.endswith("…") and not d[:-1].endswith(" ")


def test_rss_solo_trae_informes_verificados_y_es_xml_valido():
    informes = [{"fecha": "2026-11-30", "ok": False, "cifras": 3, "html": ""},
                {"fecha": "2026-11-25", "ok": True, "cifras": 21, "html": "<h3>Título</h3><p>Texto & más</p>"}]
    with tempfile.TemporaryDirectory() as d:
        xml = rss(informes, os.path.join(d, "informes.xml"))
    items = ET.fromstring(xml).findall("./channel/item")
    assert len(items) == 1
    assert items[0].findtext("link").endswith("archivo.html#informe-2026-11-25")
    assert "<h3>Título</h3>" in items[0].findtext("description")  # el HTML va escapado dentro del XML


def test_imagen_de_vista_previa():
    try:
        from PIL import Image
    except ImportError:
        return  # sin Pillow no hay imagen, y el Pulso se publica igual
    with tempfile.TemporaryDirectory() as d:
        ruta = os.path.join(d, "og.png")
        assert imagen_og(PUL, ruta)
        with Image.open(ruta) as im:
            assert im.size == (1200, 630)
