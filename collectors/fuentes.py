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
import urllib.request
from datetime import date

from pipeline.store import Obs, RAIZ

AGENTE = "economista-boliviano/0.1 (+monitor económico sin fines de lucro)"


def _get(url: str, intentos: int = 3, espera: float = 3.0) -> str:
    ultimo_error = None
    for i in range(intentos):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENTE})
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read().decode("utf-8", errors="replace")
        except Exception as e:  # noqa: BLE001 - registrar y reintentar
            ultimo_error = e
            time.sleep(espera * (i + 1))
    raise RuntimeError(f"no se pudo leer {url}: {ultimo_error}")


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
    f = re.search(r"VIGENCIA:\s*DEL\s+\w+\s+(\d{1,2})\s+DE\s+(\w+)\s+DE\s+(\d{4})", texto, re.I)
    if not f:
        f = re.search(r"FECHA DE CORTE:\s*\w+\s+(\d{1,2})\s+DE\s+(\w+)\s+DE\s+(\d{4})", texto, re.I)
    if not f:
        raise ValueError("no se encontró la fecha de vigencia en la página del BCB")
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
    out = []
    for serie, codigo in BM.items():
        url = f"https://api.worldbank.org/v2/country/BOL/indicator/{codigo}?format=json&per_page=200"
        out += parsear_bm(serie, _get(url))
    return out


# ---------- FMI DataMapper (WEO; incluye proyecciones) ----------

FMI = {"fmi_weo_pib": "NGDP_RPCH", "fmi_weo_inflacion": "PCPIPCH"}


def parsear_fmi(serie: str, cuerpo: str, hasta_anio: int | None = None) -> list[Obs]:
    datos = json.loads(cuerpo)
    valores = datos.get("values", {}).get(FMI[serie], {}).get("BOL", {})
    hasta_anio = hasta_anio or date.today().year - 1  # solo historia; las proyecciones van aparte
    return [Obs(serie, f"{a}-12-31", float(v), "FMI WEO", "https://www.imf.org/external/datamapper/profile/BOL")
            for a, v in valores.items() if v is not None and int(a) <= hasta_anio]


def fmi() -> list[Obs]:
    out = []
    for serie, codigo in FMI.items():
        out += parsear_fmi(serie, _get(f"https://www.imf.org/external/datamapper/api/v1/{codigo}/BOL"))
    return out


RECOLECTORES = {"manual": manual, "bcb_tco": bcb_tco, "banco_mundial": banco_mundial, "fmi": fmi}
