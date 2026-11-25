"""Pruebas de los avisos y de su sincronización con issues de GitHub (sin internet)."""
from datetime import date

from pipeline.avisos import Aviso, _cuerpo, actualizar_estado, calcular, sincronizar

LUN, MAR, MIE = date(2026, 11, 23), date(2026, 11, 24), date(2026, 11, 25)


# ---------- Fuentes caídas ----------

def _claves(avisos):
    return [a.clave for a in avisos]


def test_una_falla_aislada_no_avisa_dos_seguidas_si():
    e = actualizar_estado({}, ["fmi"], {"fmi": "403"}, LUN)
    assert "fuente:fmi" not in _claves(calcular(e, [], [], {}))
    e = actualizar_estado(e, ["fmi"], {"fmi": "403"}, MAR)
    assert "fuente:fmi" in _claves(calcular(e, [], [], {}))


def test_dos_corridas_el_mismo_dia_no_cuentan_doble():
    e = actualizar_estado({}, ["fmi"], {"fmi": "403"}, LUN)
    e = actualizar_estado(e, ["fmi"], {"fmi": "403"}, LUN)  # "Run workflow" a mano
    assert e["fmi"]["fallos_seguidos"] == 1


def test_una_lectura_buena_reinicia_la_cuenta():
    e = actualizar_estado({}, ["fmi"], {"fmi": "403"}, LUN)
    e = actualizar_estado(e, ["fmi"], {}, MAR)
    e = actualizar_estado(e, ["fmi"], {"fmi": "403"}, MIE)
    assert e["fmi"]["fallos_seguidos"] == 1


def test_fuente_no_intentada_no_cambia():
    # con --sin-red, las fuentes de internet no se intentan: su cuenta queda igual
    e = actualizar_estado({}, ["fmi"], {"fmi": "403"}, LUN)
    e = actualizar_estado(e, ["manual"], {}, MAR)
    assert e["fmi"]["fallos_seguidos"] == 1


# ---------- Series vencidas o por vencer ----------

def _f(serie, edad, limite, estado=None):
    return {"serie": serie, "nombre": serie, "ultimo": "2026-10-23", "edad_dias": edad,
            "limite_dias": limite, "estado": estado or ("fresco" if edad <= limite else "viejo")}


def test_paralelo_vencido_explica_por_que_no_vota_la_brecha():
    av = calcular({}, [_f("paralelo", 33, 10)], ["brecha"], {"brecha": "último paralelo viejo"})
    assert _claves(av) == ["vencida:paralelo"]  # sin un segundo aviso repetido por la brecha
    # el paralelo llega solo desde paralelo.bo: el aviso apunta al recolector, no a la carga manual
    assert "brecha" in av[0].detalle and "recolector" in av[0].detalle


def test_serie_manual_vencida_indica_donde_cargarla():
    av = calcular({}, [_f("embi", 40, 30)], ["embi"], {})
    assert _claves(av) == ["vencida:embi"] and "entradas.csv" in av[0].detalle


def test_serie_manual_por_vencer_avisa_una_semana_antes():
    assert _claves(calcular({}, [_f("embi", 23, 30)], [], {})) == ["por-vencer:embi"]
    assert calcular({}, [_f("embi", 22, 30)], [], {}) == []  # quedan 8 días: todavía no


def test_serie_automatica_no_avisa_por_vencer():
    # el tipo de cambio llega solo; si se atrasa, lo cubre el aviso de fuente caída o de serie vencida
    assert calcular({}, [_f("tco", 4, 5)], [], {}) == []
    assert _claves(calcular({}, [_f("tco", 9, 5)], ["brecha", "depreciacion_30d"], {})) == ["vencida:tco"]


def test_series_fuera_del_motor_no_avisan():
    # las series del Banco Mundial y el FMI son contexto: no votan en el índice
    assert calcular({}, [_f("wb_inflacion", 900, 800)], [], {}) == []


def test_indicador_sin_voto_por_otra_razon_avisa():
    av = calcular({}, [_f("rin", 10, 70)], ["rin_var_12m"], {"rin_var_12m": "sin dato de hace un año"})
    assert _claves(av) == ["sin-voto:rin_var_12m"] and "hace un año" in av[0].detalle


def test_dato_en_cuarentena_avisa_y_explica_como_aprobarlo():
    q = {"serie": "tco", "fecha": "2026-09-19", "valor": 11.0, "motivo": "salto de 9.9% en 1 días"}
    av = calcular({}, [], [], {}, [q])
    assert _claves(av) == ["cuarentena:tco:2026-09-19"]
    assert "aprobados.csv" in av[0].detalle and "9.9%" in av[0].detalle


# ---------- Vigilancia de las rutinas y de propuestas sin revisar ----------

from datetime import datetime, timezone  # noqa: E402

from pipeline.avisos import avisos_prs, avisos_rutinas, lunes_de_referencia  # noqa: E402

UTC = timezone.utc
BITACORA_DESDE = datetime(2026, 11, 25, tzinfo=UTC)
MARTES = datetime(2026, 12, 1, 13, 17, tzinfo=UTC)       # el robot del martes
LUNES_TEMPRANO = datetime(2026, 11, 30, 13, 17, tzinfo=UTC)  # el robot del lunes, antes de las rutinas


def _c(rutina, cuando):
    return {"body": f"<!-- bitacora: {rutina} {cuando[:10]} -->\nresumen", "created_at": cuando}


def test_lunes_de_referencia():
    assert lunes_de_referencia(MARTES).date() == date(2026, 11, 30)
    assert lunes_de_referencia(LUNES_TEMPRANO).date() == date(2026, 11, 23)  # el de hoy aún no terminó


def test_rutinas_al_dia_no_avisan():
    c = [_c("carga", "2026-11-30T12:06:00Z"), _c("informe", "2026-11-30T14:03:00Z")]
    assert avisos_rutinas(c, MARTES, BITACORA_DESDE) == []


def test_rutina_desactivada_avisa_el_martes():
    # la condición de "listo" de la sesión 11: se desactiva una rutina y el martes llega el aviso
    c = [_c("carga", "2026-11-30T12:06:00Z")]
    assert _claves(avisos_rutinas(c, MARTES, BITACORA_DESDE)) == ["rutina:informe"]


def test_comentario_viejo_no_cuenta():
    c = [_c("carga", "2026-11-25T18:00:00Z"), _c("informe", "2026-11-25T18:10:00Z")]  # de la semana anterior
    assert _claves(avisos_rutinas(c, MARTES, BITACORA_DESDE)) == ["rutina:carga", "rutina:informe"]


def test_bitacora_nueva_no_exige_lunes_anteriores():
    # el miércoles en que se crea la bitácora no se puede exigir el comentario del lunes anterior
    miercoles = datetime(2026, 11, 25, 20, 0, tzinfo=UTC)
    assert avisos_rutinas([], miercoles, BITACORA_DESDE) == []


def test_propuesta_olvidada_avisa_despues_de_7_dias():
    prs = [{"number": 7, "title": "Sesión 10", "created_at": "2026-11-25T19:02:00Z", "html_url": "u"}]
    assert avisos_prs(prs, datetime(2026, 12, 1, tzinfo=UTC)) == []
    assert _claves(avisos_prs(prs, datetime(2026, 12, 3, 20, 0, tzinfo=UTC))) == ["pr-sin-revisar:7"]


# ---------- Sincronización con issues de GitHub ----------

class GitHubFalso:
    def __init__(self, abiertos=()):
        self.issues = {i["number"]: dict(i) for i in abiertos}
        self.llamadas = []

    def __call__(self, metodo, ruta, datos=None):
        self.llamadas.append((metodo, ruta.split("?")[0], datos))
        if metodo == "GET":
            return [i for i in self.issues.values() if i.get("state", "open") == "open"]
        if metodo == "POST" and ruta == "/issues":
            n = max(self.issues, default=0) + 1
            self.issues[n] = {"number": n, "state": "open", **datos}
            return self.issues[n]
        if metodo == "PATCH":
            self.issues[int(ruta.split("/")[2])].update(datos)
        return {}


A = Aviso("vencida:paralelo", "vencida", "Dato vencido: paralelo", "detalle")


def test_abre_un_issue_por_aviso_nuevo():
    gh = GitHubFalso()
    r = sincronizar([A], gh)
    assert r["abiertos"] == ["vencida:paralelo"]
    assert gh.issues[1]["labels"] == ["robot"]


def test_no_duplica_ni_molesta_si_el_aviso_sigue_igual():
    gh = GitHubFalso([{"number": 7, "title": A.titulo, "body": _cuerpo(A, "")}])
    r = sincronizar([A], gh)
    assert r == {"abiertos": [], "actualizados": [], "cerrados": []}


def test_actualiza_en_silencio_si_cambia_el_detalle():
    viejo = Aviso(A.clave, A.tipo, A.titulo, "detalle de ayer")
    gh = GitHubFalso([{"number": 7, "title": A.titulo, "body": _cuerpo(viejo, "")}])
    r = sincronizar([A], gh)
    assert r["actualizados"] == ["vencida:paralelo"] and len(gh.issues) == 1


def test_cierra_el_issue_cuando_se_resuelve():
    gh = GitHubFalso([{"number": 7, "title": A.titulo, "body": _cuerpo(A, "")}])
    r = sincronizar([], gh)
    assert r["cerrados"] == ["vencida:paralelo"] and gh.issues[7]["state"] == "closed"


def test_no_toca_issues_escritos_por_personas():
    gh = GitHubFalso([{"number": 3, "title": "Idea: agregar gráfico", "body": "texto de una persona"}])
    sincronizar([], gh)
    assert gh.issues[3].get("state", "open") == "open"
    assert not [c for c in gh.llamadas if c[1].startswith("/issues/3")]
