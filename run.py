"""Orquestador: recolectar -> validar -> guardar -> calcular -> publicar -> informe de salud.

python run.py                 # todo, incluidas fuentes en internet
python run.py --sin-red       # solo entradas manuales (para probar sin internet)
python run.py --hoy 2026-11-25
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import date

from collectors.fuentes import RECOLECTORES
from engine import pulso as P
from pipeline import store, validate

RED = ["bcb_tco", "banco_mundial", "fmi"]


def main(argv=None) -> dict:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sin-red", action="store_true")
    ap.add_argument("--hoy", type=date.fromisoformat, default=date.today())
    a = ap.parse_args(argv)

    contratos = store.cargar_contratos()
    existentes = store.leer()
    nuevas, errores = [], {}
    for nombre in ["manual"] + ([] if a.sin_red else RED):
        try:
            got = RECOLECTORES[nombre]()
            nuevas += got
            print(f"  {nombre}: {len(got)} datos")
        except Exception as e:  # noqa: BLE001 - una fuente caída no detiene al sistema
            errores[nombre] = str(e)[:300]
            print(f"  {nombre}: ERROR {errores[nombre]}")

    # Validar solo lo que es nuevo o cambió
    previas = store.por_serie(existentes)
    idx = {(o.serie, o.fecha): o.valor for o in existentes}
    candidatas = [o for o in nuevas if idx.get((o.serie, o.fecha)) != o.valor]
    aceptadas, rechazadas = validate.revisar(candidatas, previas, contratos, a.hoy)
    validate.guardar_cuarentena(rechazadas)
    todas, cambios = store.fusionar(existentes, aceptadas)
    store.escribir(todas)

    series = store.por_serie(todas)
    fresc = validate.frescura(series, contratos, a.hoy)
    salud = {
        "fecha": a.hoy.isoformat(),
        "datos_nuevos": cambios,
        "en_cuarentena": [{"serie": o.serie, "fecha": o.fecha, "valor": o.valor, "motivo": m} for o, m in rechazadas],
        "fuentes_con_error": errores,
        "frescura": fresc,
    }
    pul = P.construir(series, contratos, salud, a.hoy)
    P.guardar(pul)
    escribir_informe_salud(salud, pul)
    print(f"Índice {pul['indice']} ({pul['estado']}), régimen {pul['regimen']}; "
          f"{cambios} datos nuevos, {len(rechazadas)} en cuarentena, {len(errores)} fuentes con error.")
    return pul


def escribir_informe_salud(salud: dict, pul: dict) -> None:
    viejos = [f for f in salud["frescura"] if f["estado"] != "fresco"]
    L = [f"# Informe de salud del sistema — {salud['fecha']}", "",
         f"- Índice de riesgo: **{pul['indice']}** ({pul['estado']}), régimen {pul['regimen']}",
         f"- Datos nuevos o corregidos: {salud['datos_nuevos']}",
         f"- En cuarentena esta corrida: {len(salud['en_cuarentena'])}",
         f"- Fuentes con error: {len(salud['fuentes_con_error'])}",
         f"- Series con dato viejo o sin datos: {len(viejos)} de {len(salud['frescura'])}",
         f"- Indicadores que no votaron por falta de dato fresco: {', '.join(pul['no_votan']) or 'ninguno'}", ""]
    if salud["en_cuarentena"]:
        L += ["## Cuarentena", "", "| Serie | Fecha | Valor | Motivo |", "|---|---|---|---|"]
        L += [f"| {q['serie']} | {q['fecha']} | {q['valor']} | {q['motivo']} |" for q in salud["en_cuarentena"]]
        L.append("")
    if salud["fuentes_con_error"]:
        L += ["## Fuentes con error", ""] + [f"- **{k}**: {v}" for k, v in salud["fuentes_con_error"].items()] + [""]
    L += ["## Frescura de cada serie", "", "| Serie | Último dato | Edad (días) | Límite | Estado |",
          "|---|---|---|---|---|"]
    for f in salud["frescura"]:
        L.append(f"| {f['nombre']} | {f['ultimo'] or '—'} | {f['edad_dias'] if f['edad_dias'] is not None else '—'} "
                 f"| {f['limite_dias']} | {f['estado']} |")
    os.makedirs(os.path.join(store.RAIZ, "reports"), exist_ok=True)
    with open(os.path.join(store.RAIZ, "reports", "salud.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
