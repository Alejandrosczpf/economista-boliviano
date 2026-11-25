"""Datos manuales: qué falta cargar y revisión de cada propuesta antes de que entre.

python -m pipeline.propuesta pendientes          # qué series manuales hay que actualizar, y cuándo vencen
python -m pipeline.propuesta revisar <base.csv>  # compara data/manual/entradas.csv con una versión anterior
                                                 # y revisa cada fila nueva o cambiada (lo usa el workflow
                                                 # de pull requests; sale con código 1 si algo no pasa)

Reglas de una fila propuesta:
- serie conocida y que NO llegue sola por un recolector (esas no se cargan a mano);
- fecha válida, no futura; valor numérico;
- fuente y enlace (http/https) obligatorios: sin fuente no hay dato;
- cumple el contrato de su serie (rango posible y salto creíble), salvo que esté aprobada en aprobados.csv.
"""
from __future__ import annotations

import csv
import sys
from datetime import date

from collectors.fuentes import SERIES_AUTOMATICAS
from pipeline import store, validate

CAMPOS = ["serie", "fecha", "valor", "fuente", "url", "nota"]


def leer_csv(ruta: str) -> list[dict]:
    with open(ruta, encoding="utf-8", newline="") as f:
        return [r for r in csv.DictReader(f) if r.get("serie")]


def pendientes(hoy: date | None = None) -> list[dict]:
    """Series que se cargan a mano, con su último dato y cuántos días faltan para que venza."""
    hoy = hoy or date.today()
    contratos = store.cargar_contratos()
    series = store.por_serie(store.leer())
    out = []
    for sid, c in contratos.items():
        if sid in SERIES_AUTOMATICAS:
            continue
        ultimo = series.get(sid, [None])[-1]
        edad = (hoy - ultimo.dia).days if ultimo else None
        quedan = c["frescura_dias"] - edad if edad is not None else None
        out.append({"serie": sid, "nombre": c["nombre"], "fuente_esperada": c["fuente"],
                    "ultimo": ultimo.fecha if ultimo else None, "valor": ultimo.valor if ultimo else None,
                    "edad_dias": edad, "limite_dias": c["frescura_dias"], "vence_en_dias": quedan})
    return sorted(out, key=lambda r: (r["vence_en_dias"] is None, r["vence_en_dias"] if r["vence_en_dias"] is not None else 0))


def revisar_filas(nuevas: list[dict], previas: list[dict], hoy: date | None = None) -> list[tuple[dict, list[str]]]:
    """Revisa las filas agregadas o cambiadas. Devuelve [(fila, [problemas])]; sin problemas = lista vacía."""
    hoy = hoy or date.today()
    contratos = store.cargar_contratos()
    aprobados = store.cargar_aprobados()
    antes = {(r["serie"], r["fecha"]): r for r in previas}
    historia = store.por_serie(store.leer())
    resultado = []
    for r in nuevas:
        if antes.get((r["serie"], r["fecha"])) == r:
            continue  # sin cambios
        prob = []
        if r["serie"] not in contratos:
            prob.append(f"serie desconocida '{r['serie']}'")
        elif r["serie"] in SERIES_AUTOMATICAS:
            prob.append("esta serie llega sola por un recolector: no se carga a mano")
        if not r.get("fuente", "").strip():
            prob.append("falta la fuente")
        if not r.get("url", "").strip().startswith(("http://", "https://")):
            prob.append("falta el enlace (http/https) que respalda el dato")
        try:
            obs = store.Obs(r["serie"], r["fecha"], float(r["valor"]), r.get("fuente", ""), r.get("url", ""), r.get("nota", ""))
        except (ValueError, KeyError):
            prob.append(f"valor no numérico '{r.get('valor')}'")
            obs = None
        if obs and r["serie"] in contratos:
            previas_serie = [o for o in historia.get(r["serie"], []) if o.fecha != r["fecha"]]
            motivo = validate._motivo(obs, contratos, previas_serie, hoy,
                                      revisado=(obs.serie, obs.fecha, round(obs.valor, 6)) in aprobados)
            if motivo:
                prob.append(motivo)
        resultado.append((r, prob))
    return resultado


def informe(revisadas: list[tuple[dict, list[str]]]) -> str:
    if not revisadas:
        return "No hay filas nuevas ni cambiadas en `data/manual/entradas.csv`."
    ok = sum(1 for _, p in revisadas if not p)
    L = [f"### Revisión automática de datos manuales: {ok} de {len(revisadas)} filas pasan", "",
         "| | Serie | Fecha | Valor | Fuente | Resultado |", "|---|---|---|---|---|---|"]
    for r, p in revisadas:
        fuente = f"[{r.get('fuente', '')}]({r['url']})" if r.get("url", "").startswith("http") else r.get("fuente", "")
        L.append(f"| {'✅' if not p else '❌'} | {r['serie']} | {r['fecha']} | {r['valor']} | {fuente} | "
                 f"{'; '.join(p) if p else 'cumple el contrato'} |")
    L += ["", "Una persona debe abrir cada enlace y confirmar que el valor y la fecha coinciden con la fuente "
          "antes de aprobar. La revisión automática comprueba la forma y la credibilidad, no la verdad del dato."]
    return "\n".join(L)


def main(argv: list[str]) -> int:
    # la consola de Windows no siempre usa UTF-8: sin esto, imprimir ✅/❌ falla
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if not argv or argv[0] == "pendientes":
        print("Series manuales, de la más urgente a la menos:\n")
        for p in pendientes():
            v = "sin datos" if p["ultimo"] is None else (
                f"VENCIDA hace {-p['vence_en_dias']} días" if p["vence_en_dias"] < 0 else f"vence en {p['vence_en_dias']} días")
            print(f"- {p['serie']} ({p['nombre']}): último {p['ultimo']} = {p['valor']}; {v}. Fuente esperada: {p['fuente_esperada']}")
        return 0
    if argv[0] == "revisar" and len(argv) >= 2:
        revisadas = revisar_filas(leer_csv(f"{store.RAIZ}/data/manual/entradas.csv"), leer_csv(argv[1]))
        texto = informe(revisadas)
        print(texto)
        if len(argv) >= 3:
            with open(argv[2], "w", encoding="utf-8") as f:
                f.write(texto + "\n")
        return 1 if any(p for _, p in revisadas) else 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
