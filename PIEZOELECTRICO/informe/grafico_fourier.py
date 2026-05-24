# %%
import numpy as np
from matplotlib import ticker
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.metrics import r2_score
from scipy.optimize import curve_fit
import os


plt.style.use("seaborn-v0_8")

fontsize = 15
plt.rcParams.update(
    {
        "font.family": "serif",
        "font.size": fontsize,
        "axes.labelsize": fontsize,
        "axes.titlesize": fontsize,
        "xtick.labelsize": 14,
        "ytick.labelsize": 14,
        "legend.fontsize": 14,
        "mathtext.default": "regular",
        "mathtext.fontset": "cm",
        "legend.frameon": True,
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
image_folder = base_path + "informe/figuras/"


# %%
def select_data():
    df = pd.read_csv(save_folder + "respuesta_pulso_8.csv", index_col=["Tiempo"])
    return df


f1 = 50097
# %%
df = select_data()
t = df.index.values
dt = np.mean(np.diff(t))
V1 = df["VoltajeCH1"]
V2 = df["VoltajeCH2"]
n_points = 6000

fft_amp = np.abs(np.fft.rfft(V2, n_points))
fft_frec = np.fft.rfftfreq(n_points, d=dt)
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
ax.set_xlim(-2e3, 270e3)
# ax.set_xlim(1e3, np.max(fft_frec))
ax.set_yscale("log")
ax.xaxis.set_major_formatter(formatok)
ax.vlines(
    [i * f1 for i in range(1, 11)],
    0,
    np.max(fft_amp),
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
ax.set_xlabel("Frecuencia [kHz]")
ax.set_ylabel("Módulo DFT [u.a.]")
ax.legend(loc=9)
fig.savefig(image_folder + f"grafico_fourier.pdf", bbox_inches="tight")
