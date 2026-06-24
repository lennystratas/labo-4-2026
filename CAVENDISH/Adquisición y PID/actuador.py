"""
Actuador: convierte la accion de control en tensiones de las 2 fuentes.
====================================================================

Hay 2 canales (A y B) -- pueden ser 2 canales de una misma fuente (lo usual)
o 2 fuentes separadas. Cada canal alimenta sus 2 capacitores (que actuan
juntos). La fuerza de cada canal es ~ V^2 y SIEMPRE atractiva, asi que para
tener control bidireccional se usa un par push-pull:

    canal A empuja en +   ,   canal B empuja en -
    fuerza neta = fuerza_canal(V_A) - fuerza_canal(V_B)

LINEALIZACION (drive diferencial con bias):
    se eligen   V_A^2 = V_bias^2 + delta ,  V_B^2 = V_bias^2 - delta
    entonces    fuerza_neta = 2*k*delta      (LINEAL en delta)
    con         k = n_caps*factor*eps_r*eps0*b/d
    => para pedir una fuerza neta u:   delta = u / (2k)

Asi el lazo "ve" un actuador lineal. El rango maximo de delta (y por lo tanto
de fuerza) se elige para no pedir tensiones fuera de [0, V_max]. El bias
optimo para rango simetrico es V_bias = V_max/raiz(2).

La salida del PID (u) se interpreta como FUERZA NETA pedida [N].
"""
import re

import fuerza


def _k(geom):
    """Constante de proporcionalidad: fuerza_canal = k * V^2."""
    return geom.n_caps * geom.factor * geom.eps_r * fuerza.EPS0 * geom.b / geom.d


def _delta_max(V_bias, V_max):
    """Maximo |delta| (en V^2) que mantiene ambas tensiones en [0, V_max]."""
    return min(V_bias ** 2, V_max ** 2 - V_bias ** 2)


def fuerza_neta_maxima(geom, V_bias, V_max):
    """Fuerza neta [N] maxima alcanzable sin salir de [0, V_max]."""
    return 2.0 * _k(geom) * _delta_max(V_bias, V_max)


def control_a_tensiones(u, geom, V_bias, V_max):
    """Pasa de fuerza neta pedida u [N] a (V_A, V_B) [V], con clamp seguro."""
    if not (0.0 <= V_bias <= V_max):
        raise ValueError("se requiere 0 <= V_bias <= V_max (V_bias=%r, V_max=%r)"
                         % (V_bias, V_max))
    k = _k(geom)
    delta = u / (2.0 * k)
    dmax = _delta_max(V_bias, V_max)
    delta = max(-dmax, min(dmax, delta))          # clamp del rango lineal
    Va = (max(V_bias ** 2 + delta, 0.0)) ** 0.5
    Vb = (max(V_bias ** 2 - delta, 0.0)) ** 0.5
    # clamp final por seguridad numerica
    Va = min(max(Va, 0.0), V_max)
    Vb = min(max(Vb, 0.0), V_max)
    return Va, Vb


# ==========================================================================
# Protocolo de la fuente Hantek PPS2320A (puros y testeables).
#   - cada comando termina en 0x0a ('\n')
#   - tension : 'su'/'sa' (CH1/CH2) + 4 digitos en CENTESIMAS de V (1200=12.00V)
#   - corriente: 'si'/'sd' (CH1/CH2) + 4 digitos en MILESIMAS de A (2500=2.500A)
#   - salida  : 'O1' = ON , 'O0' = OFF
# ==========================================================================
_PREF_V = {1: "su", 2: "sa"}    # prefijo de tension   CH1 / CH2
_PREF_I = {1: "si", 2: "sd"}    # prefijo de corriente CH1 / CH2


def tension_segura(V, v_max_hard):
    """Clampea la tension a [0, v_max_hard]. Nunca deja pasar algo peligroso."""
    return min(max(V, 0.0), v_max_hard)


def codificar_tension(V, v_max_hard):
    """V [V] -> 4 digitos en centesimas (con clamp).  12.00 V -> '1200'."""
    centi = int(round(tension_segura(V, v_max_hard) * 100))
    return "%04d" % max(0, min(centi, 9999))


def codificar_corriente(A, a_max):
    """A [A] -> 4 digitos en milesimas (con clamp).  2.500 A -> '2500'."""
    mili = int(round(min(max(A, 0.0), a_max) * 1000))
    return "%04d" % max(0, min(mili, 9999))


def comando_tension(canal, V, v_max_hard):
    """Comando para fijar la tension de un canal. CH1->'su....', CH2->'sa....'."""
    return _PREF_V[canal] + codificar_tension(V, v_max_hard)


def comando_corriente(canal, A, a_max):
    """Comando para fijar el limite de corriente de un canal."""
    return _PREF_I[canal] + codificar_corriente(A, a_max)


def com_a_asrl(puerto):
    """'COM3' -> 'ASRL3::INSTR' (para pyvisa). Si ya es ASRL/otra, lo deja igual."""
    if puerto.upper().startswith("COM"):
        return "ASRL%s::INSTR" % puerto[3:]
    return puerto


def parsear_tension(respuesta):
    """Respuesta de lectura del equipo -> Volts (float). NaN si no se puede.

    Heuristica (AJUSTAR segun lo que muestre probar_fuente.py):
      - si la respuesta trae punto, se toma directo en V:  '12.00' -> 12.00
      - si son solo digitos, se asume en centesimas:       '1200'  -> 12.00
    """
    m = re.search(r"-?\d+\.?\d*", respuesta or "")
    if not m:
        return float("nan")
    num = m.group(0)
    return float(num) if "." in num else int(num) / 100.0


# ==========================================================================
# Transportes: la capa fisica (abrir / escribir / leer / cerrar). Hay dos,
# para poder probar pyserial y pyvisa con EXACTAMENTE el mismo protocolo.
# Ambos terminan los comandos en '\n' (0x0a).
# ==========================================================================
class TransporteSerial:
    """Puerto serie via pyserial. Permite forzar DTR/RTS y esperar tras abrir
    (algunos USB-serial resetean el equipo al abrir el puerto)."""

    def __init__(self, puerto, baud=9600, dtr=None, rts=None, espera=2.0, timeout=1.0):
        import time
        import serial  # pyserial (pip install pyserial)
        self.ser = serial.Serial()
        self.ser.port = puerto
        self.ser.baudrate = baud
        self.ser.timeout = timeout
        if dtr is not None:
            self.ser.dtr = dtr          # algunos equipos necesitan DTR en 0
        if rts is not None:
            self.ser.rts = rts
        self.ser.open()
        if espera > 0:
            time.sleep(espera)          # darle tiempo a que arranque
        self.ser.reset_input_buffer()

    def escribir(self, texto):
        self.ser.write((texto + "\n").encode("ascii"))

    def leer_linea(self):
        return self.ser.readline().decode("ascii", "replace").strip()

    def cerrar(self):
        self.ser.close()


class TransporteVisa:
    """Mismo protocolo pero por pyvisa (backend pyvisa-py para no depender de
    NI-VISA). Para un COM, pasar 'ASRL<n>::INSTR' (ver com_a_asrl)."""

    def __init__(self, recurso, baud=9600, timeout=1000):
        import pyvisa  # pip install pyvisa pyvisa-py
        try:
            self.rm = pyvisa.ResourceManager("@py")
        except Exception:
            self.rm = pyvisa.ResourceManager()      # cae al backend por defecto
        self.inst = self.rm.open_resource(recurso)
        try:
            self.inst.baud_rate = baud
        except Exception:
            pass
        self.inst.timeout = timeout
        self.inst.write_termination = "\n"
        self.inst.read_termination = "\n"

    def escribir(self, texto):
        self.inst.write(texto)

    def leer_linea(self):
        try:
            return self.inst.read().strip()
        except Exception:
            return ""

    def cerrar(self):
        self.inst.close()


def abrir_transporte(puerto, baud=9600, backend="serial",
                     dtr=None, rts=None, espera=2.0):
    """Crea el transporte segun backend ('serial' o 'visa')."""
    if backend == "visa":
        return TransporteVisa(com_a_asrl(puerto), baud)
    return TransporteSerial(puerto, baud, dtr=dtr, rts=rts, espera=espera)


# ==========================================================================
# Interfaz comun
# ==========================================================================
class Actuador:
    """Interfaz: el lazo solo llama aplicar(u), reposo() y cerrar()."""

    def aplicar(self, u):
        """Aplica la fuerza neta pedida u [N]. Devuelve (V_A, V_B, fuerza_real_N)."""
        raise NotImplementedError

    def reposo(self):
        """Lleva las fuentes al bias (fuerza neta 0)."""
        raise NotImplementedError

    def cerrar(self):
        pass


# ==========================================================================
# Actuador NULO: no toca ninguna fuente. Sirve para ensayar la camara y la
# medicion sin tener las fuentes conectadas (modo "solo medir").
# ==========================================================================
class ActuadorNulo(Actuador):
    def __init__(self, V_bias=0.0):
        self.V_bias = V_bias

    def aplicar(self, u):
        return self.V_bias, self.V_bias, 0.0

    def reposo(self):
        pass


# ==========================================================================
# Fuente real: Hantek PPS2320A por puerto serie (pyserial). Usa sus 2 canales
# (CH1, CH2) como las 2 'fuentes' del par push-pull.
# ==========================================================================
class ActuadorPPS2320A(Actuador):
    r"""
    Fuente Hantek PPS2320A via puerto serie (USB-serial -> COMx). Necesita
    pyserial (pip install pyserial). Protocolo (ver helpers de arriba):
    'su/sa' tension, 'si/sd' corriente, 'O1/O0' salida ON/OFF, terminador '\n'.

    canal_a / canal_b son 1 o 2 (CH1 / CH2). i_limite es el limite de corriente
    por canal (el capacitor casi no consume; un limite chico esta bien).
    """
    _LECTURA_V = {1: "rv", 2: "rh"}    # tension medida CH1 / CH2

    _LECTURA_PRESET = {1: "ru", 2: "rk"}   # tension PRESET (lo seteado) CH1 / CH2

    def __init__(self, geom, V_bias, V_max, puerto, baud=9600,
                 canal_a=1, canal_b=2, i_limite=0.5, i_max=3.1,
                 V_max_hard=None, backend="serial", dtr=None, rts=None, espera=2.0):
        self.geom = geom
        self.V_bias = V_bias
        self.V_max = V_max
        self.canal_a = canal_a
        self.canal_b = canal_b
        self.i_max = i_max
        # tope de seguridad de hardware (por si V_max logico se sube por error)
        self.V_max_hard = V_max_hard if V_max_hard is not None else V_max
        # capa fisica: 'serial' (pyserial) o 'visa' (pyvisa). Import diferido.
        self.t = abrir_transporte(puerto, baud, backend, dtr=dtr, rts=rts, espera=espera)
        # Si los canales NO salen independientes (modo serie/paralelo/trace),
        # descomenta para forzar modo independiente:  self._cmd("O2")
        for canal in (canal_a, canal_b):
            self._cmd(comando_corriente(canal, i_limite, self.i_max))
            self._cmd(comando_tension(canal, V_bias, self.V_max_hard))
        self._cmd("O1")        # salida ON  ('O1' habilita la salida en este equipo)

    def _cmd(self, texto):
        self.t.escribir(texto)

    def aplicar(self, u):
        Va, Vb = control_a_tensiones(u, self.geom, self.V_bias, self.V_max)
        self._cmd(comando_tension(self.canal_a, Va, self.V_max_hard))
        self._cmd(comando_tension(self.canal_b, Vb, self.V_max_hard))
        return Va, Vb, fuerza.fuerza_neta(Va, Vb, self.geom)

    def reposo(self):
        self._cmd(comando_tension(self.canal_a, self.V_bias, self.V_max_hard))
        self._cmd(comando_tension(self.canal_b, self.V_bias, self.V_max_hard))

    def cerrar(self):
        try:
            self._cmd("O0")    # salida OFF
            self.t.cerrar()
        except Exception:
            pass

    # ---- diagnostico (opcional) ----
    def modelo(self):
        """Envia 'a' y devuelve el modelo. Sirve para confirmar puerto y baud."""
        self._cmd("a")
        return self.t.leer_linea()

    def leer_tension(self, canal):
        """Lee la tension MEDIDA de un canal (texto crudo del equipo)."""
        self._cmd(self._LECTURA_V[canal])
        return self.t.leer_linea()

    def leer_preset(self, canal):
        """Lee la tension PRESET (la seteada) de un canal -> confirma la escritura."""
        self._cmd(self._LECTURA_PRESET[canal])
        return self.t.leer_linea()

    def leer_tensiones(self):
        """(V_A, V_B) MEDIDAS en la fuente [V], parseadas. (nan, nan) si falla.

        Lo usa el lazo para registrar la tension REAL (no solo la comandada).
        """
        try:
            va = parsear_tension(self.leer_tension(self.canal_a))
            vb = parsear_tension(self.leer_tension(self.canal_b))
            return va, vb
        except Exception:
            return float("nan"), float("nan")
