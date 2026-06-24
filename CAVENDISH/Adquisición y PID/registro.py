"""
Registro de datos en chunks, compatible con la carpeta Datos/ existente.
====================================================================

Crea Datos/medicionNN/ (NN autoincremental) y va guardando:
  * medicionNN_meta.txt    : metadatos (fecha, columnas, calibracion...)
  * medicionNN_0000.txt    : chunks de datos, tab-separated.
    Cada chunk arranca con una linea de encabezado COMENTADA (#...), que
    numpy.loadtxt ignora. Las 3 primeras columnas son t_s, x_mm, y_mm para
    seguir siendo compatible con el analisis previo.

El flush a disco se hace cada 'periodo_chunk_s' (segun la columna de tiempo,
fila[0]) y tambien al cerrar -> nunca se pierden datos.
"""
import datetime
import os


def _siguiente_medicion(base):
    """Devuelve (nn, ruta) de la primer medicionNN que no existe en base."""
    nn = 0
    while True:
        ruta = os.path.join(base, "medicion%02d" % nn)
        if not os.path.exists(ruta):
            return nn, ruta
        nn += 1


def _fmt(v):
    """Formatea un valor para el archivo (floats con buena precision)."""
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, float):
        return "%.9g" % v
    return str(v)


class Registro:
    def __init__(self, carpeta_base, columnas, periodo_chunk_s=60.0, meta=None):
        self.columnas = list(columnas)
        self.periodo = periodo_chunk_s
        self.nn, self.carpeta = _siguiente_medicion(carpeta_base)
        os.makedirs(self.carpeta)
        self.chunk = 0
        self.buffer = []
        self._escribir_meta(meta or {})

    def _escribir_meta(self, meta):
        ruta = os.path.join(self.carpeta, "medicion%02d_meta.txt" % self.nn)
        with open(ruta, "w", encoding="utf-8") as f:
            f.write("# metadatos de la medicion\n")
            f.write("fecha\t%s\n" %
                    datetime.datetime.now().isoformat(timespec="seconds"))
            f.write("columnas\t%s\n" % "\t".join(self.columnas))
            for k, v in meta.items():
                f.write("%s\t%s\n" % (k, v))

    def agregar(self, fila):
        """Agrega una fila (lista del mismo largo que columnas)."""
        if len(fila) != len(self.columnas):
            raise ValueError("la fila tiene %d valores y hay %d columnas"
                             % (len(fila), len(self.columnas)))
        self.buffer.append(fila)
        t = fila[0]
        if self.periodo > 0 and t >= (self.chunk + 1) * self.periodo:
            self._flush()
            self.chunk += 1

    def _flush(self):
        if not self.buffer:
            return
        ruta = os.path.join(self.carpeta,
                            "medicion%02d_%04d.txt" % (self.nn, self.chunk))
        with open(ruta, "w", encoding="utf-8") as f:
            f.write("# " + "\t".join(self.columnas) + "\n")
            for fila in self.buffer:
                f.write("\t".join(_fmt(v) for v in fila) + "\n")
        self.buffer = []

    def cerrar(self):
        """Hace flush del ultimo chunk parcial."""
        self._flush()
