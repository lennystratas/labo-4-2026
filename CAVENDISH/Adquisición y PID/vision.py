"""
Medicion de la posicion del laser por centroide ponderado por intensidad.
====================================================================

Pipeline (igual criterio que el de TouchDesigner, ahora en Python puro):

    frame -> gris -> (restar fondo) -> (umbral) -> CENTROIDE -> px -> mm

El centroide es la suma ponderada por intensidad sobre TODOS los pixeles.
NO asume forma del spot (nada de ajustar una gaussiana), coherente con el
criterio de analisis no parametrico.

Fiabilidad:
  * 'valido'  : hay un punto suficientemente brillante (pico > minsig).
  * 'saturado': el sensor satura (pixeles al maximo) -> el centroide se
                sesga; conviene bajar la exposicion. Se reporta como aviso.
  * ROI opcional: ignora reflejos espurios fuera de una ventana.

Convencion de coordenadas: la de la imagen (origen ARRIBA-izquierda, x a la
derecha, y hacia ABAJO). Como el servo trabaja en posicion relativa y la
calibracion fija el origen, la convencion no afecta el control.
"""
from dataclasses import dataclass
import os
import numpy as np


@dataclass
class Calibracion:
    fondo: object = None          # imagen de fondo (gris [0,1]) o None
    umbral: float = 0.08          # se pone a 0 lo que este por debajo [0,1]
    minsig: float = 0.10          # pico minimo para considerar valido [0,1]
    origen: tuple = (0.0, 0.0)    # (x,y) en px del cero de la medicion
    mmpx: float = 1.0             # milimetros por pixel
    roi: object = None            # (x0,y0,x1,y1) en px, o None
    canal: str = "gris"           # 'gris','r','g','b','max' (como leer el color)


@dataclass
class Medicion:
    x_mm: float
    y_mm: float
    x_px: float
    y_px: float
    intensidad: float             # suma total de intensidad (senal)
    pico: float                   # pixel mas brillante
    valido: bool
    saturado: bool


def a_gris(frame, canal="gris"):
    """Convierte un frame a intensidad float en [0,1]. Acepta 2D o 3D (BGR)."""
    a = np.asarray(frame)
    if a.ndim == 3:
        if canal == "gris":
            a = a.mean(axis=2)
        elif canal == "max":
            a = a.max(axis=2)
        else:
            idx = {"b": 0, "g": 1, "r": 2}[canal]   # OpenCV entrega BGR
            a = a[:, :, idx]
    a = a.astype(np.float64)
    if a.size and a.max() > 1.0:        # parece estar en 0..255
        a = a / 255.0
    return a


def limpiar(gris, fondo, umbral):
    """Resta el fondo (si hay), clampea negativos a 0 y pone a 0 lo < umbral."""
    limpio = gris.astype(np.float64)
    if fondo is not None:
        limpio = limpio - fondo
    limpio = np.clip(limpio, 0.0, None)
    limpio[limpio < umbral] = 0.0
    return limpio


def centroide(intensidad):
    """Centro de masa ponderado por intensidad. Devuelve (x_px, y_px, total, pico)."""
    I = np.asarray(intensidad, dtype=np.float64)
    total = float(I.sum())
    pico = float(I.max()) if I.size else 0.0
    if total <= 0.0:
        return float("nan"), float("nan"), total, pico
    H, W = I.shape
    col = I.sum(axis=0)               # perfil horizontal (largo W)
    row = I.sum(axis=1)               # perfil vertical (largo H)
    x = float((col * np.arange(W)).sum() / total)
    y = float((row * np.arange(H)).sum() / total)
    return x, y, total, pico


def hay_saturacion(gris, umbral_sat=0.99):
    """True si algun pixel esta al maximo (el centroide se sesga si satura)."""
    a = np.asarray(gris)
    return bool(a.size and a.max() >= umbral_sat)


def es_valido(total, pico, minsig):
    """Hay laser en pantalla: pico brillante y senal total no nula."""
    return bool(pico > minsig and total > 1e-12)


def mm_por_px(p1, p2, dist_conocida_mm):
    """mm/px = distancia real conocida / distancia en pixeles entre 2 marcadores."""
    dpx = ((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2) ** 0.5
    if dpx <= 0:
        raise ValueError("los dos marcadores no pueden coincidir")
    return dist_conocida_mm / dpx


def px_a_mm(x_px, y_px, origen, mmpx):
    """Pasa de pixeles a mm respecto del origen."""
    return (x_px - origen[0]) * mmpx, (y_px - origen[1]) * mmpx


def _aplicar_roi(gris, roi):
    """Pone a 0 todo lo de afuera del ROI (conserva coordenadas globales)."""
    x0, y0, x1, y1 = roi
    m = np.zeros_like(gris)
    m[y0:y1, x0:x1] = gris[y0:y1, x0:x1]
    return m


def medir(frame, cal):
    """Mide la posicion del laser en un frame. Devuelve una Medicion."""
    gris = a_gris(frame, cal.canal)
    if cal.roi is not None:
        gris = _aplicar_roi(gris, cal.roi)
    saturado = hay_saturacion(gris)
    limpio = limpiar(gris, cal.fondo, cal.umbral)
    x_px, y_px, total, pico = centroide(limpio)
    valido = es_valido(total, pico, cal.minsig)
    if valido:
        x_mm, y_mm = px_a_mm(x_px, y_px, cal.origen, cal.mmpx)
    else:
        x_mm = y_mm = float("nan")
    return Medicion(x_mm, y_mm, x_px, y_px, total, pico, valido, saturado)


# --------------------------------------------------------------------------
# Guardar / cargar calibracion (la escribe la GUI; el lazo la lee)
# Formato legible (NO json): un .txt de "clave<TAB>valor" + el fondo en .npy
# --------------------------------------------------------------------------
def guardar_calibracion(cal, carpeta):
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, "calibracion_valores.txt")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("# calibracion del medidor de posicion (la escribe calibracion.py)\n")
        f.write("umbral\t%.6g\n" % cal.umbral)
        f.write("minsig\t%.6g\n" % cal.minsig)
        f.write("origen_x\t%.6g\n" % cal.origen[0])
        f.write("origen_y\t%.6g\n" % cal.origen[1])
        f.write("mmpx\t%.9g\n" % cal.mmpx)
        f.write("canal\t%s\n" % cal.canal)
        if cal.roi is None:
            f.write("roi\tnone\n")
        else:
            f.write("roi\t%d %d %d %d\n" % tuple(cal.roi))
        f.write("tiene_fondo\t%d\n" % (1 if cal.fondo is not None else 0))
    if cal.fondo is not None:
        np.save(os.path.join(carpeta, "calibracion_fondo.npy"), cal.fondo)


def cargar_calibracion(carpeta):
    d = {}
    with open(os.path.join(carpeta, "calibracion_valores.txt"), encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln or ln.startswith("#"):
                continue
            k, _, v = ln.partition("\t")
            d[k] = v
    roi = None
    if d.get("roi", "none") != "none":
        roi = tuple(int(x) for x in d["roi"].split())
    fondo = None
    if int(d.get("tiene_fondo", "0")):
        fondo = np.load(os.path.join(carpeta, "calibracion_fondo.npy"))
    return Calibracion(
        fondo=fondo,
        umbral=float(d["umbral"]),
        minsig=float(d["minsig"]),
        origen=(float(d["origen_x"]), float(d["origen_y"])),
        mmpx=float(d["mmpx"]),
        roi=roi,
        canal=d.get("canal", "gris"),
    )


# --------------------------------------------------------------------------
# Captura de la camara / video (I/O; usa OpenCV, import diferido)
# --------------------------------------------------------------------------
class Camara:
    """Fuente de frames: webcam (indice) o archivo de video (ruta)."""

    def __init__(self, fuente=0, ancho=None, alto=None):
        import cv2  # import diferido: no se necesita para los tests/funciones puras
        self._cv2 = cv2
        self.cap = cv2.VideoCapture(fuente)
        if ancho:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, ancho)
        if alto:
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, alto)
        if not self.cap.isOpened():
            raise RuntimeError("no se pudo abrir la fuente de video: %r" % fuente)

    def leer(self):
        """Devuelve el ultimo frame (BGR) o None si no hay."""
        ok, frame = self.cap.read()
        return frame if ok else None

    def cerrar(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None
