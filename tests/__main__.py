"""Corre todas las pruebas SIN instalar nada:   python -m tests

Busca cada archivo tests/test_*.py y ejecuta sus funciones test_*.
En GitHub se usa pytest (da más detalle cuando algo falla); aquí basta Python.
"""
import importlib
import os
import sys
import traceback

carpeta = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(carpeta))

ok, fallas = 0, []
for archivo in sorted(f for f in os.listdir(carpeta) if f.startswith("test_") and f.endswith(".py")):
    modulo = importlib.import_module(f"tests.{archivo[:-3]}")
    for nombre in sorted(n for n in dir(modulo) if n.startswith("test_") and callable(getattr(modulo, n))):
        try:
            getattr(modulo, nombre)()
            ok += 1
        except Exception:  # noqa: BLE001
            fallas.append(f"{archivo}::{nombre}")
            print(f"\nFALLA {archivo}::{nombre}")
            traceback.print_exc(limit=3)

print(f"\n{ok} pruebas pasaron, {len(fallas)} fallaron.")
sys.exit(1 if fallas else 0)
