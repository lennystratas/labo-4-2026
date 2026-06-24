"""Mini-runner de tests, para correr SIN instalar pytest.

Cada archivo test_*.py importa `correr` de aca y al final hace:

    if __name__ == "__main__":
        import sys; sys.exit(correr(globals()))

Asi se corre con:  python tests/test_xxx.py
y devuelve codigo != 0 si algo falla (util para verificar de un vistazo).
"""
import os
import sys

# Hace que los modulos del proyecto (fuerza.py, pid.py, ...) sean importables
# aunque la carpeta tenga espacios/acentos: agrega la carpeta padre al path.
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)


def correr(ns):
    """Corre todas las funciones test_* del namespace dado. Devuelve # de fallos."""
    pruebas = [(n, f) for n, f in sorted(ns.items())
               if n.startswith("test_") and callable(f)]
    fallos = 0
    for nombre, fn in pruebas:
        try:
            fn()
            print("  PASA  %s" % nombre)
        except AssertionError as e:
            fallos += 1
            print("  FALLA %s: %s" % (nombre, e))
        except Exception as e:
            fallos += 1
            print("  ERROR %s: %s: %s" % (nombre, type(e).__name__, e))
    print("-> %s (%d/%d pasaron)" % (
        "TODO OK" if fallos == 0 else "HAY FALLOS",
        len(pruebas) - fallos, len(pruebas)))
    return fallos
