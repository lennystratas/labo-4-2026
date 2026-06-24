"""Tests del controlador PID (servo de nulo)."""
from _bootstrap import correr
import pid


def test_proporcional_puro():
    c = pid.PID(kp=2.0, ki=0.0, kd=0.0, setpoint=10.0)
    # error = 10 - 4 = 6  ->  salida = 2*6 = 12
    assert abs(c.update(4.0, dt=0.1) - 12.0) < 1e-12


def test_signo_error_positivo_da_salida_positiva():
    c = pid.PID(kp=1.0, ki=0.0, kd=0.0, setpoint=5.0)
    assert c.update(0.0, dt=0.1) > 0.0   # medicion por debajo del setpoint


def test_integral_acumula_con_error_constante():
    c = pid.PID(kp=0.0, ki=1.0, kd=0.0, setpoint=1.0)
    s1 = c.update(0.0, dt=1.0)   # integral = 1*1*1 = 1
    s2 = c.update(0.0, dt=1.0)   # integral = 2
    assert s2 > s1
    assert abs(s2 - 2.0) < 1e-9


def test_salida_se_satura_al_maximo():
    c = pid.PID(kp=100.0, ki=0.0, kd=0.0, setpoint=10.0,
                salida_min=-5.0, salida_max=5.0)
    assert abs(c.update(0.0, dt=0.1) - 5.0) < 1e-12


def test_antiwindup_no_acumula_en_saturacion():
    # con anti-windup, tras muchos pasos saturados, al desaparecer el error
    # la salida vuelve a ~0 de inmediato (el integral no se "cargo")
    c = pid.PID(kp=1.0, ki=10.0, kd=0.0, setpoint=10.0,
                salida_min=-5.0, salida_max=5.0)
    for _ in range(50):
        c.update(0.0, dt=0.1)          # error grande y positivo -> saturado en +5
    salida = c.update(10.0, dt=0.1)    # error = 0
    assert abs(salida) < 1e-6, "hubo windup: salida=%r" % salida


def test_derivada_sobre_medicion_no_patea_al_cambiar_setpoint():
    c = pid.PID(kp=0.0, ki=0.0, kd=5.0, setpoint=0.0)
    c.update(1.0, dt=0.1)              # fija medicion previa = 1.0
    c.setpoint = 100.0                 # salto de setpoint
    salida = c.update(1.0, dt=0.1)     # misma medicion -> derivada debe ser 0
    assert abs(salida) < 1e-9, "la derivada pateo con el cambio de setpoint: %r" % salida


def test_primer_llamado_sin_derivada():
    c = pid.PID(kp=0.0, ki=0.0, kd=5.0, setpoint=0.0)
    assert abs(c.update(123.0, dt=0.1)) < 1e-9  # no hay medicion previa -> deriv 0


def test_mantener_devuelve_ultima_salida_sin_integrar():
    c = pid.PID(kp=1.0, ki=1.0, kd=0.0, setpoint=1.0)
    u = c.update(0.0, dt=1.0)
    integral_antes = c.integral
    assert abs(c.mantener() - u) < 1e-12
    assert c.integral == integral_antes  # mantener NO integra


def test_reset_limpia_estado():
    c = pid.PID(kp=0.0, ki=1.0, kd=0.0, setpoint=1.0)
    c.update(0.0, dt=1.0)
    c.reset()
    assert c.integral == 0.0
    assert abs(c.update(0.0, dt=1.0) - 1.0) < 1e-9  # arranca de cero otra vez


def test_dt_no_positivo_lanza_error():
    c = pid.PID(kp=1.0, ki=0.0, kd=0.0, setpoint=0.0)
    try:
        c.update(0.0, dt=0.0)
    except ValueError:
        return
    assert False, "dt<=0 deberia lanzar ValueError"


if __name__ == "__main__":
    import sys
    sys.exit(correr(globals()))
