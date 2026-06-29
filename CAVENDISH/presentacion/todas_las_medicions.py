# %% Imports, agarrar datos
import os
import glob
import re
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from scipy.signal import find_peaks, medfilt, butter, filtfilt
from matplotlib.backends.backend_pdf import PdfPages

plt.style.use("seaborn-v0_8")

fontsize = 15
plt.rcParams.update(
    {
        "font.family": "serif",
        "font.size": fontsize,
        "axes.labelsize": fontsize,
        "axes.titlesize": fontsize,
        "xtick.labelsize": fontsize,
        "ytick.labelsize": fontsize,
        "legend.fontsize": fontsize,
        "mathtext.default": "regular",
        "mathtext.fontset": "cm",
        "legend.frameon": True,
    }
)


w = {"amarillo": "#F3AA0C", "verde": "#055E49", "violeta": "#35274A", "rojo": "#F2300F"}


def a_minutos(x, pos):
    return f"{x / 60:.1f}"


formato_minutos = ticker.FuncFormatter(a_minutos)


def graficar_medicion(nro_medicion):
    # >>> Elegí la medición a graficar (carpeta dentro de Datos) <<<
    CARPETA = os.path.join(
        "..",
        "Datos",
        f"medicion{'0' + str(nro_medicion) if nro_medicion < 10 else nro_medicion}",
    )

    # ---------- leer metadatos ----------
    meta = {}
    _metas = glob.glob(os.path.join(CARPETA, "*_meta.txt"))
    if _metas:
        with open(_metas[0]) as fh:
            for line in fh:
                line = line.strip()
                if "\t" in line and not line.startswith("#"):
                    k, v = line.split("\t", 1)
                    meta[k] = v

    def _mget(clave, cast=float, default=np.nan):
        try:
            return cast(meta[clave])
        except Exception:
            return default

    # ---------- variables de metadata ----------
    fecha = meta.get("fecha", "")
    mm_por_px = _mget("mm_por_px")
    width_px = _mget("width_px", int, 0)
    height_px = _mget("height_px", int, 0)
    umbral = _mget("umbral")
    guardar_cada_s = _mget("guardar_cada_s")
    dist_pantalla_cm = _mget("distancia_a_la_pantalla (cm)")

    # instantes (s) en que se agregó masa -> líneas verticales
    masa_times = sorted(
        float(v) for k, v in meta.items() if re.match(r"masa_\d+_s$", k)
    )

    print("medición:", os.path.basename(CARPETA))
    for k in (
        "fecha",
        "mm_por_px",
        "width_px",
        "height_px",
        "umbral",
        "guardar_cada_s",
    ):
        print(f"  {k:16s}= {meta.get(k, '(falta)')}")
    print(f"  dist_pantalla_cm= {dist_pantalla_cm}")
    print(f"  masa_times (s)  = {masa_times}")

    # helper: marca líneas verticales en los instantes de las masas
    def marcar_masas(ax):
        for i, tm in enumerate(masa_times):
            ax.axvline(
                tm,
                color="red",
                ls="--",
                lw=1.2,
                alpha=0.8,
                label=("masa" if i == 0 else None),
            )

    # Chunks de datos, ordenados por su índice nnnn (NO alfabético). Excluye el _meta.
    archivos = glob.glob(os.path.join(CARPETA, "*_[0-9][0-9][0-9][0-9].txt"))
    archivos.sort(key=lambda f: int(re.search(r"_(\d+)\.txt$", f).group(1)))
    print(f"{len(archivos)} archivos encontrados")
    print(archivos[:3], "...", archivos[-3:])

    # Concatena todos los chunks en orden -> curva completa
    datos = []
    for f in archivos:
        a = np.atleast_2d(np.loadtxt(f, delimiter="\t"))
        if a.size:  # ignora chunks vacíos
            datos.append(a)
    datos = np.concatenate(datos, axis=0)
    print("shape:", datos.shape, "(filas, columnas)")
    datos[:5]

    t = datos[:, 0]  # tiempo (s)
    t -= t[0]
    x_mm = datos[:, 1]  # posición X (mm)
    y_mm = datos[:, 2]  # posición Y (mm)

    # ---------- mm -> grados (palanca óptica) ----------
    # El haz se refleja en el espejo del péndulo: si el espejo gira θ, el haz se desvía 2θ.
    # Por eso el ángulo del PÉNDULO = ángulo del haz / 2  (poné 1 si querés el ángulo del haz).
    FACTOR_ESPEJO = 2.0
    if not np.isfinite(dist_pantalla_cm):
        raise ValueError("El meta no tiene 'distancia_a_la_pantalla (cm)'.")
    L_mm = dist_pantalla_cm * 10.0  # distancia a la pantalla en mm

    def mm_a_grados(v_mm):
        return np.degrees(np.arctan(v_mm / L_mm)) / FACTOR_ESPEJO

    x_deg = mm_a_grados(x_mm)
    y_deg = mm_a_grados(y_mm)

    fig, ax = plt.subplots(figsize=(8, 4), sharex=True)
    ax.plot(t, x_deg, lw=0.7)
    ax.set_ylabel("x (grados)")
    ax.grid(alpha=0.3)
    ax.set_xlabel("Tiempo [min]")
    ax.xaxis.set_major_formatter(formato_minutos)
    marcar_masas(ax)

    if masa_times:
        ax.legend(loc="upper right")
    fig.suptitle(f"{os.path.basename(CARPETA)} — {len(t)} muestras, {t[-1]:.1f} s")
    return fig, ax


def save_figs_to_pdf(fig_ax_pairs, filename="output.pdf"):
    """
    Saves a list of (fig, ax) pairs into a single multi-page PDF.

    Parameters:
    - fig_ax_pairs: List of tuples, e.g., [(fig1, ax1), (fig2, ax2), ...]
    - filename: The output PDF file path.
    """
    if not fig_ax_pairs:
        print("No figures provided to save.")
        return

    # Use a context manager to automatically close the PDF when done
    with PdfPages(filename) as pdf:
        for fig, ax in fig_ax_pairs:
            # Save the current figure to a new page in the PDF
            # 'bbox_inches="tight"' ensures labels aren't cut off
            pdf.savefig(fig, bbox_inches="tight")

    print(f"Successfully saved {len(fig_ax_pairs)} pages to '{filename}'")


# %% Guardar
figuras = []
# excluir = [10, 11, 12, 13, 14]
for med in range(1, 31):
    # if med not in excluir:
    figuras.append(graficar_medicion(med))
save_figs_to_pdf(figuras, "todas_las_mediciones.pdf")
