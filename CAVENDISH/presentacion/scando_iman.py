# %%
import os
import glob
import re
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from scipy.signal import find_peaks, medfilt, butter, filtfilt
from matplotlib.backends.backend_pdf import PdfPages

# plt.style.use("seaborn-v0_8")
plt.style.use("windows7_aero.mplstyle")

fontsize = 15
plt.rcParams.update(
    {
        "font.size": fontsize,
        "axes.labelsize": fontsize,
        "axes.titlesize": fontsize,
        "xtick.labelsize": fontsize,
        "ytick.labelsize": fontsize,
        "legend.fontsize": fontsize,
        "mathtext.fontset": "cm",
        "legend.frameon": True,
    }
)


w = {"amarillo": "#F3AA0C", "verde": "#055E49", "violeta": "#35274A", "rojo": "#F2300F"}

colores = [
    "#3D6DA8",
    "#1AA3A3",
    "#6B8E4E",
    "#E08A3C",
    "#7E5C8A",
    "#B5444B",
    "#B5338C",
    "#6E7F8D",
]


def a_minutos(x, pos):
    return f"{x / 60:.1f}"


formato_minutos = ticker.FuncFormatter(a_minutos)
nro_medicion = 26

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
masa_times = sorted(float(v) for k, v in meta.items() if re.match(r"masa_\d+_s$", k))

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
x_mm = datos[:, 1]  # posición X (mm)
y_mm = datos[:, 2]  # posición Y (mm)
rango = (t >= 0) & (t <= 125 * 60)

saltear = 12
t = t[rango][::saltear]
x_mm = x_mm[rango][::saltear]
y_mm = y_mm[rango][::saltear]

# ---------- mm -> grados (palanca óptica) ----------
# El haz se refleja en el espejo del péndulo: si el espejo gira θ, el haz se desvía 2θ.
# Por eso el ángulo del PÉNDULO = ángulo del haz / 2  (poné 1 si querés el ángulo del haz).
FACTOR_ESPEJO = 2.0
if not np.isfinite(dist_pantalla_cm):
    raise ValueError("El meta no tiene 'distancia_a_la_pantalla (cm)'.")
L_mm = dist_pantalla_cm * 10.0  # distancia a la pantalla en mm


def mm_a_grados_con_error(v_mm, e_v, L_mm, e_L, FACTOR_ESPEJO=FACTOR_ESPEJO):
    """
    Calcula el ángulo en grados y propaga los errores.

    Parámetros:
    v_mm, L_mm : Valores de las variables.
    e_v, e_L   : Incertidumbres (errores) de v_mm y L_mm.
    FACTOR_ESPEJO : Constante de la función.
    """
    # 1. Calcular el valor central
    angulo = np.degrees(np.arctan(v_mm / L_mm)) / FACTOR_ESPEJO

    # 2. Definir la constante de conversión (incluye el paso a grados)
    C = 180.0 / (np.pi * FACTOR_ESPEJO)

    # 3. Calcular el denominador común de las derivadas
    denominador = L_mm**2 + v_mm**2

    # 4. Derivadas parciales
    deriv_v = C * (L_mm / denominador)
    deriv_L = -C * (v_mm / denominador)

    # 5. Propagación de errores (Fórmula de cuadratura)
    e_angulo = np.sqrt((deriv_v * e_v) ** 2 + (deriv_L * e_L) ** 2)

    return angulo, e_angulo


x_deg, Dx_deg = mm_a_grados_con_error(x_mm, mm_por_px, L_mm, 5)

y_deg, Dy_deg = mm_a_grados_con_error(y_mm, mm_por_px, L_mm, 5)
fig, ax = plt.subplots(figsize=(9, 4), sharex=True)
ax.errorbar(t, x_deg, fmt="--.", lw=0.7, yerr=Dx_deg, label="Datos")
ax.set_ylabel("Ángulo [$^\\circ$]")
ax.grid(alpha=0.5)
ax.set_xlabel("Tiempo [min]")
ax.xaxis.set_major_formatter(formato_minutos)
ax.legend()
hilo = masa_times[0]
ax.axvline(
    hilo,
    color=colores[2],
    ls="--",
    lw=2,
    alpha=0.8,
    label="Límite hilo",
)
ax.legend(loc="upper left")
svg_offset = 0.1
fig.text(
    x=0.25,
    y=0.55,
    s="Con imán",
    fontsize=11,
    color=colores[2],
    weight="bold",
    bbox=dict(facecolor="white", edgecolor=colores[2], boxstyle="round,pad=0.5"),
)

fig.text(
    x=0.55,
    y=0.775,
    s="Sin imán",
    fontsize=11,
    color=colores[2],
    weight="bold",
    bbox=dict(facecolor="white", edgecolor=colores[2], boxstyle="round,pad=0.5"),
)


fig.savefig("figuras/sacando_iman.svg", bbox_inches="tight")
plt.tight_layout()
plt.show()
