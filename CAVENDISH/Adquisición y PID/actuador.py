"""
Actuador: convierte la accion de control en tensiones de las 2 fuentes.
====================================================================

Hay 2 fuentes (A y B), cada una alimenta sus 2 capacitores (que actuan
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
# Fuente programable real por SCPI/VISA  (esqueleto - completar manana)
# ==========================================================================
class ActuadorSCPI(Actuador):
    """
    Dos fuentes de banco programables por VISA (pyvisa). Es un ESQUELETO:
    los comandos SCPI exactos dependen del modelo de fuente -> se confirman
    cuando este el equipo (estan marcados con TODO).
    """

    def __init__(self, geom, V_bias, V_max, recurso_a, recurso_b,
                 V_max_hard=None):
        import pyvisa  # import diferido (solo hace falta con hardware real)
        self.geom = geom
        self.V_bias = V_bias
        self.V_max = V_max
        # tope de seguridad de hardware (por si V_max logico se sube por error)
        self.V_max_hard = V_max_hard if V_max_hard is not None else V_max
        self._rm = pyvisa.ResourceManager()
        self.fa = self._rm.open_resource(recurso_a)
        self.fb = self._rm.open_resource(recurso_b)
        self._init_fuente(self.fa)
        self._init_fuente(self.fb)

    def _init_fuente(self, f):
        # TODO(lab): ajustar a los comandos de TU fuente
        f.write("*RST")
        f.write("VOLT %.4f" % self.V_bias)
        f.write("OUTP ON")

    def _set_tension(self, f, V):
        V = min(max(V, 0.0), self.V_max_hard)     # nunca pasar el tope duro
        # TODO(lab): ajustar a los comandos de TU fuente
        f.write("VOLT %.4f" % V)

    def aplicar(self, u):
        Va, Vb = control_a_tensiones(u, self.geom, self.V_bias, self.V_max)
        self._set_tension(self.fa, Va)
        self._set_tension(self.fb, Vb)
        return Va, Vb, fuerza.fuerza_neta(Va, Vb, self.geom)

    def reposo(self):
        self._set_tension(self.fa, self.V_bias)
        self._set_tension(self.fb, self.V_bias)

    def cerrar(self):
        try:
            for f in (self.fa, self.fb):
                f.write("OUTP OFF")   # TODO(lab): ajustar
                f.close()
        except Exception:
            pass
