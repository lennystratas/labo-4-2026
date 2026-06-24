"""
Calibracion del medidor de posicion  --  TODO CON CLICKS, sin editar archivos.
====================================================================

Abri una ventana con el video en vivo y:

  1) Apreta 'f' SIN laser  -> captura el fondo (resta la luz ambiente).
  2) Pone el laser. Subi el slider "umbral" hasta que se vea SOLO el haz
     (activa la vista 'v' para ver la imagen ya limpia).
  3) Marcadores de escala: apreta '1' y clickea una marca real; apreta '2'
     y clickea otra marca a una distancia CONOCIDA. Subi el slider "dist mm"
     a esa distancia. El mm/px se calcula solo.
  4) Origen: apreta 'o' y clickea donde quieras el cero de la medicion.
  5) Apreta 's' para GUARDAR. Listo: control_loop.py la usa automaticamente.

Teclas:  1 / 2 = marcadores   o = origen   f = fondo   c = borrar fondo
         v = ver imagen limpia   s = guardar   q = salir
"""
import argparse
import math

import numpy as np

import parametros as P
import vision


def _nada(v):
    pass


def _texto(cv2, img, lineas):
    for i, s in enumerate(lineas):
        y = 24 + 22 * i
        cv2.putText(img, s, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(img, s, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)


def _mmpx_seguro(m1, m2, dist):
    if m1 is None or m2 is None:
        return 1.0
    try:
        return vision.mm_por_px(m1, m2, dist)
    except ValueError:
        return 1.0


def main(argv=None):
    import cv2

    ap = argparse.ArgumentParser(description="Calibracion interactiva del medidor")
    ap.add_argument("--fuente", default=None, help="webcam (indice) o ruta de video")
    a = ap.parse_args(argv)

    fuente = a.fuente if a.fuente is not None else P.FUENTE_VIDEO
    try:
        fuente = int(fuente)
    except (TypeError, ValueError):
        pass
    cam = vision.Camara(fuente, P.ANCHO, P.ALTO)

    est = {"m1": None, "m2": None, "origen": None,
           "activo": "m1", "fondo": None, "ver_limpio": False}

    def on_mouse(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            est[est["activo"]] = (x, y)

    win = "Calibracion"
    cv2.namedWindow(win)
    cv2.setMouseCallback(win, on_mouse)
    cv2.createTrackbar("umbral x1000", win, int(P.UMBRAL * 1000), 1000, _nada)
    cv2.createTrackbar("minsig x1000", win, int(P.MINSIG * 1000), 1000, _nada)
    cv2.createTrackbar("dist mm", win, 100, 1000, _nada)

    while True:
        frame = cam.leer()
        if frame is None:
            print("No hay mas frames (o falla la camara).")
            break

        umbral = max(cv2.getTrackbarPos("umbral x1000", win), 0) / 1000.0
        minsig = max(cv2.getTrackbarPos("minsig x1000", win), 0) / 1000.0
        dist = max(cv2.getTrackbarPos("dist mm", win), 1)

        mmpx = _mmpx_seguro(est["m1"], est["m2"], dist)
        origen = est["origen"] if est["origen"] else (0, 0)
        cal = vision.Calibracion(fondo=est["fondo"], umbral=umbral, minsig=minsig,
                                 origen=origen, mmpx=mmpx, roi=None, canal="gris")
        m = vision.medir(frame, cal)

        if est["ver_limpio"]:
            limp = vision.limpiar(vision.a_gris(frame), est["fondo"], umbral)
            img = cv2.cvtColor((np.clip(limp, 0, 1) * 255).astype(np.uint8),
                               cv2.COLOR_GRAY2BGR)
        else:
            img = frame.copy()

        if est["m1"]:
            cv2.circle(img, est["m1"], 6, (0, 0, 255), 2)
        if est["m2"]:
            cv2.circle(img, est["m2"], 6, (255, 0, 0), 2)
        if est["m1"] and est["m2"]:
            cv2.line(img, est["m1"], est["m2"], (0, 255, 255), 1)
        if est["origen"]:
            cv2.drawMarker(img, est["origen"], (0, 255, 255), cv2.MARKER_TILTED_CROSS, 16, 2)
        if m.valido and not math.isnan(m.x_px):
            cv2.drawMarker(img, (int(round(m.x_px)), int(round(m.y_px))),
                           (0, 255, 0), cv2.MARKER_CROSS, 20, 2)

        _texto(cv2, img, [
            "activo: %s   (1=marcador1  2=marcador2  o=origen)" % est["activo"],
            "mm/px = %.4g    dist conocida = %d mm" % (mmpx, dist),
            "x=%s  y=%s  valido=%d  %s" % (
                ("%.3f" % m.x_mm) if m.valido else "--",
                ("%.3f" % m.y_mm) if m.valido else "--",
                int(m.valido), "  SATURADO!" if m.saturado else ""),
            "f=fondo(%s)  c=borrar  v=limpio(%s)  s=GUARDAR  q=salir" % (
                "si" if est["fondo"] is not None else "no",
                "on" if est["ver_limpio"] else "off"),
        ])
        cv2.imshow(win, img)

        k = cv2.waitKey(1) & 0xFF
        if k == ord("q"):
            break
        elif k == ord("1"):
            est["activo"] = "m1"
        elif k == ord("2"):
            est["activo"] = "m2"
        elif k == ord("o"):
            est["activo"] = "origen"
        elif k == ord("f"):
            est["fondo"] = vision.a_gris(frame)
            print("Fondo capturado.")
        elif k == ord("c"):
            est["fondo"] = None
            print("Fondo borrado.")
        elif k == ord("v"):
            est["ver_limpio"] = not est["ver_limpio"]
        elif k == ord("s"):
            if not (est["m1"] and est["m2"] and est["origen"]):
                print("Faltan puntos: marca 1, 2 y origen antes de guardar.")
            else:
                final = vision.Calibracion(
                    fondo=est["fondo"], umbral=umbral, minsig=minsig,
                    origen=(float(origen[0]), float(origen[1])),
                    mmpx=mmpx, roi=None, canal="gris")
                vision.guardar_calibracion(final, P.CARPETA_CALIBRACION)
                print("Calibracion guardada en:", P.CARPETA_CALIBRACION)

    cam.cerrar()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
