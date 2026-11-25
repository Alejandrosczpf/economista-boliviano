"""Páginas públicas que se generan con el propio sistema (no se escriben a mano, así no envejecen):

- site/metodologia.html: "Cómo se calcula". Umbrales, pesos, estados, histéresis y fuentes salen del motor
  y de config/series.json en cada corrida. Una prueba exige que coincidan con el motor.
- site/archivo.html: todos los informes semanales verificados, y "qué decía el índice el día X"
  (desde data/indice.csv).
"""
from __future__ import annotations

import html
import json
import os
import re
from datetime import date

from engine.motor import (ESTADOS, INICIO_FLOTACION, INSUMOS, MARGEN_HISTERESIS, PESOS, UMBRALES, es, fe)
from engine.pulso import EXPLICA, INFORMES, _md_a_html
from pipeline.store import RAIZ

SITIO = os.path.join(RAIZ, "site")
REPO = "https://github.com/Alejandrosczpf/economista-boliviano"
E = html.escape


def _estilos() -> str:
    """Los mismos estilos (y el modo oscuro) del Pulso, tomados de la plantilla."""
    with open(os.path.join(SITIO, "plantilla.html"), encoding="utf-8") as f:
        m = re.search(r"<style>(.*?)</style>", f.read(), re.S)
    return m.group(1) if m else ""


def _pagina(titulo: str, cuerpo: str, script: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(titulo)} · Pulso · Economista Boliviano</title>
<style>{_estilos()}
.doc{{max-width:880px}} .doc h2{{margin-top:30px}} .doc p,.doc li{{line-height:1.6}} .doc table{{margin:8px 0 4px}}
.nav{{font-size:13px;display:flex;gap:16px;flex-wrap:wrap;margin-bottom:6px}}
.doc td.n{{white-space:nowrap}}
</style></head>
<body><div class="wrap doc">
<div class="nav"><a href="index.html">← Pulso de hoy</a><a href="metodologia.html">Cómo se calcula</a><a href="archivo.html">Archivo</a></div>
<h1>{E(titulo)}</h1>
{cuerpo}
<footer>Generada automáticamente el {fe(date.today().isoformat())} a partir del código y los datos del
<a href="{REPO}">repositorio público</a>. Esta es una herramienta de análisis, no una recomendación financiera.</footer>
</div>{script}</body></html>
"""


def _num(v: float) -> str:
    return es(v, 1 if v % 1 else 0)


# ---------- Cómo se calcula ----------

def metodologia(contratos: dict, anual: list[dict] | None = None) -> str:
    regimenes = list(PESOS)  # ["fijo", "flotante"]
    filas = []
    for ind, u in UMBRALES.items():
        x = EXPLICA[ind]
        dir_ = "≥" if u["mayor"] else "≤"
        pesos = " · ".join(f"{r}: {_num(PESOS[r][ind])}" if ind in PESOS[r] else f"{r}: no vota" for r in regimenes)
        series = ", ".join(f"<code>{s}</code>" for s in INSUMOS.get(ind, []))
        filas.append(
            f'<tr data-indicador="{ind}" data-amarillo="{u["amarillo"]}" data-rojo="{u["rojo"]}" '
            f'data-mayor="{str(u["mayor"]).lower()}" '
            + " ".join(f'data-peso-{r}="{PESOS[r].get(ind, 0)}"' for r in regimenes)
            + f'><td><b>{E(x["titulo"])}</b><br><span class="sub">{E(x["que"])}</span></td>'
              f'<td class="n">{dir_} {_num(u["amarillo"])}</td><td class="n">{dir_} {_num(u["rojo"])}</td>'
              f'<td>{pesos}</td><td>{series}</td></tr>')
    estados = " · ".join(f"<b>{n}</b>: de {lo} a {min(hi, 100)}" for lo, hi, n in ESTADOS)
    fuentes = []
    for sid, c in contratos.items():
        fuentes.append(f'<tr data-serie="{sid}"><td><code>{sid}</code><br><span class="sub">{E(c["nombre"])}</span></td>'
                       f'<td>{E(c["fuente"])}</td><td>{E(c["frecuencia"])}</td>'
                       f'<td class="n">{c["frescura_dias"]}</td><td class="n">{c.get("rezago_dias", 0)}</td></tr>')
    alerta = [r["anio"] for r in (anual or []) if r["estado"] == "alerta"]
    rangos = []
    for a in alerta:
        if rangos and a == rangos[-1][1] + 1:
            rangos[-1][1] = a
        else:
            rangos.append([a, a])
    txt_alerta = ", ".join(f"{a}" if a == b else f"{a}-{b}" for a, b in rangos)
    cuerpo = f"""
<p class="sub">Esta página se arma sola con el código del sistema. Si cambia un umbral o una fuente, cambia aquí también.</p>

<h2>Qué es el índice</h2>
<p>Es un <b>índice de alerta temprana</b> de 0 a 100, construido con el método de señales de Kaminsky, Lizondo y
Reinhart (1998, "Leading Indicators of Currency Crises", IMF Staff Papers). Cada indicador emite una señal:
verde (0), amarillo (½) o rojo (1). El índice es el <b>promedio ponderado</b> de las señales, multiplicado por 100.</p>
<ul>
<li><b>Estados:</b> {estados}.</li>
<li><b>Histéresis:</b> subir de estado es inmediato; para bajar, el índice debe quedar {_num(MARGEN_HISTERESIS)}
puntos por debajo del umbral. Así no cambia de estado por oscilaciones de un día.</li>
<li><b>Sin dato no hay voto:</b> un indicador sin dato fresco no vota, y no se inventa ni se arrastra un valor viejo.
Si vota menos de la mitad de los indicadores, la página lo advierte.</li>
<li><b>Dos regímenes:</b> con el dólar fijo (hasta el {fe(INICIO_FLOTACION.isoformat())}) la brecha cambiaria y la
caída de reservas son las alarmas mayores. Con flotación, depreciarse es un ajuste normal, y lo que alarma es la
<i>presión</i> cambiaria: depreciación rápida más pérdida de reservas.</li>
</ul>

<h2>Indicadores, umbrales y pesos</h2>
<details open><summary>Ver la tabla</summary>
<table id="indicadores"><thead><tr><th>Indicador</th><th>Amarillo</th><th>Rojo</th><th>Peso</th><th>Series</th></tr></thead>
<tbody>{''.join(filas)}</tbody></table></details>

<h2>¿Funciona? Prueba con la historia</h2>
<p>El índice se calcula año por año desde 1980 con series oficiales (FMI, BCB, Banco Mundial) y las reglas del tipo
de cambio fijo. Estuvo en <b>alerta</b> en: {txt_alerta or "—"}. Las pruebas automáticas del sistema exigen que
siga reconociendo la hiperinflación (desde 1981), la calma del auge 2005-2014, la vigilancia de 2016 y 2019, el
aviso de 2022 y la crisis de 2023-2024. Si un cambio de fórmula o una revisión de datos rompe eso, no se publica.
El detalle año por año está en el <a href="index.html">Pulso</a> ("¿Habría avisado?").</p>

<h2>Fuentes de cada serie</h2>
<p><b>Frescura:</b> los días que un dato sigue valiendo. <b>Rezago:</b> los días entre la fecha del dato y su
publicación. Al reconstruir el pasado, un dato solo cuenta desde que se publicó, para no usar lo que todavía no se sabía.</p>
<details><summary>Ver las {len(contratos)} series</summary>
<table id="fuentes"><thead><tr><th>Serie</th><th>Fuente</th><th>Frecuencia</th><th>Frescura (días)</th><th>Rezago (días)</th></tr></thead>
<tbody>{''.join(fuentes)}</tbody></table></details>
<p>El dólar paralelo es la mediana diaria del USDT en plataformas P2P, según <a href="https://paralelo.bo">paralelo.bo</a>
(datos bajo licencia CC-BY 4.0); no es el precio en efectivo de las casas de cambio. Las demás fuentes son datos públicos
oficiales (BCB, INE, FMI, Banco Mundial) o, para el riesgo país y las proyecciones, notas de prensa con su enlace.</p>

<h2>Controles de calidad</h2>
<ul>
<li><b>Contratos:</b> cada serie tiene un rango posible y un salto creíble. Un dato que los rompe va a
<b>cuarentena</b> y no entra al cálculo hasta que una persona lo revisa. Si es real, se aprueba con su motivo y su
enlace en <code>data/manual/aprobados.csv</code>.</li>
<li><b>Datos cargados a mano:</b> una rutina de IA propone cada lunes los datos que no tienen recolector, como un
<i>pull request</i> con la cita textual de cada número. Una revisión automática comprueba la fuente, la fecha y el
contrato, y una persona aprueba.</li>
<li><b>Informe semanal:</b> lo redacta una IA usando solo la "ficha de hechos" del día. Un programa comprueba cada
número y que la oración nombre su tema. Una sola cifra sin respaldo bloquea la publicación.</li>
<li><b>Avisos:</b> fuentes caídas, datos vencidos o por vencer, datos en cuarentena, rutinas que no reportaron y
propuestas sin revisar abren un aviso en el repositorio.</li>
</ul>

<h2>Límites conocidos</h2>
<ul>
<li><b>Riesgo país (EMBI):</b> JP Morgan no lo publica abiertamente y llega por la prensa cada 2-3 meses; por eso
vale {contratos.get("embi", {}).get("frescura_dias", "—")} días.</li>
<li><b>Reservas:</b> el índice usa las reservas <b>netas</b>; la prensa suele citar las brutas, que son mayores. La
liquidez se calcula sobre las brutas.</li>
<li><b>Déficit fiscal:</b> la prueba histórica usa el del gobierno general (FMI), algo menor que el del sector público
no financiero que publica el MEFP.</li>
<li><b>Dólar oficial:</b> desde el 26-sep-2026 el BCB lo calcula como mediana ponderada (RD 142/2026), en vez de un
promedio.</li>
<li><b>Historia anterior a 2002:</b> votan 4 de 8 indicadores, porque no hay series de liquidez ni de brecha.</li>
<li>El índice mide señales: <b>no predice</b> ni recomienda qué hacer con el dinero.</li>
</ul>
"""
    return _pagina("Cómo se calcula el índice", cuerpo)


# ---------- Archivo ----------

def informes_verificados(carpeta: str = INFORMES) -> list[dict]:
    """Todos los informes, del más nuevo al más viejo, cada uno verificado contra la ficha de su fecha."""
    from engine import hechos as H
    from engine.verificador import numeros, verificar_informe
    if not os.path.isdir(carpeta):
        return []
    out = []
    for nombre in sorted((f for f in os.listdir(carpeta) if re.fullmatch(r"\d{4}-\d{2}-\d{2}\.md", f)), reverse=True):
        fecha = nombre[:10]
        texto = open(os.path.join(carpeta, nombre), encoding="utf-8").read()
        ficha = H.leer(fecha)
        malos = verificar_informe(texto, ficha) if ficha else [("—", "sin ficha de hechos")]
        out.append({"fecha": fecha, "ok": not malos, "cifras": len(numeros(texto)),
                    "html": _md_a_html(texto) if not malos else ""})
    return out


def archivo(filas_indice: list[dict], informes: list[dict]) -> str:
    bloques = []
    for inf in informes:
        if inf["ok"]:
            bloques.append(f'<details class="card" style="margin:8px 0"><summary><b>Informe del {fe(inf["fecha"])}</b> · '
                           f'las {inf["cifras"]} cifras fueron verificadas contra los datos de ese día</summary>{inf["html"]}</details>')
        else:
            bloques.append(f'<div class="card" style="margin:8px 0">Informe del {fe(inf["fecha"])}: <b>no publicado</b>, '
                           'porque no pasó la verificación de cifras.</div>')
    indicadores = [i for i in PESOS["flotante"]]
    datos = [{"f": r["fecha"], "i": float(r["indice"]), "e": r["estado"], "v": int(r["votan"]), "d": int(r["de"]),
              "o": r["origen"], "s": {k: (None if r.get(k) in ("", None) else float(r[k])) for k in indicadores}}
             for r in sorted(filas_indice, key=lambda r: r["fecha"])]
    titulos = {k: EXPLICA[k]["titulo"] for k in indicadores}
    cuerpo = f"""
<h2>Informes semanales</h2>
{''.join(bloques) or '<p class="sub">Todavía no hay informes publicados.</p>'}

<h2>¿Qué decía el índice el día…?</h2>
<p class="sub">Elija una fecha desde el inicio de la flotación. Hasta que empezó el robot, los días son una
reconstrucción con los datos que ya se habían publicado ese día; después, lo que el robot calculó esa mañana.</p>
<div class="card"><label>Fecha: <input type="date" id="dia"></label>
<div id="resultado" style="margin-top:12px"></div></div>
"""
    script = f"""<script id="datos" type="application/json">{json.dumps({"filas": datos, "titulos": titulos}, ensure_ascii=False).replace("</", "<\\/")}</script>
<script>
(function(){{
const D = JSON.parse(document.getElementById('datos').textContent), F = D.filas;
const MES=['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic'];
const fecha = s => {{const [a,m,d]=s.split('-'); return `${{+d}} ${{MES[m-1]}} ${{a}}`;}};
const nf = (v,d=1) => new Intl.NumberFormat('es-BO',{{minimumFractionDigits:d,maximumFractionDigits:d}}).format(v);
const SEM = s => s==null ? '⚪ sin dato' : s===0 ? '🟢 verde' : s===0.5 ? '🟡 amarillo' : '🔴 rojo';
const inp = document.getElementById('dia'), out = document.getElementById('resultado');
if(!F.length){{ out.textContent='Sin datos.'; return; }}
inp.min = F[0].f; inp.max = F[F.length-1].f; inp.value = F[F.length-1].f;
function mostrar(){{
  const r = F.find(x=>x.f===inp.value) || F.filter(x=>x.f<=inp.value).pop();
  if(!r){{ out.textContent='No hay datos para esa fecha.'; return; }}
  const filas = Object.entries(D.titulos).map(([k,t])=>`<tr><td>${{t}}</td><td>${{SEM(r.s[k])}}</td></tr>`).join('');
  out.innerHTML = `<div style="font-size:20px;font-weight:600">${{fecha(r.f)}}: índice ${{nf(r.i)}}, ${{r.e}}</div>
    <div class="sub">Votaron ${{r.v}} de ${{r.d}} indicadores · ${{r.o==='en vivo'?'calculado ese día por el robot':'reconstruido con los datos de entonces'}}</div>
    <table style="margin-top:8px"><thead><tr><th>Indicador</th><th>Señal ese día</th></tr></thead><tbody>${{filas}}</tbody></table>`;
}}
inp.addEventListener('change', mostrar); mostrar();
}})();
</script>"""
    return _pagina("Archivo", cuerpo, script)


def guardar(contratos: dict, filas_indice: list[dict], anual: list[dict]) -> None:
    for nombre, contenido in (("metodologia.html", metodologia(contratos, anual)),
                              ("archivo.html", archivo(filas_indice, informes_verificados()))):
        with open(os.path.join(SITIO, nombre), "w", encoding="utf-8") as f:
            f.write(contenido)
