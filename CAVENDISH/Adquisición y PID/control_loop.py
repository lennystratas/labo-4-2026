"""
Lazo de control PID: mantiene el pendulo quieto y registra la fuerza.
====================================================================

Flujo de cada vuelta:

    medir posicion (camara)  ->  PID  ->  fuerza pedida  ->  2 tensiones
                                                          ->  registrar

La salida del PID es un COMANDO normalizado en [-1, 1] = fraccion de la
fuerza neta maxima disponible. La fuerza real en N se calcula de las
tensiones (modelo de fuerza.py) y es lo que se registra: esa es la medicion
del experimento (al acercar la masa, cambia la fuerza necesaria).

El mismo `correr_lazo` se usa con la camara real (este archivo) y se podia
usar con el simulador durante el desarrollo: solo cambia el `origen` y el
`actuador` (inyeccion de dependencias).
"""
import math
import time

import fuerza
import actuador as actuador_mod
import vision
import registro as registro_mod
from pid import PID

# Columnas del registro. Las 3 primeras (t_s, x_mm, y_mm) mantienen
# compatibilidad con el analisis previo; el resto es propio del feedback.
COLUMNAS = ["t_s", "x_mm", "y_mm", "valido", "setpoint_mm",
            "error_mm", "cmd", "V_A", "V_B", "F_neta_N"]


def paso_de_control(pos_mm, valido, pid, dt):
    """Decide el comando: PID si la medicion es valida, si no MANTIENE.

    Evita que el integrador se descontrole cuando se pierde el laser
    (invalido o NaN): en ese caso repite la ultima salida sin integrar.
    """
    if valido and not math.isnan(pos_mm):
        return pid.update(pos_mm, dt)
    return pid.mantener()


class FuenteCamara:
    """Origen de medicion para el laboratorio: camara + pipeline de vision."""

    def __init__(self, camara, calibracion):
        self.cam = camara
        self.cal = calibracion
        self.ultimo_frame = None
        self.ultima_medicion = None

    def medir(self):
        frame = self.cam.leer()
        if frame is None:
            return None
        self.ultimo_frame = frame
        self.ultima_medicion = vision.medir(frame, self.cal)
        return self.ultima_medicion

    def paso(self, dt):
        pass            # el mundo real avanza solo

    def cerrar(self):
        self.cam.cerrar()


def correr_lazo(origen, actuador, pid, fmax, eje="x", *,
                dt_fijo=None, t_max=None, n_iter=None,
                registro=None, on_iter=None, reloj=time.monotonic):
    """Corre el lazo de control. Devuelve la cantidad de iteraciones hechas.

    origen   : objeto con medir()->Medicion (o None) y paso(dt)
    actuador : objeto con aplicar(F)->(V_A, V_B, F_real)
    fmax     : fuerza neta maxima [N] (mapea cmd en [-1,1] a fuerza)
    dt_fijo  : si se da, usa ese paso (simulacion); si no, mide el reloj real
    """
    t0 = reloj()
    t_prev = t0
    i = 0
    while True:
        ahora = reloj()
        if dt_fijo is not None:
            dt = dt_fijo
            t = i * dt_fijo
        else:
            dt = ahora - t_prev
            if dt <= 0:
                dt = 1e-3
            t = ahora - t0
        t_prev = ahora

        m = origen.medir()
        if m is None:
            break

        pos = m.x_mm if eje == "x" else m.y_mm
        cmd = paso_de_control(pos, m.valido, pid, dt)
        cmd = max(-1.0, min(1.0, cmd))           # comando normalizado
        Va, Vb, F_real = actuador.aplicar(cmd * fmax)

        if registro is not None:
            err = (pid.setpoint - pos) if (m.valido and not math.isnan(pos)) else float("nan")
            registro.agregar([t, m.x_mm, m.y_mm, int(m.valido), pid.setpoint,
                              err, cmd, Va, Vb, F_real])

        if on_iter is not None and on_iter(i, t, m, cmd, F_real, Va, Vb, origen) is False:
            break

        origen.paso(dt)
        i += 1
        if n_iter is not None and i >= n_iter:
            break
        if t_max is not None and t >= t_max:
            break
    return i


# --------------------------------------------------------------------------
# Vista en vivo (overlay) - solo laboratorio. OpenCV import diferido.
# --------------------------------------------------------------------------
def _dibujar(cv2, frame, m, cmd, F_real, Va, Vb, eje):
    img = frame.copy()
    color_ok = (0, 255, 0)
    color_mal = (0, 0, 255)
    if m.valido and not math.isnan(m.x_px):
        c = (int(round(m.x_px)), int(round(m.y_px)))
        cv2.drawMarker(img, c, color_ok, cv2.MARKER_CROSS, 24, 2)
    txt = [
        "pos=%s  valido=%d  %s" % (
            ("%.3f mm" % (m.x_mm if eje == "x" else m.y_mm)) if m.valido else "----",
            int(m.valido),
            "SATURADO!" if m.saturado else ""),
        "cmd=%+.3f  F=%+.3e N" % (cmd, F_real),
        "V_A=%.2f  V_B=%.2f  (q=salir)" % (Va, Vb),
    ]
    for j, s in enumerate(txt):
        cv2.putText(img, s, (10, 24 + 22 * j), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(img, s, (10, 24 + 22 * j), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.imshow("Control PID (q=salir)", img)


def main(argv=None):
    import argparse
    import parametros as P

    ap = argparse.ArgumentParser(description="Lazo de control PID del pendulo")
    ap.add_argument("--fuente", default=None,
                    help="webcam (indice) o ruta de video; por defecto el de parametros.py")
    ap.add_argument("--sin-fuentes", action="store_true",
                    help="no usar las fuentes SCPI (solo medir y mostrar)")
    ap.add_argument("--sin-ventana", action="store_true", help="no mostrar la ventana")
    a = ap.parse_args(argv)

    geom = fuerza.Geometria(b=P.B_ANCHO_PLACA, d=P.D_SEPARACION, brazo=P.BRAZO,
                            n_caps=P.N_CAPS_POR_FUENTE, eps_r=P.EPS_R,
                            factor=P.FACTOR_FORMULA)
    fmax = actuador_mod.fuerza_neta_maxima(geom, P.V_BIAS, P.V_MAX)

    if a.sin_fuentes:
        act = actuador_mod.ActuadorNulo(P.V_BIAS)
        print("[modo solo-medir] sin fuente")
    else:
        act = actuador_mod.ActuadorPPS2320A(geom, P.V_BIAS, P.V_MAX,
                                            P.PUERTO_FUENTE, P.BAUD_FUENTE,
                                            P.CANAL_A, P.CANAL_B, P.I_LIMITE)
        try:
            print("Fuente conectada. Modelo:", act.modelo())
        except Exception as e:
            print("Aviso: no pude leer el modelo (revisa puerto/baud):", e)

    pid = PID(P.KP, P.KI, P.KD, setpoint=P.SETPOINT_MM,
              salida_min=-1.0, salida_max=1.0, tau_deriv=P.TAU_DERIV)

    cal = vision.cargar_calibracion(P.CARPETA_CALIBRACION)
    fuente_video = a.fuente if a.fuente is not None else P.FUENTE_VIDEO
    try:
        fuente_video = int(fuente_video)
    except (TypeError, ValueError):
        pass
    cam = vision.Camara(fuente_video, P.ANCHO, P.ALTO)
    origen = FuenteCamara(cam, cal)

    reg = registro_mod.Registro(P.CARPETA_DATOS, COLUMNAS, P.PERIODO_CHUNK_S,
                                meta={"fmax_N": fmax, "V_bias": P.V_BIAS,
                                      "V_max": P.V_MAX, "eje": P.EJE,
                                      "kp": P.KP, "ki": P.KI, "kd": P.KD})

    cv2 = None
    if not a.sin_ventana:
        import cv2 as _cv2
        cv2 = _cv2

    def on_iter(i, t, m, cmd, F_real, Va, Vb, origen):
        if cv2 is None:
            return True
        _dibujar(cv2, origen.ultimo_frame, m, cmd, F_real, Va, Vb, P.EJE)
        return cv2.waitKey(1) & 0xFF != ord("q")

    print("Corriendo lazo. Datos -> %s" % reg.carpeta)
    try:
        correr_lazo(origen, act, pid, fmax, eje=P.EJE, registro=reg, on_iter=on_iter)
    finally:
        act.reposo()
        act.cerrar()
        origen.cerrar()
        reg.cerrar()
        if cv2 is not None:
            cv2.destroyAllWindows()
        print("Listo. Datos guardados en %s" % reg.carpeta)


if __name__ == "__main__":
    main()
