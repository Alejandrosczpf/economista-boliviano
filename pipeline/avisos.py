"""Avisos: lo que una persona debe saber hoy, sin abrir el informe de salud.

Cuatro clases de aviso:
- fuente caída: una fuente falló en DIAS_SEGUIDOS corridas (días) seguidas.
- serie vencida: una serie que alimenta el índice tiene un dato más viejo que su límite.
- serie por vencer: una serie cargada a mano vence en AVISO_ANTICIPADO_DIAS días o menos.
- indicador sin voto: un indicador no vota por otra razón (p. ej. falta el dato de hace un año).

En GitHub, cada aviso es un *issue* con la etiqueta "robot", y GitHub avisa por correo.
Si el aviso sigue al día siguiente, el issue se actualiza sin volver a notificar.
Cuando el problema se resuelve, el robot comenta y lo cierra solo.

El estado (fallos seguidos de cada fuente) vive en data/estado_fuentes.json:
el robot lo guarda en git junto con los datos, así lo recuerda de un día para otro.

Uso en GitHub Actions:  python -m pipeline.avisos   (lee reports/avisos.json)
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import date

from collectors.fuentes import SERIES_AUTOMATICAS
from engine.motor import INSUMOS
from pipeline.store import RAIZ

DIAS_SEGUIDOS = 2
AVISO_ANTICIPADO_DIAS = 7
ESTADO = os.path.join(RAIZ, "data", "estado_fuentes.json")
AVISOS = os.path.join(RAIZ, "reports", "avisos.json")
ETIQUETA = "robot"

# Series que llegan solas (recolector automático). Las demás se cargan a mano.
AUTOMATICAS = SERIES_AUTOMATICAS


@dataclass
class Aviso:
    clave: str    # estable de un día a otro: identifica su issue en GitHub
    tipo: str     # fuente_caida | vencida | por_vencer | sin_voto
    titulo: str
    detalle: str


# ---------- Estado de las fuentes ----------

def leer_estado(ruta: str = ESTADO) -> dict:
    if not os.path.exists(ruta):
        return {}
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def guardar_estado(estado: dict, ruta: str = ESTADO) -> None:
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")


def actualizar_estado(estado: dict, intentadas: list[str], errores: dict[str, str], hoy: date) -> dict:
    """Cuenta los días seguidos con falla de cada fuente intentada en esta corrida.
    Una segunda corrida el mismo día no cuenta doble. Una corrida sin error reinicia la cuenta."""
    nuevo = dict(estado)
    dia = hoy.isoformat()
    for fuente in intentadas:
        e = dict(nuevo.get(fuente) or {})
        if fuente in errores:
            if e.get("ultimo_dia_con_falla") != dia:
                e["fallos_seguidos"] = e.get("fallos_seguidos", 0) + 1
                e["ultimo_dia_con_falla"] = dia
            e.setdefault("falla_desde", dia)
            e["ultimo_error"] = errores[fuente]
        else:
            e = {"fallos_seguidos": 0, "ultima_lectura_ok": dia}
        nuevo[fuente] = e
    return nuevo


# ---------- Cálculo de avisos ----------

def _fecha(iso: str) -> str:
    a, m, d = iso.split("-")
    return f"{int(d)}-{['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic'][int(m)-1]}-{a}"


def calcular(estado: dict, frescura: list[dict], no_votan: list[str], notas: dict[str, str]) -> list[Aviso]:
    """estado: de actualizar_estado. frescura: de validate.frescura. no_votan: indicadores sin voto.
    notas: indicador -> explicación del Pulso (por qué no vota)."""
    avisos: list[Aviso] = []

    for fuente, e in sorted(estado.items()):
        n = e.get("fallos_seguidos", 0)
        if n >= DIAS_SEGUIDOS:
            avisos.append(Aviso(
                f"fuente:{fuente}", "fuente_caida", f"Fuente caída: {fuente}",
                f"La fuente **{fuente}** falla desde el {_fecha(e['falla_desde'])} "
                f"({n} corridas seguidas).\n\nÚltimo error:\n\n```\n{e.get('ultimo_error', '')}\n```"))

    del_motor = {s for series in INSUMOS.values() for s in series}
    por_serie = {f["serie"]: f for f in frescura}
    explicado = set()  # indicadores cuyo silencio ya explica un aviso de serie vencida
    for sid in sorted(del_motor):
        f = por_serie.get(sid)
        if not f:
            continue
        afectados = [i for i, ss in INSUMOS.items() if sid in ss and i in no_votan]
        como_cargar = ("Llega sola desde su recolector: revisar si la fuente cambió de formato."
                       if sid in AUTOMATICAS else
                       "Se carga a mano: agregar un dato nuevo, con su fuente y enlace, en `data/manual/entradas.csv`.")
        if f["estado"] == "sin datos":
            avisos.append(Aviso(f"vencida:{sid}", "vencida", f"Serie sin datos: {f['nombre']}",
                                f"No hay ningún dato de **{f['nombre']}**. {como_cargar}"))
            explicado.update(afectados)
        elif f["estado"] == "viejo":
            efecto = (f"Mientras tanto, no vota en el índice: {', '.join(afectados)}." if afectados
                      else "Por ahora el índice no pierde ningún indicador (otra fuente lo cubre).")
            avisos.append(Aviso(
                f"vencida:{sid}", "vencida", f"Dato vencido: {f['nombre']}",
                f"El último dato de **{f['nombre']}** es del {_fecha(f['ultimo'])}: tiene {f['edad_dias']} días "
                f"y el límite es {f['limite_dias']}.\n\n{efecto}\n\n{como_cargar}"))
            explicado.update(afectados)
        elif sid not in AUTOMATICAS:
            quedan = f["limite_dias"] - f["edad_dias"]
            if quedan <= AVISO_ANTICIPADO_DIAS:
                afect = [i for i, ss in INSUMOS.items() if sid in ss]
                avisos.append(Aviso(
                    f"por-vencer:{sid}", "por_vencer", f"Dato por vencer: {f['nombre']}",
                    f"El último dato de **{f['nombre']}** es del {_fecha(f['ultimo'])} y vence en "
                    f"{quedan} día{'s' if quedan != 1 else ''} (límite {f['limite_dias']} días). "
                    f"Cuando venza puede dejar de votar: {', '.join(afect)}.\n\n{como_cargar}"))

    for ind in no_votan:
        if ind not in explicado:
            avisos.append(Aviso(f"sin-voto:{ind}", "sin_voto", f"Indicador sin voto: {ind}",
                                f"El indicador **{ind}** no vota en el índice. Motivo: {notas.get(ind) or 'sin detalle'}."))
    return avisos


def guardar_avisos(avisos: list[Aviso], hoy: date, ruta: str = AVISOS) -> None:
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump({"fecha": hoy.isoformat(), "avisos": [asdict(a) for a in avisos]}, f, ensure_ascii=False, indent=1)


# ---------- Sincronizar con los issues de GitHub ----------

MARCA = "<!-- aviso-robot: {} -->"


def _clave_de(cuerpo: str | None) -> str | None:
    if not cuerpo or "<!-- aviso-robot: " not in cuerpo:
        return None
    return cuerpo.split("<!-- aviso-robot: ", 1)[1].split(" -->", 1)[0]


def _cuerpo(a: Aviso, url_corrida: str) -> str:
    pie = f"\n\n---\nÚltima revisión: [corrida del robot]({url_corrida})." if url_corrida else ""
    return (f"{a.detalle}{pie}\n\nEste aviso lo abrió el robot y lo cerrará solo cuando el problema se resuelva."
            f"\n\n{MARCA.format(a.clave)}")


def sincronizar(avisos: list[Aviso], api, url_corrida: str = "") -> dict:
    """api(metodo, ruta, datos=None) -> respuesta JSON. Se inyecta para poder probarlo sin internet.
    Devuelve un resumen: claves abiertas, actualizadas y cerradas."""
    try:
        api("POST", "/labels", {"name": ETIQUETA, "color": "5319e7",
                                "description": "Avisos automáticos del robot recolector"})
    except Exception:  # noqa: BLE001 - la etiqueta ya existe
        pass
    abiertos = {}
    for issue in api("GET", f"/issues?labels={ETIQUETA}&state=open&per_page=100") or []:
        clave = _clave_de(issue.get("body"))
        if clave and "pull_request" not in issue:
            abiertos[clave] = issue
    resumen = {"abiertos": [], "actualizados": [], "cerrados": []}
    vigentes = {a.clave for a in avisos}
    for a in avisos:
        cuerpo = _cuerpo(a, url_corrida)
        issue = abiertos.get(a.clave)
        if issue is None:
            api("POST", "/issues", {"title": a.titulo, "body": cuerpo, "labels": [ETIQUETA]})
            resumen["abiertos"].append(a.clave)
        elif issue.get("body") != cuerpo or issue.get("title") != a.titulo:
            # editar no envía correo: el issue queda al día sin molestar todos los días
            api("PATCH", f"/issues/{issue['number']}", {"title": a.titulo, "body": cuerpo})
            resumen["actualizados"].append(a.clave)
    for clave, issue in abiertos.items():
        if clave not in vigentes:
            n = issue["number"]
            api("POST", f"/issues/{n}/comments",
                {"body": f"Resuelto: el robot ya no detecta este problema.{' ' + url_corrida if url_corrida else ''}"})
            api("PATCH", f"/issues/{n}", {"state": "closed", "state_reason": "completed"})
            resumen["cerrados"].append(clave)
    return resumen


def api_github(repo: str, token: str):
    def llamar(metodo: str, ruta: str, datos: dict | None = None):
        req = urllib.request.Request(
            f"https://api.github.com/repos/{repo}{ruta}", method=metodo,
            data=json.dumps(datos).encode() if datos is not None else None,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                     "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "economista-boliviano-robot"})
        with urllib.request.urlopen(req, timeout=30) as r:
            cuerpo = r.read()
            return json.loads(cuerpo) if cuerpo else None
    return llamar


def main() -> int:
    repo, token = os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GITHUB_TOKEN")
    if not repo or not token:
        print("Sin GITHUB_REPOSITORY/GITHUB_TOKEN: no se tocan issues (corrida local).")
        return 0
    with open(AVISOS, encoding="utf-8") as f:
        avisos = [Aviso(**a) for a in json.load(f)["avisos"]]
    url = ""
    if os.environ.get("GITHUB_RUN_ID"):
        url = f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/{repo}/actions/runs/{os.environ['GITHUB_RUN_ID']}"
    r = sincronizar(avisos, api_github(repo, token), url)
    print(f"Avisos: {len(avisos)} vigentes; abiertos {r['abiertos']}, actualizados {r['actualizados']}, "
          f"cerrados {r['cerrados']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
