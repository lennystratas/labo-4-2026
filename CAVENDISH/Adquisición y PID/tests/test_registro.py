"""Tests del registro de datos en chunks (compatible con Datos/)."""
import os
import tempfile
from _bootstrap import correr
import numpy as np
import registro

COLS = ["t_s", "x_mm", "y_mm"]


def test_crea_carpeta_medicion00():
    with tempfile.TemporaryDirectory() as base:
        r = registro.Registro(base, COLS, periodo_chunk_s=60)
        assert os.path.isdir(r.carpeta)
        assert os.path.basename(r.carpeta) == "medicion00"
        r.cerrar()


def test_numero_de_medicion_incrementa():
    with tempfile.TemporaryDirectory() as base:
        r0 = registro.Registro(base, COLS); r0.cerrar()
        r1 = registro.Registro(base, COLS); r1.cerrar()
        assert os.path.basename(r0.carpeta) == "medicion00"
        assert os.path.basename(r1.carpeta) == "medicion01"


def test_flush_por_tiempo():
    with tempfile.TemporaryDirectory() as base:
        r = registro.Registro(base, ["t_s", "x_mm"], periodo_chunk_s=1.0)
        r.agregar([0.0, 1.0])
        r.agregar([0.5, 2.0])
        chunk0 = os.path.join(r.carpeta, "medicion00_0000.txt")
        assert not os.path.exists(chunk0)         # todavia no flush
        r.agregar([1.0, 3.0])                      # t>=1 -> flush
        assert os.path.exists(chunk0)
        data = np.loadtxt(chunk0)
        assert data.shape == (3, 2)
        r.cerrar()


def test_cerrar_hace_flush_del_resto():
    with tempfile.TemporaryDirectory() as base:
        r = registro.Registro(base, ["t_s", "x_mm"], periodo_chunk_s=100)
        r.agregar([0.0, 5.0]); r.agregar([1.0, 6.0])
        r.cerrar()
        data = np.loadtxt(os.path.join(r.carpeta, "medicion00_0000.txt"))
        assert data.shape == (2, 2)


def test_header_comentado_y_tab_separado():
    with tempfile.TemporaryDirectory() as base:
        r = registro.Registro(base, ["t_s", "x_mm", "valido"], periodo_chunk_s=100)
        r.agregar([0.0, 176.741837, 1])
        r.cerrar()
        with open(os.path.join(r.carpeta, "medicion00_0000.txt")) as f:
            lineas = f.read().splitlines()
        assert lineas[0].startswith("#")
        assert "t_s" in lineas[0] and "valido" in lineas[0]
        vals = lineas[1].split("\t")
        assert abs(float(vals[1]) - 176.741837) < 1e-6
        assert vals[2] == "1"


def test_escribe_meta():
    with tempfile.TemporaryDirectory() as base:
        r = registro.Registro(base, COLS, meta={"comentario": "prueba"})
        meta = os.path.join(r.carpeta, "medicion00_meta.txt")
        assert os.path.exists(meta)
        txt = open(meta).read()
        assert "columnas" in txt and "comentario" in txt
        r.cerrar()


if __name__ == "__main__":
    import sys
    sys.exit(correr(globals()))
