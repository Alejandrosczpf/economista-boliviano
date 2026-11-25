"""Pruebas de las páginas generadas: la metodología debe reflejar el motor real, y el archivo solo publica lo verificado."""
import re

from engine.motor import PESOS, UMBRALES
from engine.paginas import archivo, metodologia
from pipeline.store import cargar_contratos

C = cargar_contratos()


def _filas_indicadores(html):
    return {m.group(1): m.group(0) for m in re.finditer(r'<tr data-indicador="(\w+)"[^>]*>', html)}


def test_metodologia_refleja_los_umbrales_y_pesos_del_motor():
    filas = _filas_indicadores(metodologia(C))
    assert set(filas) == set(UMBRALES)
    for ind, u in UMBRALES.items():
        f = filas[ind]
        assert f'data-amarillo="{u["amarillo"]}"' in f and f'data-rojo="{u["rojo"]}"' in f
        assert f'data-mayor="{str(u["mayor"]).lower()}"' in f
        for r in PESOS:
            assert f'data-peso-{r}="{PESOS[r].get(ind, 0)}"' in f


def test_metodologia_lista_todas_las_series_con_su_frescura():
    html = metodologia(C)
    for sid, c in C.items():
        fila = re.search(rf'<tr data-serie="{sid}">.*?</tr>', html, re.S)
        assert fila and f'>{c["frescura_dias"]}<' in fila.group(0)


def test_metodologia_resume_la_prueba_historica():
    anual = [{"anio": a, "estado": "alerta"} for a in (1981, 1982, 1983, 2020)] + [{"anio": 2005, "estado": "calma"}]
    assert "1981-1983, 2020" in metodologia(C, anual)


def test_archivo_publica_solo_informes_verificados():
    informes = [{"fecha": "2026-11-30", "ok": False, "cifras": 20, "html": ""},
                {"fecha": "2026-11-25", "ok": True, "cifras": 21, "html": "<p>Texto verificado</p>"}]
    html = archivo([], informes)
    assert "Texto verificado" in html and "las 21 cifras fueron verificadas" in html
    assert "no publicado" in html and "30 nov 2026" in html


def test_archivo_trae_cada_dia_del_indice():
    filas = [{"fecha": "2026-11-24", "indice": "64.7", "estado": "alerta", "votan": "7", "de": "9", "origen": "reconstruido",
              "brecha": "", "embi": "0.5"},
             {"fecha": "2026-11-25", "indice": "47.8", "estado": "vigilancia", "votan": "9", "de": "9", "origen": "en vivo",
              "brecha": "0.0", "embi": "0.5"}]
    html = archivo(filas, [])
    assert '"f": "2026-11-24"' in html and '"f": "2026-11-25"' in html and '"brecha": null' in html
