"""Corre TODA la suite de tests de un saque:  python tests/correr_todos.py"""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _bootstrap import correr   # noqa: E402

MODULOS = ["test_fuerza", "test_pid", "test_vision",
           "test_actuador", "test_registro", "test_control_loop"]


def main():
    total = 0
    for nombre in MODULOS:
        print("== %s ==" % nombre)
        mod = importlib.import_module(nombre)
        total += correr(vars(mod))
    print("\n==== TOTAL: %d fallo(s) ====" % total)
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
