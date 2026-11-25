"""Recolectores. Solo biblioteca estándar de Python (sin dependencias que instalar).

Cada recolector devuelve una lista de Obs. Si una fuente falla, se registra el error
y el resto sigue: una fuente caída nunca detiene al sistema.
"""
from __future__ import annotations

import csv
import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta

from pipeline.store import Obs, RAIZ

# Identificación honesta del programa ante cada servidor.
# SOLO caracteres ASCII: con una tilde ("económico") la API del Banco Mundial responde 403.
AGENTE = "economista-boliviano/0.2 (+https://github.com/Alejandrosczpf/economista-boliviano)"


class FallaParcial(Exception):
    """Una fuente con varios indicadores leyó algunos y falló en otros.
    Lleva los datos que sí se obtuvieron, para no perderlos."""

    def __init__(self, obs: list[Obs], errores: dict[str, str]):
        self.obs = obs
        self.errores = errores
        super().__init__("; ".join(f"{k}: {v}" for k, v in errores.items()))


def _get(url: str, intentos: int = 3, espera: float = 3.0, binario: bool = False):
    ultimo_error = None
    for i in range(intentos):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENTE, "Accept": "application/json, text/html, */*"})
            with urllib.request.urlopen(req, timeout=40) as r:
                cuerpo = r.read()
                return cuerpo if binario else cuerpo.decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            ultimo_error = e
            if 400 <= e.code < 500 and e.code != 429:
                break  # 403/404: el servidor ya respondió que no; reintentar no cambia nada
            time.sleep(espera * (i + 1))
        except Exception as e:  # noqa: BLE001 - red caída, tiempo agotado: reintentar
            ultimo_error = e
            time.sleep(espera * (i + 1))
    raise RuntimeError(f"no se pudo leer {url}: {ultimo_error}")


def _por_indicador(tareas: dict[str, callable]) -> list[Obs]:
    """Corre cada indicador por separado: si uno falla, los demás se conservan."""
    out, errores = [], {}
    for serie, tarea in tareas.items():
        try:
            out += tarea()
        except Exception as e:  # noqa: BLE001
            errores[serie] = str(e)[:200]
    if errores and not out:
        raise RuntimeError("; ".join(f"{k}: {v}" for k, v in errores.items()))
    if errores:
        raise FallaParcial(out, errores)
    return out


# ---------- Entradas manuales (o cargadas por la IA cada semana con su fuente) ----------

def manual(ruta: str | None = None) -> list[Obs]:
    ruta = ruta or f"{RAIZ}/data/manual/entradas.csv"
    with open(ruta, encoding="utf-8", newline="") as f:
        return [Obs(r["serie"], r["fecha"], float(r["valor"]), r["fuente"], r.get("url", ""), r.get("nota", ""))
                for r in csv.DictReader(f) if r.get("serie")]


# ---------- Banco Central de Bolivia: tipo de cambio oficial del día ----------

URL_TCO = "https://www.bcb.gob.bo/bcb_tco_publico_ultima_cotizacion.php"
MESES = {m: i for i, m in enumerate(
    ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
     "septiembre", "octubre", "noviembre", "diciembre"], start=1)}


def parsear_tco(pagina: str) -> Obs:
    """Lee 'Bs 11,83/$us' y la fecha 'VIGENCIA: DEL MIÉRCOLES 25 DE NOVIEMBRE DE 2026'.
    La fecha guardada es el primer día de vigencia (así la reporta la prensa)."""
    texto = html.unescape(re.sub(r"<[^>]+>", " ", pagina))
    texto = re.sub(r"\s+", " ", texto)
    m = re.search(r"Bs\.?\s*(\d{1,3}[.,]\d{1,4})\s*/\s*\$\s*us", texto, re.I)
    if not m:
        raise ValueError("no se encontró la cotización 'Bs x,xx/$us' en la página del BCB")
    valor = float(m.group(1).replace(",", "."))
    # La página escribe "VIGENCIA: MIÉRCOLES 25 DE ..." y a veces "VIGENCIA: DEL MIÉRCOLES 25 ... AL ...".
    # Sin vigencia NO se usa la fecha de corte: es el día anterior y guardaría el dato mal fechado
    # (pasó el 25-nov-2026). Mejor fallar y que llegue el aviso.
    f = re.search(r"VIGENCIA:\s*(?:DEL\s+)?\w+\s+(\d{1,2})\s+DE\s+(\w+)\s+DE\s+(\d{4})", texto, re.I)
    if not f:
        raise ValueError("no se encontró la fecha de vigencia en la página del BCB (¿cambió el formato?)")
    mes = MESES[f.group(2).lower().replace("é", "e")]
    dia = date(int(f.group(3)), mes, int(f.group(1)))
    return Obs("tco", dia.isoformat(), valor, "BCB", URL_TCO, "página de última cotización")


# Historia diaria: tabla "información por períodos". Desde el 27-jun-2026 trae un solo valor
# (el TCO) para cada día, fines de semana incluidos. Antes mostraba compra y venta del tipo fijo.
URL_TCO_PERIODOS = "https://www.bcb.gob.bo/librerias/indicadores/dolar/periodos.php"
INICIO_TCO_UNICO = date(2026, 6, 27)
FUENTE_TCO = "BCB"


def parsear_tco_periodos(pagina: str) -> list[Obs]:
    """Filas como: <td>152</td><td>25 de Noviembre 2026</td><td>Bs 11,83 por 1 US$</td>"""
    out = []
    for fila in re.findall(r"<tr[^>]*>(.*?)</tr>", pagina, re.S | re.I):
        celdas = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", c))).strip()
                  for c in re.findall(r"<td[^>]*>(.*?)</td>", fila, re.S | re.I)]
        if len(celdas) < 3 or not celdas[0].isdigit() or "por 1 US$" not in celdas[2]:
            continue  # encabezados y filas del tipo fijo (compra/venta)
        f = re.match(r"(\d{1,2}) de (\w+) (\d{4})$", celdas[1])
        v = re.search(r"Bs\s*(\d{1,3}[.,]\d{1,4})\s+por 1 US\$", celdas[2])
        if not f or not v:
            raise ValueError(f"fila del BCB con formato desconocido: {celdas}")
        dia = date(int(f.group(3)), MESES[f.group(2).lower()], int(f.group(1)))
        out.append(Obs("tco", dia.isoformat(), float(v.group(1).replace(",", ".")), FUENTE_TCO,
                       URL_TCO_PERIODOS, "tabla por períodos"))
    if not out:
        raise ValueError("la tabla del BCB por períodos no trajo ninguna fila del TCO (¿cambió el formato?)")
    return out


def bcb_tco(hoy: date | None = None) -> list[Obs]:
    """Historia diaria (tabla por períodos) + cotización del día (página de última cotización).
    Si las dos traen el mismo día con valores distintos, se avisa en vez de elegir en silencio."""
    hoy = hoy or date.today()
    desde = max(INICIO_TCO_UNICO, hoy - timedelta(days=400))
    url = (f"{URL_TCO_PERIODOS}?sdd={desde.day}&smm={desde.month}&saa={desde.year}"
           f"&edd={hoy.day}&emm={hoy.month}&eaa={hoy.year}&qlist=1")
    obs, errores = [], {}
    try:
        obs = parsear_tco_periodos(_get(url))
    except Exception as e:  # noqa: BLE001
        errores["tabla_periodos"] = str(e)[:200]
    try:
        del_dia = parsear_tco(_get(URL_TCO))
        previo = next((o for o in obs if o.fecha == del_dia.fecha), None)
        if previo is None:
            obs.append(del_dia)
        elif abs(previo.valor - del_dia.valor) > 1e-9:
            errores["no_coinciden"] = (f"{del_dia.fecha}: tabla {previo.valor} vs página del día {del_dia.valor}; "
                                       "se guarda el de la tabla")
    except Exception as e:  # noqa: BLE001
        errores["pagina_del_dia"] = str(e)[:200]
    if errores and not obs:
        raise RuntimeError("; ".join(f"{k}: {v}" for k, v in errores.items()))
    if errores:
        raise FallaParcial(obs, errores)
    return obs


# ---------- Banco Mundial (API pública, sin clave) ----------

BM = {
    "wb_inflacion": "FP.CPI.TOTL.ZG",
    "wb_pib_crec": "NY.GDP.MKTP.KD.ZG",
    "wb_reservas": "FI.RES.TOTL.CD",
    "wb_exportaciones": "NE.EXP.GNFS.CD",
    "wb_dinero_amplio_pib": "FM.LBL.BMNY.GD.ZS",
}


def parsear_bm(serie: str, cuerpo: str) -> list[Obs]:
    datos = json.loads(cuerpo)
    if not isinstance(datos, list) or len(datos) < 2 or datos[1] is None:
        return []
    out = []
    for r in datos[1]:
        if r.get("value") is None:
            continue
        out.append(Obs(serie, f"{r['date']}-12-31", float(r["value"]), "Banco Mundial",
                       f"https://data.worldbank.org/indicator/{BM[serie]}?locations=BO"))
    return out


def banco_mundial() -> list[Obs]:
    def tarea(serie, codigo):
        url = f"https://api.worldbank.org/v2/country/BOL/indicator/{codigo}?format=json&per_page=200"
        return lambda: parsear_bm(serie, _get(url))
    return _por_indicador({s: tarea(s, c) for s, c in BM.items()})


# ---------- FMI: Perspectivas de la Economía Mundial (WEO; incluye proyecciones) ----------
# Dos puertas al mismo dato:
#  1) api.imf.org (SDMX 3.0, la API oficial nueva): trae solo Bolivia (~5 KB).
#  2) DataMapper (la API vieja): trae todos los países (~120 KB) y bloquea a los
#     servidores de GitHub con 403. Queda como respaldo.

FMI = {"fmi_weo_pib": "NGDP_RPCH",               # crecimiento real
       "fmi_weo_inflacion": "PCPIPCH",          # inflación promedio del año
       "fmi_weo_inflacion_fin": "PCPIEPCH",     # inflación a fin de año (la que mide el motor: 12 meses)
       "fmi_weo_balance": "GGXCNL_NGDP"}        # balance fiscal del gobierno general, % del PIB
URL_FMI_PERFIL = "https://www.imf.org/external/datamapper/profile/BOL"


def _solo_historia(serie: str, pares, hasta_anio: int | None) -> list[Obs]:
    hasta_anio = hasta_anio or date.today().year - 1  # solo historia; las proyecciones van aparte
    return [Obs(serie, f"{a}-12-31", float(v), "FMI WEO", URL_FMI_PERFIL)
            for a, v in pares if v is not None and int(a) <= hasta_anio]


def parsear_fmi(serie: str, cuerpo: str, hasta_anio: int | None = None) -> list[Obs]:
    """Formato DataMapper: {"values": {"NGDP_RPCH": {"BOL": {"2024": 0.7, ...}}}}"""
    datos = json.loads(cuerpo)
    valores = datos.get("values", {}).get(FMI[serie], {}).get("BOL", {})
    return _solo_historia(serie, valores.items(), hasta_anio)


def parsear_fmi_sdmx(serie: str, cuerpo: str, hasta_anio: int | None = None) -> list[Obs]:
    """Formato SDMX-JSON 3.0: las observaciones vienen por posición ("0", "1", ...)
    y los años están en la dimensión TIME_PERIOD de la estructura."""
    datos = json.loads(cuerpo)["data"]
    estructura = datos["structures"][0]["dimensions"]["observation"]
    tiempo = next(d for d in estructura if d["id"] == "TIME_PERIOD")
    anios = [v.get("value") or v.get("id") for v in tiempo["values"]]
    pares = []
    for s in datos["dataSets"][0].get("series", {}).values():
        for pos, valor in s.get("observations", {}).items():
            v = valor[0] if isinstance(valor, list) else valor
            pares.append((anios[int(pos)], None if v in (None, "", "NaN") else float(v)))
    return _solo_historia(serie, pares, hasta_anio)


def _fmi_uno(serie: str, codigo: str) -> list[Obs]:
    url_nueva = (f"https://api.imf.org/external/sdmx/3.0/data/dataflow/IMF.RES/WEO/+/BOL.{codigo}.A"
                 "?dimensionAtObservation=TIME_PERIOD&attributes=dsd&measures=all")
    try:
        return parsear_fmi_sdmx(serie, _get(url_nueva))
    except Exception as e_nueva:  # noqa: BLE001 - probar la puerta vieja
        try:
            return parsear_fmi(serie, _get(f"https://www.imf.org/external/datamapper/api/v1/{codigo}/BOL"))
        except Exception as e_vieja:  # noqa: BLE001
            raise RuntimeError(f"API nueva: {str(e_nueva)[:120]} | DataMapper: {str(e_vieja)[:120]}")


def fmi() -> list[Obs]:
    return _por_indicador({s: (lambda s=s, c=c: _fmi_uno(s, c)) for s, c in FMI.items()})


# ---------- Dólar paralelo/digital: paralelo.bo (API pública, datos CC-BY 4.0) ----------
# Mediana de las mejores ofertas de USDT/BOB en plataformas P2P (Binance, Bybit, Bitget),
# promedio entre compra y venta. Metodología: https://paralelo.bo/metodologia
# Atribución exigida por la licencia: "paralelo.bo (https://paralelo.bo)".

URL_PARALELO = "https://paralelo.bo/api/v1/historical.json"
FUENTE_PARALELO = "paralelo.bo (CC-BY 4.0)"


def parsear_paralelo(cuerpo: str, hoy: date | None = None) -> list[Obs]:
    """Serie diaria completa. El día en curso se omite: su valor todavía cambia durante el día
    y se guarda completo en la corrida siguiente."""
    d = json.loads(cuerpo)
    if d.get("illustrative") is not False:
        raise ValueError("paralelo.bo marcó la serie como ilustrativa (no observada): no se usa")
    esperado = {"currencyPair": "USD/BOB", "market": "parallel", "resolution": "daily"}
    distinto = {k: d.get(k) for k, v in esperado.items() if d.get(k) != v}
    if distinto:
        raise ValueError(f"paralelo.bo cambió el formato de la serie: {distinto}")
    hoy = hoy or date.today()
    out = []
    for p in d.get("points", []):
        dia = date.fromisoformat(p["t"][:10])
        if dia < hoy and p.get("v") is not None:
            out.append(Obs("paralelo", dia.isoformat(), float(p["v"]), FUENTE_PARALELO,
                           "https://paralelo.bo", "mediana P2P USDT/BOB"))
    return out


def paralelo() -> list[Obs]:
    return parsear_paralelo(_get(URL_PARALELO))


# ---------- INE: inflación (comunicados mensuales del IPC, vía la API pública de WordPress del INE) ----------
# Cada mes el INE publica un comunicado: "...variación positiva de 0,85% en septiembre de 2026 ... la variación
# a doce meses se situó en 5,70%". Se leen los comunicados publicados desde mayo de 2026 (datos de abril en
# adelante): antes, la redacción variaba y a veces no traía la cifra a doce meses.
# Controles: el signo mensual sale de las palabras del título ("disminuyó", "negativa"...) y se verifica con la
# inflación acumulada del mes anterior; si no hay signo ni forma de verificarlo, el dato no se guarda.

URL_INE_POSTS = "https://www.ine.gob.bo/index.php/wp-json/wp/v2/posts"
INICIO_IPC_INE = date(2026, 5, 1)  # fecha de PUBLICACIÓN del comunicado
_NUM = r"(-?\d{1,3},\d{1,2})"
_NEG = r"disminu|negativ|descen|baj[oó]|ca[ií]d|decrec|deflac"
_POS = r"positiv|aument|increment|sub[ií]|alza|crec"


def _texto(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def _ultimo_dia(anio: int, mes: int) -> date:
    return (date(anio + (mes == 12), mes % 12 + 1, 1) - timedelta(days=1))


def es_comunicado_ipc(titulo: str) -> bool:
    """Comunicado del IPC con cifra en el título (las fichas sin cifra y los del IPM/IPP no cuentan)."""
    t = titulo.lower()
    return (("consumidor" in t or "ipc" in t) and not any(k in t for k in ("mayor", "productor", "ipm", "ipp"))
            and "%" in t)


def parsear_comunicado_ipc(post: dict) -> dict:
    """Devuelve {anio, mes, doce, mensual, acum (o None), signo_explicito, url}. Falla si falta algo esencial."""
    titulo, cuerpo = _texto(post["title"]["rendered"]), _texto(post["content"]["rendered"])
    m = re.search(r"\b(" + "|".join(MESES) + r")\b(?:\s+(?:de\s+)?(\d{4}))?", titulo, re.I)
    if not m:
        raise ValueError(f"comunicado del INE sin mes en el título: {titulo[:90]}")
    mes = MESES[m.group(1).lower()]
    publicado = date.fromisoformat(post["date"][:10])
    # sin año en el título: el comunicado sale el mes siguiente (diciembre se publica en enero)
    anio = int(m.group(2)) if m.group(2) else publicado.year - (mes > publicado.month)
    doce = re.search(r"(?:variaci[oó]n|inflaci[oó]n)\s+(?:a|de)\s+doce meses\s+(?:se\s+)?"
                     r"(?:situ[oó]|ubic[oó]|alcanz[oó]|lleg[oó]|registr[oó]|fue)\s*(?:en|a|de)?\s*(?:un\s+)?"
                     + _NUM + r"\s*%", cuerpo, re.I)
    if not doce:
        raise ValueError(f"comunicado del INE sin variación a doce meses: {titulo[:90]}")
    mens = re.search(_NUM + r"\s*%", titulo)
    if not mens:
        raise ValueError(f"comunicado del INE sin variación mensual en el título: {titulo[:90]}")
    neg, pos = re.search(_NEG, titulo, re.I), re.search(_POS, titulo, re.I)
    if neg and pos:
        raise ValueError(f"signo ambiguo en el título del INE: {titulo[:90]}")
    acum = re.search(r"acumulad[ao][^.%]{0,80}?" + _NUM + r"\s*%", cuerpo, re.I)
    f = lambda s: float(s.replace(",", "."))  # noqa: E731
    return {"anio": anio, "mes": mes, "doce": f(doce.group(1)), "mensual": -abs(f(mens.group(1))) if neg else abs(f(mens.group(1))),
            "acum": f(acum.group(1)) if acum else None, "signo_explicito": bool(neg or pos), "url": post.get("link", "")}


def verificar_ipc(meses: list[dict]) -> tuple[list[dict], dict[str, str]]:
    """Comprueba cada variación mensual contra la acumulada del mes anterior (mismo año).
    Devuelve (válidos, errores). Sin signo explícito ni comprobación posible, el mes se descarta."""
    por_periodo = {(c["anio"], c["mes"]): c for c in meses}
    validos, errores = [], {}
    for (anio, mes), c in sorted(por_periodo.items()):
        clave = f"{anio}-{mes:02d}"
        if mes == 1 and c["acum"] is not None:
            esperado = c["acum"]
        else:
            prev = por_periodo.get((anio, mes - 1))
            esperado = (100 * ((1 + c["acum"] / 100) / (1 + prev["acum"] / 100) - 1)
                        if prev and prev["acum"] is not None and c["acum"] is not None else None)
        if esperado is None:
            if not c["signo_explicito"]:
                errores[clave] = "sin signo en el título y sin acumulada para comprobarlo"
                continue
        elif abs(esperado - c["mensual"]) > 0.06:
            errores[clave] = f"variación mensual {c['mensual']} no cuadra con la acumulada ({esperado:.2f})"
            continue
        validos.append(c)
    return validos, errores


def ine_ipc(hoy: date | None = None) -> list[Obs]:
    hoy = hoy or date.today()
    desde = max(INICIO_IPC_INE, hoy - timedelta(days=400))
    q = urllib.parse.quote("Índice de Precios al Consumidor")
    posts, pagina = [], 1
    while pagina <= 10:  # lotes de 20: con lotes de 100 el servidor del INE responde 500
        lote = json.loads(_get(f"{URL_INE_POSTS}?search={q}&after={desde.isoformat()}T00:00:00&per_page=20"
                               f"&page={pagina}&_fields=id,date,link,title,content"))
        posts += lote
        if len(lote) < 20:
            break
        pagina += 1
    leidos, errores = [], {}
    for p in posts:
        if not es_comunicado_ipc(_texto(p["title"]["rendered"])):
            continue
        try:
            leidos.append(parsear_comunicado_ipc(p))
        except ValueError as e:
            errores[f"post {p['id']}"] = str(e)
    validos, malos = verificar_ipc(leidos)
    errores.update(malos)
    out = []
    for c in validos:
        dia = _ultimo_dia(c["anio"], c["mes"]).isoformat()
        out.append(Obs("inflacion_12m", dia, c["doce"], "INE", c["url"], "comunicado mensual del IPC"))
        out.append(Obs("inflacion_mensual", dia, c["mensual"], "INE", c["url"], "comunicado mensual del IPC"))
    if errores and not out:
        raise RuntimeError("; ".join(f"{k}: {v}" for k, v in errores.items()))
    if errores:
        raise FallaParcial(out, errores)
    return out


# ---------- BCB: reservas internacionales por componentes (Excel oficial, mensual desde 2002) ----------
# Columnas de la hoja mensual: C = reservas brutas (total), D = oro, E = divisas, J = RIN (netas).
# OJO: la prensa y los informes suelen citar las BRUTAS. Antes de esta fuente, la serie manual "rin"
# mezclaba netas (hasta 2024) con brutas (desde 2025). Aquí cada concepto va en su propia serie.

URL_RIN_XLSX = ("https://www.bcb.gob.bo/webdocs/sector_externo/F%20Reservas%20Internacionales%20Netas/"
                "Reservas_Internacionales_Netas_del_Banco_Central_de_Bolivia_por_componentes.xlsx")
_X = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def leer_xlsx(datos: bytes) -> dict[str, list[dict[str, str]]]:
    """Lee un .xlsx con la biblioteca estándar: {hoja: [ {columna: valor} por fila ]}."""
    import io
    import xml.etree.ElementTree as ET
    import zipfile
    z = zipfile.ZipFile(io.BytesIO(datos))
    comp = []
    if "xl/sharedStrings.xml" in z.namelist():
        comp = ["".join(t.text or "" for t in si.iter(_X + "t"))
                for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall(_X + "si")]
    nombres = [h.get("name") for h in ET.fromstring(z.read("xl/workbook.xml")).find(_X + "sheets")]
    libro = {}
    for i, nombre in enumerate(nombres, 1):
        filas = []
        for fila in ET.fromstring(z.read(f"xl/worksheets/sheet{i}.xml")).find(_X + "sheetData"):
            d = {}
            for c in fila:
                v = c.find(_X + "v")
                if v is not None and v.text is not None:
                    col = "".join(ch for ch in c.get("r") if ch.isalpha())
                    d[col] = comp[int(v.text)] if c.get("t") == "s" else v.text
            filas.append(d)
        libro[nombre] = filas
    return libro


def parsear_rin_xlsx(datos: bytes) -> list[Obs]:
    libro = leer_xlsx(datos)
    hoja = next((f for n, f in libro.items() if "mens" in n.lower()), None)
    if hoja is None:
        raise ValueError(f"el Excel de RIN no tiene hoja mensual: {list(libro)}")
    encabezado = next((f for f in hoja if "TOTAL" in f.get("C", "").upper()), {})
    esperado = {"C": "TOTAL", "D": "ORO", "E": "DIVISAS", "J": "RESERVAS INTERNACIONALES NET"}
    distinto = {k: encabezado.get(k) for k, v in esperado.items() if v not in encabezado.get(k, "").upper()}
    if distinto:
        raise ValueError(f"el Excel de RIN cambió de columnas: {distinto}")
    out = []
    base = date(1899, 12, 30)  # origen de las fechas de Excel
    for f in hoja:
        a = f.get("A", "")
        if not a.replace(".", "", 1).isdigit() or float(a) < 30000:
            continue
        inicio_mes = base + timedelta(days=int(float(a)))
        dia = _ultimo_dia(inicio_mes.year, inicio_mes.month).isoformat()  # "saldos a fin de" mes
        nota = "preliminar" if "(p)" in f.get("B", "") else ""
        for serie, col in (("rin", "J"), ("rin_brutas", "C"), ("rin_divisas", "E")):
            if f.get(col):
                out.append(Obs(serie, dia, round(float(f[col]), 2), "BCB", URL_RIN_XLSX, nota))
    if not out:
        raise ValueError("el Excel de RIN no trajo datos")
    return out


def bcb_rin() -> list[Obs]:
    return parsear_rin_xlsx(_get(URL_RIN_XLSX, binario=True))


# Series que llegan solas. Las demás se cargan a mano (y avisan antes de vencerse).
SERIES_AUTOMATICAS = ({"tco", "paralelo", "inflacion_12m", "inflacion_mensual", "rin", "rin_brutas", "rin_divisas"}
                      | set(BM) | set(FMI))

RECOLECTORES = {"manual": manual, "bcb_tco": bcb_tco, "paralelo": paralelo, "ine_ipc": ine_ipc,
                "bcb_rin": bcb_rin, "banco_mundial": banco_mundial, "fmi": fmi}
