"""
Controlador PID para el servo de nulo (mantener el pendulo quieto).
====================================================================

Caracteristicas pensadas para este experimento:

  * dt variable: se le pasa el dt medido en cada vuelta del lazo (el tiempo
    entre frames de la camara no es perfectamente constante).

  * Derivada sobre la MEDICION (no sobre el error): asi un cambio de setpoint
    no produce un "patada" derivativa. Con filtro pasa-bajos opcional para no
    amplificar el ruido de la camara (tau_deriv; por defecto 0 = sin filtro).

  * Anti-windup por integracion condicional: si la salida esta saturada y el
    error empuja todavia mas hacia la saturacion, el integral NO se acumula.
    Asi no se "carga" y el sistema responde apenas el error se da vuelta.

  * mantener(): devuelve la ultima salida SIN integrar. El lazo lo usa cuando
    la medicion de posicion es invalida (laser perdido/saturado), para no
    descontrolar el actuador.
"""


class PID:
    def __init__(self, kp, ki, kd, setpoint=0.0,
                 salida_min=float("-inf"), salida_max=float("+inf"),
                 tau_deriv=0.0):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.setpoint = setpoint
        self.salida_min = salida_min
        self.salida_max = salida_max
        self.tau_deriv = tau_deriv        # constante del filtro de la derivada [s]
        self.reset()

    def reset(self):
        self.integral = 0.0
        self.medicion_prev = None
        self.deriv_filt = 0.0
        self.ultima_salida = 0.0
        # diagnostico: ultimos terminos calculados (utiles para el log)
        self.p_term = self.i_term = self.d_term = 0.0

    def update(self, medicion, dt):
        """Calcula la accion de control para la medicion y el dt dados."""
        if dt <= 0:
            raise ValueError("dt debe ser > 0, se recibio %r" % dt)

        error = self.setpoint - medicion

        # --- derivada sobre la medicion (con filtro opcional) ---
        if self.medicion_prev is None:
            deriv = 0.0
        else:
            raw_d = (medicion - self.medicion_prev) / dt
            if self.tau_deriv > 0.0:
                alpha = dt / (self.tau_deriv + dt)
                self.deriv_filt += alpha * (raw_d - self.deriv_filt)
            else:
                self.deriv_filt = raw_d
            deriv = -self.kd * self.deriv_filt
        self.medicion_prev = medicion

        # --- integral tentativo ---
        integral_tent = self.integral + self.ki * error * dt

        # --- salida sin clampear ---
        p = self.kp * error
        salida_sc = p + integral_tent + deriv

        # --- clamp + anti-windup (integracion condicional) ---
        acumular = True
        if salida_sc > self.salida_max:
            salida = self.salida_max
            if error > 0:           # integrar mas empeoraria la saturacion
                acumular = False
        elif salida_sc < self.salida_min:
            salida = self.salida_min
            if error < 0:
                acumular = False
        else:
            salida = salida_sc

        if acumular:
            self.integral = integral_tent

        # guardar terminos para diagnostico/log
        self.p_term = p
        self.i_term = self.integral
        self.d_term = deriv
        self.ultima_salida = salida
        return salida

    def mantener(self):
        """Devuelve la ultima salida sin integrar (para medicion invalida)."""
        return self.ultima_salida
