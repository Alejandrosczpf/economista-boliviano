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

from collectors.fuentes import RECOLECTORES, FallaParcial
from engine import historia, memoria
from engine import pulso as P
from pipeline import avisos, store, validate

RED = ["bcb_tco", "paralelo", "ine_ipc", "bcb_rin", "banco_mundial", "fmi"]


def main(argv=None) -> dict:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sin-red", action="store_true")
    ap.add_argument("--hoy", type=date.fromisoformat, default=date.today())
    a = ap.parse_args(argv)

    contratos = store.cargar_contratos()
    existentes = store.leer()
    nuevas, errores = [], {}
    intentadas = ["manual"] + ([] if a.sin_red else RED)
    for nombre in intentadas:
        try:
            got = RECOLECTORES[nombre]()
            nuevas += got
            print(f"  {nombre}: {len(got)} datos")
        except FallaParcial as e:  # algunos indicadores sí llegaron: se usan, y se anota el resto
            nuevas += e.obs
            errores[nombre] = ("parcial: " + str(e))[:300]
            print(f"  {nombre}: {len(e.obs)} datos; ERROR PARCIAL {e}")
        except Exception as e:  # noqa: BLE001 - una fuente caída no detiene al sistema
            errores[nombre] = str(e)[:300]
            print(f"  {nombre}: ERROR {errores[nombre]}")

    # Si dos fuentes traen la misma serie y fecha, gana la última recolectada (las automáticas
    # van después de la manual). Sin esto, las dos se pisarían en cada corrida.
    nuevas = store.deduplicar(nuevas)

    # Validar solo lo que es nuevo o cambió
    previas = store.por_serie(existentes)
    idx = {(o.serie, o.fecha): o.valor for o in existentes}
    candidatas = [o for o in nuevas if idx.get((o.serie, o.fecha)) != o.valor]
    aceptadas, rechazadas = validate.revisar(candidatas, previas, contratos, a.hoy, store.cargar_aprobados())
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

    # Memoria: el índice de cada día desde el inicio de la flotación
    filas = memoria.actualizar(memoria.leer(), series, contratos, a.hoy)
    memoria.escribir(filas)
    pul["indice_historia"] = memoria.para_pulso(filas)
    # el estado del día es el de la memoria: con histéresis, bajar de estado exige margen
    pul["estado_sin_histeresis"] = pul["estado"]
    pul["estado"] = filas[-1]["estado"]
    P.guardar(pul)

    # Prueba retrospectiva anual con series oficiales (reports/historia.md)
    with open(os.path.join(store.RAIZ, "reports", "historia.md"), "w", encoding="utf-8") as fh:
        fh.write(historia.informe(historia.prueba_retrospectiva(series, 1980, a.hoy.year - 1)))

    # Avisos: lo que una persona debe saber hoy (en GitHub se vuelven issues)
    estado = avisos.actualizar_estado(avisos.leer_estado(), intentadas, errores, a.hoy)
    avisos.guardar_estado(estado)
    notas = {t["id"]: t.get("nota") for t in pul["tarjetas"]}
    lista = avisos.calcular(estado, fresc, pul["no_votan"], notas, salud["en_cuarentena"])
    avisos.guardar_avisos(lista, a.hoy)

    escribir_informe_salud(salud, pul, lista)
    print(f"Índice {pul['indice']} ({pul['estado']}), régimen {pul['regimen']}; "
          f"{cambios} datos nuevos, {len(rechazadas)} en cuarentena, {len(errores)} fuentes con error, "
          f"{len(lista)} avisos.")
    for av in lista:
        print(f"  aviso: {av.titulo}")
    return pul


def escribir_informe_salud(salud: dict, pul: dict, lista_avisos: list | None = None) -> None:
    viejos = [f for f in salud["frescura"] if f["estado"] != "fresco"]
    lista_avisos = lista_avisos or []
    L = [f"# Informe de salud del sistema — {salud['fecha']}", "",
         f"- Índice de riesgo: **{pul['indice']}** ({pul['estado']}), régimen {pul['regimen']}",
         f"- Datos nuevos o corregidos: {salud['datos_nuevos']}",
         f"- En cuarentena esta corrida: {len(salud['en_cuarentena'])}",
         f"- Fuentes con error: {len(salud['fuentes_con_error'])}",
         f"- Series con dato viejo o sin datos: {len(viejos)} de {len(salud['frescura'])}",
         f"- Indicadores que no votaron por falta de dato fresco: {', '.join(pul['no_votan']) or 'ninguno'}",
         f"- Avisos vigentes: {len(lista_avisos)}", ""]
    if lista_avisos:
        L += ["## Avisos", ""] + [f"- **{av.titulo}**" for av in lista_avisos] + [""]
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
