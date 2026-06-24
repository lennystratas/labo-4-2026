# =====================================================================
#  PARAMETROS  --  el UNICO archivo donde tocas numeros a mano.
#  Solo cambias el valor despues del "=".  No hay llaves ni comillas raras.
#  La CALIBRACION de la camara (marcadores, origen, umbral) NO va aca:
#  se hace clickeando en la ventana de  calibracion.py  y se guarda sola.
# =====================================================================
import os

_AQUI = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------------
#  CAMARA / VIDEO
# ---------------------------------------------------------------------
FUENTE_VIDEO = 0          # 0 = primera webcam ; 1 = segunda ; o "ruta\\al\\video.mp4"
ANCHO = 1280              # resolucion pedida a la camara [px]
ALTO  = 720
EJE   = "x"              # eje que se controla: "x" (horizontal/torsion) o "y"


# ---------------------------------------------------------------------
#  GEOMETRIA DE LOS CAPACITORES   (Fig.13)   ***PLACEHOLDERS: ajustar!***
#  Fuerza lateral por capacitor:  F = FACTOR * eps_r * eps0 * V^2 * b / d
# ---------------------------------------------------------------------
B_ANCHO_PLACA     = 0.05     # b: ancho de la placa [m]
D_SEPARACION      = 0.001    # d: separacion entre placas [m]
BRAZO             = 0.02     # distancia del capacitor al eje de giro [m]
N_CAPS_POR_FUENTE = 2        # cada fuente alimenta 2 capacitores (actuan juntos)
EPS_R             = 1.0      # permitividad relativa (1.0 = aire/vacio)
FACTOR_FORMULA    = 1.0      # 1.0 = formula de la guia ; 0.5 = convencion con 1/2


# ---------------------------------------------------------------------
#  FUENTES DE TENSION
# ---------------------------------------------------------------------
V_MAX  = 30.0            # tension maxima de cada fuente [V]
V_BIAS = 21.2            # tension de reposo (bias) [V]. Optimo ~ V_MAX/raiz(2)=21.2
                         # para rango simetrico de empuje en ambos sentidos.

# Direcciones VISA de las 2 fuentes (se ven con pyvisa; completar en el lab):
RECURSO_FUENTE_A = "USB0::0x0000::0x0000::SN_A::INSTR"
RECURSO_FUENTE_B = "USB0::0x0000::0x0000::SN_B::INSTR"


# ---------------------------------------------------------------------
#  PID   (la salida es un comando en [-1, 1] = fraccion de la fuerza maxima)
# ---------------------------------------------------------------------
#  OJO: estos valores quedaron VALIDADOS en el simulador (ver verificacion.png)
#  y sirven de PUNTO DE PARTIDA. En el laboratorio el periodo del pendulo, la
#  palanca optica (mm por radian) y la escala de fuerza son distintos, asi que
#  habra que reajustarlos. Como reajustar, en el README (seccion "Tuneo").
KP = 2.8                 # proporcional  [comando / mm]
KI = 0.8                 # integral      [comando / (mm*s)]  -> saca el error de regimen
KD = 5.6                 # derivativo    [comando / (mm/s)]  -> amortigua (clave!)
TAU_DERIV = 0.3          # filtro de la derivada [s] (0 = sin filtro)
SETPOINT_MM = 0.0        # posicion objetivo (el "nulo"). Normalmente 0.


# ---------------------------------------------------------------------
#  MEDICION (valores por defecto; el fino se ajusta en calibracion.py)
# ---------------------------------------------------------------------
UMBRAL = 0.08            # pone a 0 lo que este por debajo (0..1)
MINSIG = 0.10            # pico minimo para dar la medicion por valida (0..1)


# ---------------------------------------------------------------------
#  ARCHIVOS
# ---------------------------------------------------------------------
CARPETA_CALIBRACION = os.path.join(_AQUI, "calibracion")          # la escribe calibracion.py
CARPETA_DATOS       = os.path.normpath(os.path.join(_AQUI, "..", "Datos"))
PERIODO_CHUNK_S     = 60      # cada cuantos segundos se vuelca un chunk a disco
