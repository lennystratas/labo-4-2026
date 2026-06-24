"""Tests de medicion de posicion (centroide) y matematica de calibracion."""
import math
import tempfile
from _bootstrap import correr
import numpy as np
import vision


# ---------------- centroide ----------------
def test_centroide_de_un_punto():
    I = np.zeros((10, 20))
    I[3, 7] = 1.0                       # fila 3 (y), columna 7 (x)
    x, y, total, pico = vision.centroide(I)
    assert abs(x - 7) < 1e-9 and abs(y - 3) < 1e-9
    assert total == 1.0 and pico == 1.0


def test_centroide_ponderado_por_intensidad():
    I = np.zeros((5, 11))
    I[2, 0] = 1.0
    I[2, 10] = 3.0                      # x = (0*1 + 10*3)/4 = 7.5
    x, y, _, _ = vision.centroide(I)
    assert abs(x - 7.5) < 1e-9 and abs(y - 2) < 1e-9


def test_centroide_total_cero_devuelve_nan():
    x, y, total, _ = vision.centroide(np.zeros((4, 4)))
    assert total == 0.0 and math.isnan(x) and math.isnan(y)


# ---------------- limpieza (fondo + umbral) ----------------
def test_limpiar_resta_fondo_y_aplica_umbral():
    gris = np.array([[0.0, 0.5], [0.8, 0.05]])
    fondo = np.array([[0.0, 0.1], [0.0, 0.0]])
    limpio = vision.limpiar(gris, fondo, umbral=0.2)
    # gris-fondo = [[0,0.4],[0.8,0.05]] ; <0.2 -> 0
    assert limpio[0, 0] == 0.0
    assert abs(limpio[0, 1] - 0.4) < 1e-9
    assert abs(limpio[1, 0] - 0.8) < 1e-9
    assert limpio[1, 1] == 0.0


def test_limpiar_sin_fondo():
    gris = np.array([[0.3, 0.05]])
    limpio = vision.limpiar(gris, None, umbral=0.1)
    assert abs(limpio[0, 0] - 0.3) < 1e-9 and limpio[0, 1] == 0.0


# ---------------- saturacion ----------------
def test_saturacion_detecta_pixel_al_maximo():
    assert vision.hay_saturacion(np.array([[0.5, 1.0]])) is True


def test_sin_saturacion_si_todo_por_debajo():
    assert vision.hay_saturacion(np.array([[0.5, 0.9]]), umbral_sat=0.99) is False


# ---------------- validez ----------------
def test_valido_si_pico_supera_minsig():
    assert vision.es_valido(total=10.0, pico=0.3, minsig=0.1) is True


def test_invalido_si_pico_debajo_de_minsig():
    assert vision.es_valido(total=10.0, pico=0.05, minsig=0.1) is False


# ---------------- calibracion (px <-> mm) ----------------
def test_mm_por_px_horizontal():
    assert abs(vision.mm_por_px((0, 0), (100, 0), 50.0) - 0.5) < 1e-12


def test_mm_por_px_diagonal():
    # distancia pixel = 5, dist conocida = 10 -> 2 mm/px
    assert abs(vision.mm_por_px((0, 0), (3, 4), 10.0) - 2.0) < 1e-12


def test_px_a_mm_resta_origen_y_escala():
    x_mm, y_mm = vision.px_a_mm(30, 20, origen=(10, 20), mmpx=0.5)
    assert abs(x_mm - 10.0) < 1e-12 and abs(y_mm - 0.0) < 1e-12


# ---------------- medir (todo junto) ----------------
def test_medir_punto_brillante():
    frame = np.zeros((10, 20, 3), dtype=np.uint8)
    frame[3, 7, :] = 255
    cal = vision.Calibracion(fondo=None, umbral=0.1, minsig=0.1,
                             origen=(5, 3), mmpx=0.5, roi=None)
    m = vision.medir(frame, cal)
    assert m.valido
    assert abs(m.x_px - 7) < 1e-9 and abs(m.y_px - 3) < 1e-9
    assert abs(m.x_mm - 1.0) < 1e-9 and abs(m.y_mm - 0.0) < 1e-9
    assert m.saturado          # pixel a 255 -> saturacion del sensor


def test_medir_invalido_si_oscuro():
    frame = np.full((10, 20, 3), 10, dtype=np.uint8)   # tenue uniforme
    cal = vision.Calibracion(fondo=None, umbral=0.1, minsig=0.5,
                             origen=(0, 0), mmpx=1.0, roi=None)
    m = vision.medir(frame, cal)
    assert not m.valido


def test_roi_ignora_lo_de_afuera():
    frame = np.zeros((10, 20, 3), dtype=np.uint8)
    frame[3, 7, :] = 255       # dentro del ROI
    frame[8, 18, :] = 255      # fuera del ROI
    cal = vision.Calibracion(fondo=None, umbral=0.1, minsig=0.1,
                             origen=(0, 0), mmpx=1.0, roi=(0, 0, 10, 6))
    m = vision.medir(frame, cal)
    assert abs(m.x_px - 7) < 1e-9 and abs(m.y_px - 3) < 1e-9


def test_calibracion_ida_y_vuelta():
    cal = vision.Calibracion(fondo=np.ones((4, 5)) * 0.2, umbral=0.07, minsig=0.2,
                             origen=(3, 4), mmpx=0.5, roi=(0, 0, 4, 5), canal="r")
    with tempfile.TemporaryDirectory() as d:
        vision.guardar_calibracion(cal, d)
        c2 = vision.cargar_calibracion(d)
    assert abs(c2.umbral - 0.07) < 1e-9 and abs(c2.minsig - 0.2) < 1e-9
    assert c2.origen == (3.0, 4.0) and abs(c2.mmpx - 0.5) < 1e-9
    assert c2.roi == (0, 0, 4, 5) and c2.canal == "r"
    assert c2.fondo is not None and abs(float(c2.fondo.mean()) - 0.2) < 1e-9


if __name__ == "__main__":
    import sys
    sys.exit(correr(globals()))
