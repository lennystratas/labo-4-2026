"""
Simulador del pendulo de torsion  ***SOLO PARA DESARROLLO/VERIFICACION***.
====================================================================

Hace de "mundo" para probar el lazo SIN hardware:
  * physics : pendulo de torsion  I*th'' + c*th' + kappa*th = tau
  * camara  : renderiza un spot gaussiano en la posicion del angulo y lo
              mide con el MISMO vision.medir() del laboratorio (centroide).
  * fuentes : usa el MISMO mapeo actuador.control_a_tensiones().

Implementa medir()/paso(dt)/aplicar(F) -> se enchufa a control_loop.correr_lazo
igual que la camara+fuentes reales (inyeccion de dependencias).

>>> Este archivo se quita para el laboratorio (no lo necesita). <<<
"""
import math
import os as _os
import sys as _sys

# este archivo vive en una subcarpeta; agrega la carpeta del lab al path
# para poder importar los modulos del laboratorio (actuador, fuerza, vision).
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

import numpy as np

import actuador as actuador_mod
import fuerza
import vision


class Simulador:
    def __init__(self, geom, V_bias, V_max, *,
                 T0=20.0, Q=20.0, I=1e-5,
                 theta0=0.005, tau_dist=0.0,
                 W=320, H=240, ganancia_px_por_rad=4000.0, mmpx=0.05,
                 sigma_px=2.5, ruido_px=0.8, seed=0):
        # --- pendulo ---
        self.I = I
        omega0 = 2.0 * math.pi / T0
        self.kappa = I * omega0 ** 2          # rigidez torsional [N*m/rad]
        self.c = I * omega0 / Q               # amortiguamiento [N*m*s/rad]
        self.theta = theta0
        self.omega = 0.0
        self.tau_dist = tau_dist              # torque perturbador (la "masa")
        self.brazo = geom.brazo
        # --- fuentes (mismo mapeo que el lab) ---
        self.geom = geom
        self.V_bias = V_bias
        self.V_max = V_max
        self.F_actual = 0.0
        # --- camara simulada ---
        self.W = W
        self.H = H
        self.cx = W / 2.0
        self.cy = H / 2.0
        self.gan = ganancia_px_por_rad
        self.sigma = sigma_px
        self.ruido = ruido_px
        self.rng = np.random.default_rng(seed)
        self.ultimo_frame = None
        self.cal = vision.Calibracion(fondo=None, umbral=0.06, minsig=0.05,
                                      origen=(self.cx, self.cy), mmpx=mmpx, roi=None)
        self._xs = np.arange(W)
        self._ys = np.arange(H)

    # ---- "camara" ----
    def _render(self):
        x_px = self.cx + self.gan * self.theta
        gx = np.exp(-((self._xs - x_px) ** 2) / (2.0 * self.sigma ** 2))
        gy = np.exp(-((self._ys - self.cy) ** 2) / (2.0 * self.sigma ** 2))
        img = 220.0 * np.outer(gy, gx)
        if self.ruido > 0:
            img = img + self.rng.normal(0.0, self.ruido, size=img.shape)
        img = np.clip(img, 0, 255).astype(np.uint8)
        frame = np.repeat(img[:, :, None], 3, axis=2)   # BGR (gris)
        self.ultimo_frame = frame
        return frame

    def medir(self):
        return vision.medir(self._render(), self.cal)

    # ---- "fuentes" ----
    def aplicar(self, F):
        Va, Vb = actuador_mod.control_a_tensiones(F, self.geom, self.V_bias, self.V_max)
        self.F_actual = fuerza.fuerza_neta(Va, Vb, self.geom)
        return Va, Vb, self.F_actual

    # ---- physics ----
    def paso(self, dt):
        tau = self.F_actual * self.brazo + self.tau_dist
        alpha = (tau - self.c * self.omega - self.kappa * self.theta) / self.I
        # Euler semi-implicito (estable para oscilador)
        self.omega += alpha * dt
        self.theta += self.omega * dt

    def cerrar(self):
        pass

    # ---- ayuda para la verificacion ----
    def torque_max(self, fmax):
        return fmax * self.brazo
