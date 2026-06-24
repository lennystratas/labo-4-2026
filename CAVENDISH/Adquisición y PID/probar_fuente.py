"""
Diagnostico de comunicacion con la fuente Hantek PPS2320A.
====================================================================

El log del lazo muestra la tension que el PID PIDE, no lo que la fuente
confirma -> aunque la comunicacion falle, el log "cambia". Este script
LEE DE VUELTA de la fuente (comandos 'ru'/'rk') para confirmar de verdad.

Uso:
  python probar_fuente.py                          # lista los puertos serie
  python probar_fuente.py --puerto COM3            # diagnostico a 9600
  python probar_fuente.py --puerto COM3 --barrer   # prueba varios bauds
  python probar_fuente.py --puerto COM3 --backend visa     # probar pyvisa
  python probar_fuente.py --puerto COM3 --dtr off --rts off # togglear lineas
"""
import argparse
import time

import actuador as A

BAUDS = [9600, 115200, 57600, 38400, 19200, 4800, 2400]


def listar_puertos():
    try:
        from serial.tools import list_ports
    except ImportError:
        print("Falta pyserial.  Instala con:  pip install pyserial")
        return
    puertos = list(list_ports.comports())
    if not puertos:
        print("No se detectan puertos serie. Conecta la fuente por USB.")
        return
    print("Puertos serie detectados:")
    for p in puertos:
        print("  %-8s %s  [%s]" % (p.device, p.description, p.hwid))


def _abrir(puerto, baud, backend, dtr, rts, espera):
    try:
        return A.abrir_transporte(puerto, baud, backend, dtr=dtr, rts=rts, espera=espera)
    except ImportError:
        if backend == "visa":
            print("Falta pyvisa.  Instala con:  pip install pyvisa pyvisa-py")
        else:
            print("Falta pyserial.  Instala con:  pip install pyserial")
        raise SystemExit(1)


def barrer(puerto, backend, dtr, rts, espera):
    print("Barriendo bauds en %s (%s), buscando respuesta a 'a' (modelo)...\n"
          % (puerto, backend))
    responden = []
    for baud in BAUDS:
        try:
            t = _abrir(puerto, baud, backend, dtr, rts, min(espera, 0.6))
        except SystemExit:
            return
        except Exception as e:
            print("  %-7d no abre: %s" % (baud, e))
            continue
        try:
            t.escribir("a")
            time.sleep(0.3)
            r = t.leer_linea()
        except Exception:
            r = ""
        finally:
            t.cerrar()
        print("  %-7d respuesta = %r%s" % (baud, r, "   <-- RESPONDE!" if r else ""))
        if r:
            responden.append(baud)
    print()
    if responden:
        print("Baud(s) que responden:", responden,
              "-> poné ese en parametros.py (BAUD_FUENTE)")
    else:
        print("Ninguno respondio. Probá: otro --puerto, --backend visa, "
              "o --dtr off / --rts off.")


def diagnostico(puerto, baud, backend, dtr, rts, espera, vmax):
    print("== Diagnostico %s @ %d (%s)  dtr=%s rts=%s espera=%ss ==\n"
          % (puerto, baud, backend, dtr, rts, espera))
    try:
        t = _abrir(puerto, baud, backend, dtr, rts, espera)
    except SystemExit:
        return

    def cmd(c):
        t.escribir(c)

    def q(c, pausa=0.25):
        t.escribir(c)
        time.sleep(pausa)
        return t.leer_linea()

    try:
        modelo = q("a")
        print("modelo (a)             :", repr(modelo),
              "" if modelo else "  <- VACIO: revisá baud/puerto/DTR/backend")
        print("CH1 preset antes  (ru) :", repr(q("ru")))

        c1 = A.comando_tension(1, 5.0, vmax)
        print("-> set CH1 = 5.00 V    (envio %r)" % c1)
        cmd(c1)
        time.sleep(0.4)
        print("CH1 preset despues(ru) :", repr(q("ru")), "  (deberia reflejar 5.00 V)")

        c2 = A.comando_tension(2, 3.0, vmax)
        print("-> set CH2 = 3.00 V    (envio %r)" % c2)
        cmd(c2)
        time.sleep(0.4)
        print("CH2 preset despues(rk) :", repr(q("rk")), "  (deberia reflejar 3.00 V)")

        print("-> salida ON (O1)")
        cmd("O1")
        time.sleep(0.4)
        print("CH1 medida        (rv) :", repr(q("rv")))
        print("CH2 medida        (rh) :", repr(q("rh")))

        # restaurar: 0 V y salida OFF
        cmd(A.comando_tension(1, 0.0, vmax))
        cmd(A.comando_tension(2, 0.0, vmax))
        cmd("O0")
    finally:
        t.cerrar()

    print("\nInterpretacion:")
    print("  * Si 'modelo' trae texto y 'preset despues' refleja lo seteado -> COMUNICACION OK.")
    print("  * Si sale todo vacio -> probá --barrer, --backend visa, o --dtr off / --rts off.")


def main():
    ap = argparse.ArgumentParser(description="Diagnostico de la fuente Hantek PPS2320A")
    ap.add_argument("--puerto", help="p.ej. COM3 (sin esto, lista los puertos)")
    ap.add_argument("--baud", type=int, default=9600)
    ap.add_argument("--backend", choices=["serial", "visa"], default="serial")
    ap.add_argument("--barrer", action="store_true", help="probar varios bauds")
    ap.add_argument("--dtr", choices=["on", "off"], default=None, help="forzar DTR")
    ap.add_argument("--rts", choices=["on", "off"], default=None, help="forzar RTS")
    ap.add_argument("--espera", type=float, default=2.0, help="segundos tras abrir el puerto")
    ap.add_argument("--vmax", type=float, default=30.0)
    a = ap.parse_args()

    if not a.puerto:
        listar_puertos()
        print("\nUso:")
        print("  python probar_fuente.py --puerto COM3            # diagnostico a 9600")
        print("  python probar_fuente.py --puerto COM3 --barrer   # probar varios bauds")
        print("  python probar_fuente.py --puerto COM3 --backend visa")
        print("  python probar_fuente.py --puerto COM3 --dtr off --rts off")
        return

    dtr = None if a.dtr is None else (a.dtr == "on")
    rts = None if a.rts is None else (a.rts == "on")
    if a.barrer:
        barrer(a.puerto, a.backend, dtr, rts, a.espera)
    else:
        diagnostico(a.puerto, a.baud, a.backend, dtr, rts, a.espera, a.vmax)


if __name__ == "__main__":
    main()
