# %%
import numpy as np
from matplotlib import ticker
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.metrics import r2_score
from scipy.optimize import curve_fit
import os

plt.style.use("seaborn-v0_8")

fontsize = 13
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
        "legend.fontsize": 13,
    }
)

w = {"amarillo": "#F3AA0C", "verde": "#055E49", "violeta": "#35274A", "rojo": "#F2300F"}


def get_base_path():
    paths = [
        "C:/Users/publico/Documents/l4-g6-2026-1C/piezo/",  # compu labo
        "C:/Users/olive/Documents/labo-4-2026/PIEZOELECTRICO/",  # Oli
        "C:/Users/lenny/OneDrive/Documents/FISICA/LABO 4/labo-4-2026/PIEZOELECTRICO/",  # Lenny
    ]
    for path in paths:
        if os.path.isdir(path):
            return path
    else:
        raise OSError("None of the paths are valid")


def formato_kilo(valor, posicion):
    # Dividimos entre 1000 y le decimos que muestre 1 decimal (.1f)
    return f"{valor / 1000:.0f}"


def formato_exp(valor, posicion):
    if valor == 0:
        return "0"
    else:
        return f"{valor * 1000:.0f}e-3"


formatok = ticker.FuncFormatter(formato_kilo)
formato_1e = ticker.FuncFormatter(formato_exp)

base_path = get_base_path()

save_folder = base_path + "datos/"
image_folder = base_path + "poster/figuras/"


# %%
def select_data():
    df = pd.read_csv(save_folder + "respuesta_pulso_8.csv", index_col=["Tiempo"])
    return df


f1 = 50097
# %%
df = select_data()
t = df.index.values
fig, ax1 = plt.subplots(figsize=(6, 3))
dt = np.mean(np.diff(t))
V1 = df["VoltajeCH1"]
V2 = df["VoltajeCH2"]
n_points = 6000
fft_amp = np.abs(np.fft.rfft(V2, n_points))
fft_frec = np.fft.rfftfreq(n_points, d=dt)

fig, axs = plt.subplots(
    1,
    2,
    sharey=True,
    figsize=(9, 3),
    gridspec_kw={"wspace": 0.05},
)
ax1, ax2 = axs
ax1.plot(
    fft_frec,
    fft_amp,
    "--.",
    color=w["verde"],
    zorder=10,
    label="DFT",
)
ax1.set_xlim(80e3, 170e3)
ax1.xaxis.set_major_formatter(formatok)
ax1.set_ylim(0, 0.7)
ax1.vlines(2 * f1, 0, 0.45, label="$f_{esp}$ modo 2", linestyles="--", color=w["rojo"])
ax1.vlines(
    3 * f1,
    0,
    0.45,
    label="$f_{esp}$ modo 3 = 100 kHz",
    linestyles="--",
    color=w["amarillo"],
)
ax1.set_xlabel("Frecuencia [ kHz ]")
ax1.set_ylabel("Módulo DFT [ u.a. ]")
ax1.legend(loc=9)


ax2.plot(
    fft_frec,
    fft_amp,
    "--.",
    color=w["verde"],
    zorder=10,
    label="DFT",
)
ax2.set_xlim(180e3, 270e3)
ax2.xaxis.set_major_formatter(formatok)
# ax2.set_ylim(0, 1)
ax2.vlines(2 * f1, 0, 0.45, label="$f_{esp}$ modo 2", linestyles="--", color=w["rojo"])
ax2.vlines(
    3 * f1,
    0,
    0.45,
    label="$f_{esp}$ modo 3 = 100 kHz",
    linestyles="--",
    color=w["amarillo"],
)
ax2.set_xlabel("Frecuencia [ kHz ]")
# ax.set_ylabel("Módulo DFT [ u.a. ]")
# ax1.legend(loc=9)


# plt.vlines(150159, 0, 0.45, label="$f_{med}$ modo 3", linestyles="--", color="purple")
# %%

fig, ax = plt.subplots(
    1,
    1,
    figsize=(9, 3),
)
ax.plot(
    fft_frec,
    fft_amp,
    "--.",
    color=w["verde"],
    zorder=10,
    label="DFT",
)
ax.set_xlim(80e3, 270e3)
ax.xaxis.set_major_formatter(formatok)
ax.set_ylim(0, 0.7)
ax.vlines(
    [i * f1 for i in range(2, 6)],
    0,
    0.7,
    label="$f_{esp}$ modos 2-5",
    linestyles="--",
    color=w["rojo"],
)
# ax.vlines(
#     3 * f1,
#     0,
#     0.45,
#     label="$f_{esp}$ modo 3 = 100 kHz",
#     linestyles="--",
#     color=w["amarillo"],
# )
ax.set_xlabel("Frecuencia [ kHz ]")
ax.set_ylabel("Módulo DFT [ u.a. ]")
ax.legend(loc=9)
fig.savefig(image_folder + f"grafico_fourier.svg", bbox_inches="tight")
