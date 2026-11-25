"""Verificador de cifras: ningún informe escrito por IA se publica con un número sin respaldo.

Uso: python -m engine.verificador informes/AAAA-MM-DD.md
     (compara contra data/hechos/AAAA-MM-DD.json, la ficha que escribió el robot ese día)
Sale con código 1 si alguna cifra no pasa.

Reglas para cada número del informe:
1. Debe coincidir con un hecho de la ficha DE ESA FECHA, con el redondeo con que está escrito:
   "47,8" exige 47,75-47,85; "48" admite 47,5-48,5. Se compara el valor absoluto: "cayó 2,8 %" vale para −2,8.
2. La MISMA oración debe nombrar el tema de ese hecho (sus palabras clave). Así, "la inflación llegó a
   59,6 %" no pasa aunque 59,6 sea un dato real: es el cambio anual de las reservas.
3. No cuentan como cifras las fechas ("25 de noviembre", "25 nov", "25/11/2026") ni los años (1800-2100).

Antes (fase 1) se comparaba contra TODOS los datos históricos: casi cualquier número inventado coincidía
con algún valor viejo. Ahora la lista es corta (la ficha del día) y además se exige el tema.
"""
from __future__ import annotations

import os
import re
import sys
import unicodedata

NUM = re.compile(r"(?<![\w/.,-])(-?\d{1,3}(?:\.\d{3})+(?:,\d+)?|-?\d+(?:,\d+)?|-?\d+\.\d+)(?![\w/]|,\d|\.\d)")
MESES = ("enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre|"
         "ene|feb|mar|abr|may|jun|jul|ago|sep|set|oct|nov|dic")
FECHAS = re.compile(rf"\b\d{{1,2}}(?:\s+de)?\s+(?:{MESES})\b|\b\d{{1,2}}[/-]\d{{1,2}}(?:[/-]\d{{2,4}})?\b|"
                    rf"\b\d{{1,2}}-(?:{MESES})\b", re.I)
IGNORAR_ANIOS = range(1800, 2101)


def _sin_tildes(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


def a_float(t: str) -> float:
    t = t.strip()
    if "," in t:                                   # formato boliviano: 3.932,8
        return float(t.replace(".", "").replace(",", "."))
    if re.fullmatch(r"-?\d{1,3}(\.\d{3})+", t):     # 3.932 = miles
        return float(t.replace(".", ""))
    return float(t)


def decimales(t: str) -> int:
    if "," in t:
        return len(t.split(",")[1])
    if re.fullmatch(r"-?\d+\.\d+", t) and not re.fullmatch(r"-?\d{1,3}(\.\d{3})+", t):
        return len(t.split(".")[1])
    return 0


def numeros(texto: str) -> list[tuple[str, float, int]]:
    """Cifras del texto como (crudo, valor, decimales), sin fechas ni años."""
    texto = texto.replace("−", "-")           # signo menos tipográfico
    texto = FECHAS.sub(lambda m: " " * len(m.group(0)), texto)
    out = []
    for m in NUM.finditer(texto):
        crudo = m.group(1)
        v = a_float(crudo)
        if v.is_integer() and int(abs(v)) in IGNORAR_ANIOS and decimales(crudo) == 0:
            continue
        out.append((crudo, v, decimales(crudo)))
    return out


def _oraciones(texto: str) -> list[str]:
    # se corta en . ! ? ; seguidos de espacio, o en salto de línea. El punto de miles ("3.965") no corta,
    # y los dos puntos tampoco: "Inflación: 7,08 %" es una sola afirmación.
    return [o for o in re.split(r"(?<=[.!?;])\s+|\n+", texto) if o.strip()]


def verificar_informe(texto: str, ficha: dict) -> list[tuple[str, str]]:
    """Devuelve [(cifra, problema)] de las cifras que no pasan. Lista vacía = todo verificado."""
    hechos = ficha["hechos"]
    problemas = []
    for oracion in _oraciones(texto):
        normal = _sin_tildes(oracion)
        for crudo, v, dec in numeros(oracion):
            margen = 0.5 * 10 ** (-dec) + 1e-9
            mismos = [h for h in hechos if abs(abs(v) - abs(h["valor"])) <= margen]
            if not mismos:
                problemas.append((crudo, "no coincide con ninguna cifra de la ficha del día"))
            elif not any(any(c in normal for c in h["claves"]) for h in mismos):
                temas = "; ".join(h["texto"] for h in mismos[:3])
                problemas.append((crudo, f"la cifra existe ({temas}) pero la oración no nombra ese tema"))
    return problemas


def _fecha_del_archivo(ruta: str) -> str:
    m = re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(ruta))
    if not m:
        raise SystemExit(f"El nombre del informe debe llevar la fecha AAAA-MM-DD: {ruta}")
    return m.group(1)


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    from engine import hechos as H
    malos_total = 0
    for ruta in argv:
        fecha = _fecha_del_archivo(ruta)
        ficha = H.leer(fecha)
        if ficha is None:
            print(f"❌ {ruta}: no hay ficha de hechos del {fecha} (data/hechos/{fecha}.json): no se puede verificar.")
            malos_total += 1
            continue
        texto = open(ruta, encoding="utf-8").read()
        malos = verificar_informe(texto, ficha)
        n = len(numeros(texto))
        if malos:
            print(f"❌ {ruta}: {len(malos)} de {n} cifras no pasan:")
            for crudo, problema in malos:
                print(f"   - {crudo}: {problema}")
        else:
            print(f"✅ {ruta}: las {n} cifras coinciden con los datos del {fecha}.")
        malos_total += len(malos)
    return 1 if malos_total else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
