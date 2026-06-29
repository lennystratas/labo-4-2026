"""Tests del paso de control (decision PID vs mantener) y del lazo+registro."""
import math
import os
import tempfile
from _bootstrap import correr
import numpy as np
import control_loop
import registro as registro_mod
import vision
from pid import PID


class PidStub:
    def __init__(self):
        self.update_llamado = False
        self.setpoint = 0.0

    def update(self, pos, dt):
        self.update_llamado = True
        return 0.7

    def mantener(self):
        return 0.3


def test_usa_pid_si_medicion_valida():
    p = PidStub()
    cmd = control_loop.paso_de_control(2.0, True, p, 0.1)
    assert p.update_llamado and abs(cmd - 0.7) < 1e-12


def test_mantiene_si_medicion_invalida():
    p = PidStub()
    cmd = control_loop.paso_de_control(2.0, False, p, 0.1)
    assert (not p.update_llamado) and abs(cmd - 0.3) < 1e-12


def test_mantiene_si_posicion_es_nan():
    p = PidStub()
    cmd = control_loop.paso_de_control(float("nan"), True, p, 0.1)
    assert (not p.update_llamado) and abs(cmd - 0.3) < 1e-12


class _OrigenFake:
    def medir(self):
        return vision.Medicion(x_mm=1.0, y_mm=2.0, x_px=10.0, y_px=20.0,
                               intensidad=5.0, pico=0.5, valido=True, saturado=False)

    def paso(self, dt):
        pass


class _ActFake:
    def aplicar(self, u):
        return 5.0, 6.0, u            # devuelve (V_A, V_B, F_real)


class _ActFakeConLectura:
    def aplicar(self, u):
        return 5.0, 6.0, u

    def leer_tensiones(self):
        return 10.0, 11.0             # tension "real" leida de la fuente


def test_correr_lazo_registra_filas_y_columnas():
    with tempfile.TemporaryDirectory() as base:
        reg = registro_mod.Registro(base, control_loop.COLUMNAS, periodo_chunk_s=1e12)
        pid = PID(0.1, 0.0, 0.0, setpoint=0.0, salida_min=-1.0, salida_max=1.0)
        n = control_loop.correr_lazo(_OrigenFake(), _ActFake(), pid, fmax=1e-6,
                                     eje="x", dt_fijo=0.1, n_iter=5, registro=reg)
        reg.cerrar()
        assert n == 5
        data = np.loadtxt(os.path.join(reg.carpeta, "medicion00_0000.txt"))
        assert data.shape == (5, len(control_loop.COLUMNAS))


def test_correr_lazo_registra_lectura_real():
    with tempfile.TemporaryDirectory() as base:
        reg = registro_mod.Registro(base, control_loop.COLUMNAS, periodo_chunk_s=1e12)
        pid = PID(0.1, 0.0, 0.0, setpoint=0.0, salida_min=-1.0, salida_max=1.0)
        control_loop.correr_lazo(_OrigenFake(), _ActFakeConLectura(), pid, fmax=1e-6,
                                 eje="x", dt_fijo=0.1, n_iter=3, registro=reg,
                                 leer_real=True)
        reg.cerrar()
        data = np.loadtxt(os.path.join(reg.carpeta, "medicion00_0000.txt"))
        iA = control_loop.COLUMNAS.index("V_A_leido")
        iB = control_loop.COLUMNAS.index("V_B_leido")
        assert np.allclose(data[:, iA], 10.0)
        assert np.allclose(data[:, iB], 11.0)


if __name__ == "__main__":
    import sys
    sys.exit(correr(globals()))
