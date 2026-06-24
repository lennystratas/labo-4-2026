"""
Modelo electrostatico de fuerza de los capacitores de control.
====================================================================

Principio (Fig. 13 de la guia): dos placas paralelas, una fija y una movil,
que se solapan una distancia x. Al aplicar tension V aparece una fuerza
LATERAL (en la direccion de x) que tiende a aumentar el solapamiento:

        F_x = factor * eps_r * eps0 * V^2 * b / d

    b   = ancho de la placa (perpendicular al movimiento)   [m]
    d   = separacion entre placas                           [m]
    V   = tension aplicada                                  [V]
    F_x = fuerza lateral                                    [N]

Lo importante: F_x NO depende de x (el solapamiento). Mientras haya solape
parcial, la fuerza es constante con la posicion -> el actuador es una fuente
de fuerza pareja, fijada solo por V^2. Ideal para el control.

Sobre 'factor':
    La guia usa   F_x = eps0 * V^2 * b / d        -> factor = 1.0  (DEFAULT)
    Muchos textos usan F_x = 1/2 * eps0 * V^2 * b/d (convencion de energia a
    V constante) -> poner factor = 0.5.
    Como la calibracion absoluta no es lo critico (lo critico es mantener el
    pendulo quieto), se deja la de la guia por defecto, en UN solo lugar.

Tambien sirve como calculadora suelta:

    python fuerza.py --V 25 --b 0.05 --d 1e-3 --brazo 0.03
"""
from dataclasses import dataclass

# Permitividad del vacio [F/m]. (En aire es practicamente igual.)
EPS0 = 8.8541878128e-12


@dataclass
class Geometria:
    """Geometria de UN canal = las 2 placas alimentadas por UNA fuente."""
    b: float                 # ancho de placa [m]
    d: float                 # separacion entre placas [m]
    brazo: float = 0.0       # distancia del capacitor al eje de giro [m]
    n_caps: int = 2          # capacitores que alimenta cada fuente (actuan juntos)
    eps_r: float = 1.0       # permitividad relativa del medio (1.0 = vacio/aire)
    factor: float = 1.0      # 1.0 = formula de la guia ; 0.5 = convencion con 1/2


def fuerza_capacitor(V, b, d, eps_r=1.0, factor=1.0):
    """Fuerza lateral [N] de UN capacitor a tension V. F = factor*eps_r*eps0*V^2*b/d."""
    if d <= 0:
        raise ValueError("d (separacion) debe ser > 0, se recibio %r" % d)
    if b < 0:
        raise ValueError("b (ancho) debe ser >= 0, se recibio %r" % b)
    return factor * eps_r * EPS0 * V * V * b / d


def fuerza_canal(V, geom):
    """Fuerza [N] de un canal = n_caps capacitores (en paralelo) a tension V."""
    return geom.n_caps * fuerza_capacitor(V, geom.b, geom.d, geom.eps_r, geom.factor)


def fuerza_neta(V_a, V_b, geom):
    """Fuerza neta [N] del par push-pull: canal A (V_a) menos canal B (V_b)."""
    return fuerza_canal(V_a, geom) - fuerza_canal(V_b, geom)


def torque_neto(V_a, V_b, geom):
    """Torque neto [N*m] sobre el pendulo = fuerza neta * brazo de palanca."""
    return fuerza_neta(V_a, V_b, geom) * geom.brazo


def tension_para_fuerza(F_canal, geom):
    """Tension [V] que produce una fuerza dada en UN canal (inversa de fuerza_canal)."""
    if F_canal < 0:
        raise ValueError("F_canal debe ser >= 0, se recibio %r" % F_canal)
    k = geom.n_caps * geom.factor * geom.eps_r * EPS0 * geom.b / geom.d
    if k <= 0:
        raise ValueError("geometria invalida (k<=0)")
    return (F_canal / k) ** 0.5


# --------------------------------------------------------------------------
# Calculadora por linea de comandos
# --------------------------------------------------------------------------
def _cli():
    import argparse
    p = argparse.ArgumentParser(
        description="Calcula la fuerza electrostatica lateral F = factor*eps0*V^2*b/d")
    p.add_argument("--V", type=float, required=True, help="tension [V]")
    p.add_argument("--b", type=float, required=True, help="ancho de placa [m]")
    p.add_argument("--d", type=float, required=True, help="separacion entre placas [m]")
    p.add_argument("--eps_r", type=float, default=1.0, help="permitividad relativa (def 1.0)")
    p.add_argument("--factor", type=float, default=1.0, help="1.0 guia / 0.5 con 1/2 (def 1.0)")
    p.add_argument("--n_caps", type=int, default=2, help="capacitores por fuente (def 2)")
    p.add_argument("--brazo", type=float, default=0.0, help="brazo de palanca [m] (opcional)")
    a = p.parse_args()

    g = Geometria(b=a.b, d=a.d, brazo=a.brazo, n_caps=a.n_caps,
                  eps_r=a.eps_r, factor=a.factor)
    f1 = fuerza_capacitor(a.V, a.b, a.d, a.eps_r, a.factor)
    fc = fuerza_canal(a.V, g)
    print("Fuerza de 1 capacitor : %.6e N" % f1)
    print("Fuerza del canal (%d)  : %.6e N" % (a.n_caps, fc))
    if a.brazo > 0:
        print("Torque del canal      : %.6e N*m  (brazo=%.4g m)" % (fc * a.brazo, a.brazo))


if __name__ == "__main__":
    _cli()
