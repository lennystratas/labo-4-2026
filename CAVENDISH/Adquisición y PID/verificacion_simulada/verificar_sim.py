"""
Verificacion de lazo cerrado con el simulador  ***SOLO DESARROLLO***.
====================================================================

Reproduce el experimento sin hardware y comprueba que el lazo funciona:

  Fase 1: parte de un offset -> el PID lleva el pendulo al nulo (x -> 0).
  Fase 2: aparece un torque perturbador (la "masa") -> el PID lo sostiene
          en el nulo y la FUERZA DE CONTROL en regimen recupera la
          perturbacion:   F_regimen  ~  -tau_dist / brazo.

Esto valida visión + PID + mapeo de fuerza + lazo, todo junto.
Tunear:  python verificar_sim.py --kp 0.6 --ki 0.25 --kd 1.2 --tau 0.2

>>> Este archivo se quita para el laboratorio. <<<
"""
import argparse
import os as _os
import sys as _sys

# este archivo vive en una subcarpeta; agrega la carpeta del lab al path.
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import actuador
import control_loop
import fuerza
from pid import PID
from simulador import Simulador

DT = 0.02            # 50 "fps" simulados
GEOM = fuerza.Geometria(b=0.05, d=1e-3, brazo=0.02, n_caps=2)
V_BIAS, V_MAX = 21.2, 30.0
T0, Q, I0, THETA0 = 20.0, 20.0, 1e-5, 0.005


def _correr(sim, pid, fmax, t_max):
    d = {"t": [], "x": [], "cmd": [], "F": []}

    def on_iter(i, t, m, cmd, F, Va, Vb, origen):
        d["t"].append(t)
        d["x"].append(m.x_mm if m.valido else np.nan)
        d["cmd"].append(cmd)
        d["F"].append(F)
        return True

    control_loop.correr_lazo(sim, sim, pid, fmax, eje="x",
                             dt_fijo=DT, t_max=t_max, on_iter=on_iter)
    return {k: np.asarray(v) for k, v in d.items()}


def main():
    ap = argparse.ArgumentParser()
    # defaults = ganancias validadas (las mismas que parametros.py)
    ap.add_argument("--kp", type=float, default=2.8)
    ap.add_argument("--ki", type=float, default=0.8)
    ap.add_argument("--kd", type=float, default=5.6)
    ap.add_argument("--tau", type=float, default=0.3)
    a = ap.parse_args()

    fmax = actuador.fuerza_neta_maxima(GEOM, V_BIAS, V_MAX)
    tau_max = fmax * GEOM.brazo
    tau_dist = 0.5 * tau_max
    F_esperado = -tau_dist / GEOM.brazo

    # --- lazo abierto (sin control) para comparar ---
    s_ol = Simulador(GEOM, V_BIAS, V_MAX, T0=T0, Q=Q, I=I0, theta0=THETA0)
    ol = _correr(s_ol, PID(0, 0, 0), fmax, t_max=80)

    # --- lazo cerrado ---
    s = Simulador(GEOM, V_BIAS, V_MAX, T0=T0, Q=Q, I=I0, theta0=THETA0)
    pid = PID(a.kp, a.ki, a.kd, setpoint=0.0,
              salida_min=-1.0, salida_max=1.0, tau_deriv=a.tau)
    f1 = _correr(s, pid, fmax, t_max=40)          # fase 1: nulado
    s.tau_dist = tau_dist                          # aparece la "masa"
    f2 = _correr(s, pid, fmax, t_max=80)          # fase 2: sostener + medir
    t2 = f2["t"] + f1["t"][-1] + DT

    # --- metricas ---
    n5 = int(5 / DT)
    n10 = int(10 / DT)
    x_fin_p1 = float(np.nanmax(np.abs(f1["x"][-n5:])))
    x_ss = float(np.nanmean(f2["x"][-n10:]))
    F_ss = float(np.mean(f2["F"][-n10:]))
    err_rel = abs(F_ss - F_esperado) / abs(F_esperado)

    ok_p1 = x_fin_p1 < 0.05
    ok_ss = abs(x_ss) < 0.05
    ok_F = err_rel < 0.05
    todo = ok_p1 and ok_ss and ok_F

    print("=" * 60)
    print("Ganancias: kp=%.3g ki=%.3g kd=%.3g tau=%.3g" % (a.kp, a.ki, a.kd, a.tau))
    print("fuerza max disponible : %.3e N" % fmax)
    print("perturbacion (masa)   : tau_dist=%.3e N*m" % tau_dist)
    print("-" * 60)
    print("Fase1 |x| final (5s)  : %.4f mm   %s (<0.05)" % (x_fin_p1, "OK" if ok_p1 else "MAL"))
    print("Fase2 x en regimen    : %.4f mm   %s (~0)" % (x_ss, "OK" if ok_ss else "MAL"))
    print("Fase2 F en regimen    : %.4e N" % F_ss)
    print("F esperada (-tau/brazo): %.4e N" % F_esperado)
    print("error relativo de F   : %.2f %%   %s (<5%%)" % (100 * err_rel, "OK" if ok_F else "MAL"))
    print("=" * 60)
    print("RESULTADO:", "PASA  el lazo funciona" if todo else "FALLA  (ajustar ganancias)")

    # --- grafico ---
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 7), sharex=True)
    ax1.plot(ol["t"], ol["x"], color="0.7", label="lazo abierto (sin control)")
    ax1.plot(f1["t"], f1["x"], "C0", label="lazo cerrado")
    ax1.plot(t2, f2["x"], "C0")
    ax1.axvline(f1["t"][-1] + DT, color="C3", ls="--", label="aparece la masa")
    ax1.axhline(0, color="k", lw=0.5)
    ax1.set_ylabel("posicion x [mm]")
    ax1.legend(loc="upper right")
    ax1.set_title("Servo de nulo: el PID mantiene el pendulo quieto")

    ax2.plot(f1["t"], f1["F"], "C1")
    ax2.plot(t2, f2["F"], "C1", label="fuerza de control")
    ax2.axhline(F_esperado, color="C3", ls="--", label="fuerza esperada (-tau/brazo)")
    ax2.axvline(f1["t"][-1] + DT, color="C3", ls="--")
    ax2.set_xlabel("tiempo [s]")
    ax2.set_ylabel("fuerza neta [N]")
    ax2.legend(loc="upper right")
    ax2.set_title("La fuerza de control en regimen mide la perturbacion")

    fig.tight_layout()
    _png = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "verificacion.png")
    fig.savefig(_png, dpi=110)
    print("Grafico ->", _png)
    return 0 if todo else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
