"""Tests del mapeo control -> 2 tensiones (drive diferencial con bias)."""
from _bootstrap import correr
import actuador
import fuerza

GEOM = fuerza.Geometria(b=0.05, d=1e-3, n_caps=2)
V_BIAS = 15.0
V_MAX = 30.0


def test_u_cero_deja_ambas_en_bias():
    Va, Vb = actuador.control_a_tensiones(0.0, GEOM, V_BIAS, V_MAX)
    assert abs(Va - V_BIAS) < 1e-9 and abs(Vb - V_BIAS) < 1e-9


def test_u_positivo_sube_A_y_baja_B():
    umax = actuador.fuerza_neta_maxima(GEOM, V_BIAS, V_MAX)
    Va, Vb = actuador.control_a_tensiones(0.5 * umax, GEOM, V_BIAS, V_MAX)
    assert Va > V_BIAS > Vb


def test_tensiones_producen_la_fuerza_pedida():
    umax = actuador.fuerza_neta_maxima(GEOM, V_BIAS, V_MAX)
    u = 0.5 * umax
    Va, Vb = actuador.control_a_tensiones(u, GEOM, V_BIAS, V_MAX)
    assert abs(fuerza.fuerza_neta(Va, Vb, GEOM) - u) < 1e-15


def test_simetria_del_signo():
    umax = actuador.fuerza_neta_maxima(GEOM, V_BIAS, V_MAX)
    Va, Vb = actuador.control_a_tensiones(0.4 * umax, GEOM, V_BIAS, V_MAX)
    Va2, Vb2 = actuador.control_a_tensiones(-0.4 * umax, GEOM, V_BIAS, V_MAX)
    assert abs(Va - Vb2) < 1e-9 and abs(Vb - Va2) < 1e-9


def test_clamp_no_supera_vmax_ni_baja_de_cero():
    umax = actuador.fuerza_neta_maxima(GEOM, V_BIAS, V_MAX)
    Va, Vb = actuador.control_a_tensiones(10.0 * umax, GEOM, V_BIAS, V_MAX)   # mucho mas que el maximo
    assert 0.0 <= Vb and Va <= V_MAX + 1e-9


def test_fuerza_satura_en_el_maximo():
    umax = actuador.fuerza_neta_maxima(GEOM, V_BIAS, V_MAX)
    Va, Vb = actuador.control_a_tensiones(10.0 * umax, GEOM, V_BIAS, V_MAX)
    assert abs(fuerza.fuerza_neta(Va, Vb, GEOM) - umax) < 1e-15


def test_fuerza_maxima_es_positiva():
    assert actuador.fuerza_neta_maxima(GEOM, V_BIAS, V_MAX) > 0.0


def test_bias_mayor_que_vmax_es_error():
    try:
        actuador.control_a_tensiones(0.0, GEOM, V_bias=40.0, V_max=30.0)
    except ValueError:
        return
    assert False, "V_bias > V_max deberia lanzar ValueError"


# ---- protocolo Hantek PPS2320A (2 canales = CH1 y CH2) ----
def test_tension_segura_clampea():
    assert actuador.tension_segura(999.0, 30.0) == 30.0   # tope superior
    assert actuador.tension_segura(-5.0, 30.0) == 0.0     # nunca negativa
    assert actuador.tension_segura(15.0, 30.0) == 15.0    # adentro, sin tocar


def test_codificar_tension_en_centesimas():
    assert actuador.codificar_tension(12.0, 30.0) == "1200"   # 12.00 V
    assert actuador.codificar_tension(5.0, 30.0) == "0500"
    assert actuador.codificar_tension(21.2, 30.0) == "2120"
    assert actuador.codificar_tension(0.0, 30.0) == "0000"


def test_codificar_tension_clampea_a_vmax():
    assert actuador.codificar_tension(99.0, 30.0) == "3000"   # clamp a 30.00 V


def test_comando_tension_por_canal():
    assert actuador.comando_tension(1, 12.0, 30.0) == "su1200"   # CH1
    assert actuador.comando_tension(2, 5.0, 30.0) == "sa0500"    # CH2


def test_comando_corriente_por_canal():
    assert actuador.comando_corriente(1, 2.5, 3.1) == "si2500"   # CH1, 2.500 A
    assert actuador.comando_corriente(2, 0.5, 3.1) == "sd0500"   # CH2, 0.500 A


def test_com_a_asrl_convierte_puerto_com():
    assert actuador.com_a_asrl("COM3") == "ASRL3::INSTR"
    assert actuador.com_a_asrl("COM12") == "ASRL12::INSTR"


def test_com_a_asrl_deja_pasar_asrl_directo():
    assert actuador.com_a_asrl("ASRL5::INSTR") == "ASRL5::INSTR"


def test_parsear_tension_decimal():
    assert abs(actuador.parsear_tension("12.00") - 12.00) < 1e-9
    assert abs(actuador.parsear_tension("5.00V") - 5.00) < 1e-9   # ignora unidades


def test_parsear_tension_en_centesimas():
    assert abs(actuador.parsear_tension("1200") - 12.00) < 1e-9   # sin punto -> centesimas


def test_parsear_tension_invalida_es_nan():
    import math
    assert math.isnan(actuador.parsear_tension(""))
    assert math.isnan(actuador.parsear_tension("sin numeros"))


class FakeFuente:
    """Modela la PPS2320A: CADA comando devuelve UNA linea (los 'set' -> 'ok').

    Reproduce el desfasaje real: si no se lee el 'ok' de cada set, las
    lecturas salen corridas. Con lockstep (1 lectura por comando) queda OK.
    """

    def __init__(self):
        self.cola = []
        self.preset = {1: 0, 2: 0}   # en centesimas de V
        self.salida = False

    def escribir(self, texto):
        if texto[:2] == "su":
            self.preset[1] = int(texto[2:]); self.cola.append("ok")
        elif texto[:2] == "sa":
            self.preset[2] = int(texto[2:]); self.cola.append("ok")
        elif texto[:2] in ("si", "sd"):
            self.cola.append("ok")
        elif texto[:1] == "O":
            self.salida = (texto == "O1"); self.cola.append("ok")
        elif texto == "ru":
            self.cola.append("%04d" % self.preset[1])
        elif texto == "rk":
            self.cola.append("%04d" % self.preset[2])
        elif texto == "rv":
            self.cola.append("%04d" % (self.preset[1] if self.salida else 0))
        elif texto == "rh":
            self.cola.append("%04d" % (self.preset[2] if self.salida else 0))
        elif texto == "a":
            self.cola.append("PPS2320A")
        else:
            self.cola.append("ok")

    def leer_linea(self):
        return self.cola.pop(0) if self.cola else ""

    def limpiar(self):
        self.cola.clear()

    def cerrar(self):
        pass


def test_lockstep_lee_el_bias_tras_init():
    f = FakeFuente()
    g = fuerza.Geometria(b=0.05, d=1e-3, n_caps=2)
    act = actuador.ActuadorPPS2320A(g, 15.0, 30.0, transporte=f)
    va, vb = act.leer_tensiones()     # init seteo bias 15 V y salida ON
    assert abs(va - 15.0) < 1e-6 and abs(vb - 15.0) < 1e-6


def test_lockstep_aplicar_se_refleja_en_lectura():
    f = FakeFuente()
    g = fuerza.Geometria(b=0.05, d=1e-3, n_caps=2)
    act = actuador.ActuadorPPS2320A(g, 15.0, 30.0, transporte=f)
    Va, Vb, _ = act.aplicar(0.0)      # u=0 -> ambas en bias
    va, vb = act.leer_tensiones()
    assert abs(va - Va) < 1e-6 and abs(vb - Vb) < 1e-6


if __name__ == "__main__":
    import sys
    sys.exit(correr(globals()))
