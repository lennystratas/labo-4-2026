"""Tests del modelo electrostatico de fuerza (Fig. 13 de la guia)."""
from _bootstrap import correr
import fuerza

EPS0 = 8.8541878128e-12  # mismo valor que usa el modulo


def test_fuerza_capacitor_formula_de_la_guia():
    # F = eps0 * V^2 * b / d   (factor = 1, como la guia)
    V, b, d = 10.0, 0.05, 1e-3
    esperado = EPS0 * V**2 * b / d
    assert abs(fuerza.fuerza_capacitor(V, b, d) - esperado) < 1e-18


def test_fuerza_escala_con_V_al_cuadrado():
    f1 = fuerza.fuerza_capacitor(5.0, 0.05, 1e-3)
    f2 = fuerza.fuerza_capacitor(10.0, 0.05, 1e-3)
    assert abs(f2 - 4.0 * f1) < 1e-18  # el doble de V -> 4x la fuerza


def test_fuerza_no_depende_de_x():
    # la fuerza lateral de la guia NO depende del solapamiento: la formula
    # no tiene x, asi que dos llamadas iguales dan lo mismo (chequeo de cordura)
    assert fuerza.fuerza_capacitor(7.0, 0.04, 2e-3) == fuerza.fuerza_capacitor(7.0, 0.04, 2e-3)


def test_factor_un_medio_da_la_mitad():
    plena = fuerza.fuerza_capacitor(10.0, 0.05, 1e-3, factor=1.0)
    media = fuerza.fuerza_capacitor(10.0, 0.05, 1e-3, factor=0.5)
    assert abs(media - 0.5 * plena) < 1e-18


def test_d_no_positivo_lanza_error():
    try:
        fuerza.fuerza_capacitor(10.0, 0.05, 0.0)
    except ValueError:
        return
    assert False, "d<=0 deberia lanzar ValueError"


def test_canal_suma_dos_capacitores():
    g = fuerza.Geometria(b=0.05, d=1e-3, n_caps=2)
    uno = fuerza.fuerza_capacitor(12.0, g.b, g.d)
    assert abs(fuerza.fuerza_canal(12.0, g) - 2.0 * uno) < 1e-18


def test_fuerza_neta_nula_si_tensiones_iguales():
    g = fuerza.Geometria(b=0.05, d=1e-3, n_caps=2)
    assert abs(fuerza.fuerza_neta(15.0, 15.0, g)) < 1e-18


def test_fuerza_neta_positiva_si_A_mayor_que_B():
    g = fuerza.Geometria(b=0.05, d=1e-3, n_caps=2)
    assert fuerza.fuerza_neta(20.0, 10.0, g) > 0.0


def test_tension_para_fuerza_es_inversa_de_fuerza_canal():
    g = fuerza.Geometria(b=0.05, d=1e-3, n_caps=2)
    V = 18.0
    F = fuerza.fuerza_canal(V, g)
    assert abs(fuerza.tension_para_fuerza(F, g) - V) < 1e-9


def test_torque_es_fuerza_neta_por_brazo():
    g = fuerza.Geometria(b=0.05, d=1e-3, brazo=0.03, n_caps=2)
    fn = fuerza.fuerza_neta(20.0, 10.0, g)
    assert abs(fuerza.torque_neto(20.0, 10.0, g) - fn * g.brazo) < 1e-18


if __name__ == "__main__":
    import sys
    sys.exit(correr(globals()))
