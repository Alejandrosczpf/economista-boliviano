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
import urllib.request
from datetime import date

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


def _get(url: str, intentos: int = 3, espera: float = 3.0) -> str:
    ultimo_error = None
    for i in range(intentos):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENTE, "Accept": "application/json, text/html"})
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read().decode("utf-8", errors="replace")
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
    return Obs("tco", dia.isoformat(), valor, "BCB", URL_TCO, "recolector automático")


def bcb_tco() -> list[Obs]:
    return [parsear_tco(_get(URL_TCO))]


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

FMI = {"fmi_weo_pib": "NGDP_RPCH", "fmi_weo_inflacion": "PCPIPCH"}
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


RECOLECTORES = {"manual": manual, "bcb_tco": bcb_tco, "banco_mundial": banco_mundial, "fmi": fmi}
