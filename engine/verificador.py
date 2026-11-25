"""Verificador de cifras: antes de mostrar un informe escrito por la IA,
compara cada número que menciona con los datos del sistema.

Uso: python -m engine.verificador informe.md
Sale con código 1 si hay cifras que no coinciden con ningún dato (para frenar la publicación).
"""
from __future__ import annotations

import re
import sys

from pipeline.store import leer, OBS

NUM = re.compile(r"(?<![\w/.-])(-?\d{1,3}(?:\.\d{3})+(?:,\d+)?|-?\d+(?:,\d+)?|-?\d+\.\d+)(?![\w/])")
IGNORAR_AÑOS = range(1800, 2101)


def a_float(t: str) -> float:
    t = t.strip()
    if "," in t:                       # formato boliviano: 3.932,8
        return float(t.replace(".", "").replace(",", "."))
    if re.fullmatch(r"-?\d{1,3}(\.\d{3})+", t):  # 3.932 = miles
        return float(t.replace(".", ""))
    return float(t)


def numeros(texto: str) -> list[tuple[str, float]]:
    out = []
    for m in NUM.finditer(texto):
        v = a_float(m.group(1))
        if v.is_integer() and int(v) in IGNORAR_AÑOS:
            continue
        if abs(v) < 1 and "," not in m.group(1) and "." not in m.group(1):
            continue
        out.append((m.group(1), v))
    return out


def verificar(texto: str, valores_conocidos: list[float], tolerancia: float = 0.006) -> list[str]:
    """Devuelve las cifras que no coinciden (±0,6 %, o ±0,05 absoluto para valores chicos)."""
    malos = []
    for crudo, v in numeros(texto):
        ok = any(abs(v - c) <= max(abs(c) * tolerancia, 0.05) for c in valores_conocidos)
        if not ok:
            malos.append(crudo)
    return malos


def conocidos_desde_datos(extra: list[float] | None = None) -> list[float]:
    vals = [o.valor for o in leer(OBS)]
    return vals + (extra or [])


if __name__ == "__main__":
    texto = open(sys.argv[1], encoding="utf-8").read()
    import json, os  # noqa: E401
    from pipeline.store import RAIZ
    pulso = json.load(open(os.path.join(RAIZ, "site", "pulso.json"), encoding="utf-8"))
    extra = [t["valor"] for t in pulso["tarjetas"] if t["valor"] is not None] + [pulso["indice"]]
    malos = verificar(texto, conocidos_desde_datos(extra))
    if malos:
        print("Cifras sin respaldo en los datos:", ", ".join(malos))
        sys.exit(1)
    print("Todas las cifras coinciden con los datos.")
