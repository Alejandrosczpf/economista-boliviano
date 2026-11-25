"""Candidatos a nuevos indicadores, evaluados con la historia desde 1980 ANTES de entrar al índice.

Todo lo que decide (umbrales, períodos de crisis y de calma, regla de entrada) se fijó ANTES de mirar los
resultados (sesión 15, 25-nov-2026), para no acomodar las reglas a los datos. Ver reports/candidatos.md.

Regla de entrada: un candidato entra solo si cumple las cuatro condiciones:
  1. por sí solo avisa más en crisis que en calma: relación ruido/señal < 1 (Kaminsky, Lizondo y Reinhart);
  2. agregado al índice (peso 1), separa mejor los años de crisis de los de calma;
  3. no crea falsas alarmas nuevas (años de calma en "alerta");
  4. las pruebas históricas del índice siguen pasando.
Si no las cumple, se muestra como contexto y no vota.
"""
from __future__ import annotations

from statistics import mean

from engine.historia import _a_dic, indicadores_anio
from engine.motor import PESOS, estado, senal

# Umbrales de la literatura de alerta temprana, fijados antes de ver los resultados.
CANDIDATOS = {
    "cuenta_corriente": dict(titulo="Cuenta corriente", unidad="% del PIB", amarillo=-3, rojo=-5, mayor=False,
                             fuente="FMI WEO (BCA_NGDPD)",
                             por_que="Un déficit externo persistente se financia gastando reservas o con deuda."),
    "m2_reservas": dict(titulo="Dinero (M2) sobre reservas", unidad="veces", amarillo=5, rojo=10, mayor=True,
                        fuente="Banco Mundial (M2 en Bs, tipo de cambio) y RIN brutas del BCB (o reservas del BM antes de 2002)",
                        por_que="Si las reservas cubren menos del 20 % del dinero, no alcanzan a respaldarlo ante una corrida."),
    "exportaciones_var": dict(titulo="Exportaciones: cambio anual", unidad="%", amarillo=0, rojo=-10, mayor=False,
                              fuente="Banco Mundial (NE.EXP.GNFS.CD)",
                              por_que="Menos exportaciones son menos dólares que entran al país."),
    "credito_privado_cambio": dict(titulo="Crédito privado: cambio en un año", unidad="puntos del PIB", amarillo=3,
                                   rojo=5, mayor=True, fuente="Banco Mundial (FS.AST.PRVT.GD.ZS)",
                                   por_que="Los auges de crédito suelen preceder a crisis bancarias."),
}
# No evaluables con la historia: sin serie pública desde 1980.
SIN_HISTORIA = {"depositos_bolivianizacion": "Depósitos y bolivianización (BCB/ASFI): no hay serie pública anual desde 1980; "
                                             "quedan como contexto posible."}

# Períodos, fijados antes de ver los resultados.
CRISIS = set(range(1981, 1986)) | {2001, 2002, 2003} | set(range(2022, 2026))   # crisis y su año previo
NEUTROS = {1980, 1986, 2015, 2016, 2019, 2020, 2021}                             # tensión o shock externo
PESO_CANDIDATO = 1.0


def valores_candidatos(series: dict, anio: int) -> dict:
    v = {}
    cc = _a_dic(series.get("fmi_weo_cuenta_corriente"), anio)
    if cc:
        v["cuenta_corriente"] = cc.valor
    m2, tc = _a_dic(series.get("wb_m2_bs"), anio), _a_dic(series.get("wb_tc_oficial"), anio)
    res = _a_dic(series.get("rin_brutas"), anio) or _a_dic(series.get("wb_reservas"), anio)
    if m2 and tc and res and res.valor > 0:
        reservas_usd = res.valor * (1e6 if res.serie == "rin_brutas" else 1)  # el BCB publica en millones
        v["m2_reservas"] = m2.valor / (reservas_usd * tc.valor)
    ex, ex_ant = _a_dic(series.get("wb_exportaciones"), anio), _a_dic(series.get("wb_exportaciones"), anio - 1)
    if ex and ex_ant and ex_ant.valor > 0:
        v["exportaciones_var"] = 100 * (ex.valor / ex_ant.valor - 1)
    cr, cr_ant = _a_dic(series.get("wb_credito_privado_pib"), anio), _a_dic(series.get("wb_credito_privado_pib"), anio - 1)
    if cr and cr_ant:
        v["credito_privado_cambio"] = cr.valor - cr_ant.valor
    return v


def senal_candidato(cid: str, valor: float | None) -> float | None:
    if valor is None:
        return None
    u = CANDIDATOS[cid]
    if u["mayor"]:
        return 1.0 if valor >= u["rojo"] else 0.5 if valor >= u["amarillo"] else 0.0
    return 1.0 if valor <= u["rojo"] else 0.5 if valor <= u["amarillo"] else 0.0


def indice_anio(series: dict, anio: int, extra: tuple[str, ...] = ()) -> tuple[float | None, str | None]:
    """Índice del régimen fijo, como engine.historia, más los candidatos de 'extra' con peso 1."""
    base, _ = indicadores_anio(series, anio)
    num = den = 0.0
    for ind, w in PESOS["fijo"].items():
        s = senal(ind, base.get(ind))
        if s is not None:
            num, den = num + w * s, den + w
    cand = valores_candidatos(series, anio)
    for cid in extra:
        s = senal_candidato(cid, cand.get(cid))
        if s is not None:
            num, den = num + PESO_CANDIDATO * s, den + PESO_CANDIDATO
    if not den:
        return None, None
    i = round(100 * num / den, 1)
    return i, estado(i)


def _anios(series: dict) -> list[int]:
    return [a for a in range(1980, 2026) if indice_anio(series, a)[0] is not None]


def metricas_indice(series: dict, extra: tuple[str, ...] = ()) -> dict:
    filas = {a: indice_anio(series, a, extra) for a in _anios(series)}
    crisis = [filas[a][0] for a in filas if a in CRISIS]
    calma = [filas[a][0] for a in filas if a not in CRISIS and a not in NEUTROS]
    return {"separacion": round(mean(crisis) - mean(calma), 1),
            "aciertos": sum(1 for a in filas if a in CRISIS and filas[a][1] != "calma"),
            "en_crisis": sum(1 for a in filas if a in CRISIS),
            "falsas_alarmas": sorted(a for a in filas if a not in CRISIS and a not in NEUTROS and filas[a][1] == "alerta"),
            "filas": filas}


def ruido_senal(series: dict, cid: str) -> dict:
    """Relación ruido/señal del candidato solo (señal = rojo): tasa de rojos en calma / tasa de rojos en crisis."""
    crisis_tot = crisis_rojo = calma_tot = calma_rojo = 0
    for a in range(1980, 2026):
        s = senal_candidato(cid, valores_candidatos(series, a).get(cid))
        if s is None or a in NEUTROS:
            continue
        if a in CRISIS:
            crisis_tot, crisis_rojo = crisis_tot + 1, crisis_rojo + (s == 1.0)
        else:
            calma_tot, calma_rojo = calma_tot + 1, calma_rojo + (s == 1.0)
    tasa_buena = crisis_rojo / crisis_tot if crisis_tot else 0
    tasa_falsa = calma_rojo / calma_tot if calma_tot else 0
    return {"anios_crisis": crisis_tot, "rojos_en_crisis": crisis_rojo, "anios_calma": calma_tot,
            "rojos_en_calma": calma_rojo, "ruido_senal": round(tasa_falsa / tasa_buena, 2) if tasa_buena else None}


def pruebas_historicas_pasan(series: dict, extra: tuple[str, ...]) -> list[str]:
    """Las mismas exigencias que tests/test_sistema.py, con el candidato agregado. Devuelve las que fallan."""
    f = {a: indice_anio(series, a, extra) for a in range(1980, 2026)}
    fallas = []
    if any(f[a][1] != "alerta" for a in range(1981, 1986)):
        fallas.append("1981-1985 en alerta")
    if any(f[a][1] != "calma" for a in range(2005, 2015)):
        fallas.append("2005-2014 en calma")
    if f[2016][1] not in ("vigilancia", "alerta"):
        fallas.append("2016 en vigilancia o alerta")
    if f[2023][1] != "alerta" or f[2024][1] != "alerta":
        fallas.append("2023 y 2024 en alerta")
    if f[2022][1] not in ("vigilancia", "alerta") or f[2022][0] <= 50:
        fallas.append("2022 con aviso (más de 50)")
    if not f[2019][0] > f[2014][0] + 30:
        fallas.append("2019 más de 30 puntos sobre 2014")
    return fallas


def evaluar_candidatos(series: dict) -> dict:
    base = metricas_indice(series)
    resultados = {}
    for cid in CANDIDATOS:
        con = metricas_indice(series, (cid,))
        rs = ruido_senal(series, cid)
        fallas = pruebas_historicas_pasan(series, (cid,))
        condiciones = {
            "1. ruido/señal < 1": rs["ruido_senal"] is not None and rs["ruido_senal"] < 1,
            "2. separa mejor crisis de calma": con["separacion"] > base["separacion"],
            "3. sin falsas alarmas nuevas": not (set(con["falsas_alarmas"]) - set(base["falsas_alarmas"])),
            "4. pruebas históricas pasan": not fallas,
        }
        resultados[cid] = {"ruido_senal": rs, "con": {k: v for k, v in con.items() if k != "filas"},
                           "fallas_pruebas": fallas, "condiciones": condiciones, "entra": all(condiciones.values())}
    return {"base": {k: v for k, v in base.items() if k != "filas"}, "candidatos": resultados}


def contexto(series: dict) -> list[dict]:
    """Los candidatos que NO entraron pero son informativos por sí solos (ruido/señal < 1) se muestran como
    contexto: su último valor anual, con su color según sus umbrales. No votan en el índice."""
    ev = evaluar_candidatos(series)["candidatos"]
    out = []
    for cid, r in ev.items():
        rs = r["ruido_senal"]["ruido_senal"]
        if r["entra"] or rs is None or rs >= 1:
            continue
        for anio in range(2030, 1979, -1):
            v = valores_candidatos(series, anio).get(cid)
            if v is not None:
                c = CANDIDATOS[cid]
                s = senal_candidato(cid, v)
                out.append({"id": cid, "titulo": c["titulo"], "unidad": c["unidad"], "anio": anio, "valor": round(v, 2),
                            "semaforo": {0.0: "verde", 0.5: "amarillo", 1.0: "rojo"}[s], "por_que": c["por_que"],
                            "amarillo": c["amarillo"], "rojo": c["rojo"], "mayor": c["mayor"], "fuente": c["fuente"],
                            "ruido_senal": rs})
                break
    return out


def informe(series: dict) -> str:
    ev = evaluar_candidatos(series)
    b = ev["base"]
    L = ["# Candidatos a nuevos indicadores: prueba con la historia (1980-2025)", "",
         "Reglas fijadas **antes** de ver los resultados (sesión 15). Detalle en `engine/candidatos.py`.", "",
         f"- **Crisis y año previo:** {', '.join(str(a) for a in sorted(CRISIS))}",
         f"- **Neutros (no cuentan):** {', '.join(str(a) for a in sorted(NEUTROS))}",
         "- **Calma:** el resto de 1980-2025.",
         f"- **Índice actual (sin candidatos):** separación crisis − calma = {b['separacion']} puntos; "
         f"{b['aciertos']} de {b['en_crisis']} años de crisis fuera de 'calma'; falsas alarmas: {b['falsas_alarmas'] or 'ninguna'}.", "",
         "| Candidato | Umbrales (amarillo / rojo) | Ruido/señal | Separación con él | Falsas alarmas | Pruebas | ¿Entra? |",
         "|---|---|---|---|---|---|---|"]
    for cid, r in ev["candidatos"].items():
        c = CANDIDATOS[cid]
        d = "≥" if c["mayor"] else "≤"
        rs = r["ruido_senal"]
        L.append(f"| {c['titulo']} ({c['unidad']}) | {d} {c['amarillo']} / {d} {c['rojo']} | "
                 f"{rs['ruido_senal'] if rs['ruido_senal'] is not None else 'sin rojos en crisis'} "
                 f"(rojo en {rs['rojos_en_crisis']}/{rs['anios_crisis']} de crisis y {rs['rojos_en_calma']}/{rs['anios_calma']} de calma) | "
                 f"{r['con']['separacion']} | {r['con']['falsas_alarmas'] or 'ninguna'} | "
                 f"{'pasan' if not r['fallas_pruebas'] else 'fallan: ' + '; '.join(r['fallas_pruebas'])} | "
                 f"**{'sí' if r['entra'] else 'no'}** |")
    L += ["", "Condiciones de cada candidato:", ""]
    for cid, r in ev["candidatos"].items():
        L.append(f"- **{CANDIDATOS[cid]['titulo']}:** " + "; ".join(f"{k} {'✅' if ok else '❌'}" for k, ok in r["condiciones"].items()))
    L += ["", "Sin historia suficiente para la prueba:", ""] + [f"- {v}" for v in SIN_HISTORIA.values()]
    L += ["", "**Lectura:** un indicador puede ser bueno solo y empeorar el índice, porque vota en verde en crisis que no",
          "son de su tipo (por ejemplo, M2/reservas fue bajo en la hiperinflación de los 80, cuando la inflación había",
          "destruido el valor del dinero). Cambiar pesos o umbrales después de ver estos resultados sería acomodar las",
          "reglas a los datos: queda como propuesta para la revisión de junio de 2027. Los candidatos con ruido/señal < 1",
          "se muestran en el Pulso como contexto, sin votar.", ""]
    return "\n".join(L)
