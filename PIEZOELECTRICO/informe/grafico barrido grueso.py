# %% AJUSTES
from matplotlib import ticker
from mpl_toolkits.axes_grid1.inset_locator import inset_axes, mark_inset
import numpy as np
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
        "xtick.labelsize": fontsize - 1,
        "ytick.labelsize": fontsize - 1,
        "legend.fontsize": fontsize - 1,
        "mathtext.default": "regular",
        "mathtext.fontset": "cm",
        "legend.frameon": True,
        # "xtick.labelsize": 14,
        # "ytick.labelsize": 14,
        # "legend.fontsize": 14,
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


def get_base_path():
    paths = [
        "C:/Users/publico/Documents/l4-g6-2026-1C/labo-4-2026/PIEZOELECTRICO/",  # compu labo
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
    return f"{valor / 1000:.2f}"


formatok = ticker.FuncFormatter(formato_kilo)


def seno(t, A, f, phi):
    return A * np.sin(2 * np.pi * f * t + phi * np.pi / 180)


base_path = get_base_path()

save_folder = base_path + "datos/"
image_folder = base_path + "figuras/"


# %% ARCHIVOS
def select_data(filtro):
    if filtro == "grueso":
        df1 = pd.read_csv(
            save_folder + "barrido_osciloscopio_1.csv",
            index_col=["Frecuencias", "Tiempo"],
        )
        df2 = pd.read_csv(
            save_folder + "barrido_osciloscopio_2.csv",
            index_col=["Frecuencias", "Tiempo"],
        )
        df = pd.concat([df1, df2])
    elif filtro == "fino":
        df1 = pd.read_csv(
            save_folder + "barrido_osciloscopio_fino_1.csv",
            index_col=["Frecuencias", "Tiempo"],
        )
        df2 = pd.read_csv(
            save_folder + "barrido_osciloscopio_fino_2.csv",
            index_col=["Frecuencias", "Tiempo"],
        )
        df3 = pd.read_csv(
            save_folder + "barrido_osciloscopio_fino_3v2.csv",
            index_col=["Frecuencias", "Tiempo"],
        )
        df = pd.concat([df1, df2, df3])
    elif filtro == "m3":
        df1 = pd.read_csv(
            save_folder + "barrido_osciloscopio_m3_1.csv",
            index_col=["Frecuencias", "Tiempo"],
        )
        df2 = pd.read_csv(
            save_folder + "barrido_osciloscopio_m3_2.csv",
            index_col=["Frecuencias", "Tiempo"],
        )
        df = pd.concat([df1, df2])

        # df3 = pd.read_csv(
        #     save_folder + "data_RLC_3.csv", index_col=["Frecuencias", "Tiempo"]
        # )
        # df4 = pd.read_csv(
        #     save_folder + "data_RLC_4.csv", index_col=["Frecuencias", "Tiempo"]
        # )[: -4 * 2500]
        # df5 = pd.read_csv(
        #     save_folder + "data_RLC_5.csv", index_col=["Frecuencias", "Tiempo"]
        # )
    else:
        raise NameError(f"Filtro {filtro} no encontrado. Filtros disponibles: RLC")
    df = df.sort_index(level="Frecuencias")
    return df


# %% PROCESAR DATA
def procesar_data(df, plot=True):
    frecs = df.index.get_level_values("Frecuencias").unique().values

    # defino arrays para guardar resultados
    f_med_1 = np.zeros_like(frecs)
    f_med_2 = np.zeros_like(frecs)
    A1 = np.zeros_like(frecs)
    A2 = np.zeros_like(frecs)
    phi_1 = np.zeros_like(frecs)
    phi_2 = np.zeros_like(frecs)
    R2_1 = np.zeros_like(frecs)
    R2_2 = np.zeros_like(frecs)

    # defino arrays para guardar incertezas
    Df_med_1 = np.zeros_like(frecs)
    Df_med_2 = np.zeros_like(frecs)
    DA1 = np.zeros_like(frecs)
    DA2 = np.zeros_like(frecs)
    Dphi_1 = np.zeros_like(frecs)
    Dphi_2 = np.zeros_like(frecs)

    for i, f in enumerate(frecs):
        print(f"procesando f = {f}")
        t = df.xs(f, level="Frecuencias").index.values
        V1 = df.xs(f, level="Frecuencias")["VoltajeCH1"].values
        V2 = df.xs(f, level="Frecuencias")["VoltajeCH2"].values
        # V1 -= np.mean(V1)
        # V2 -= np.mean(V2)
        A1_0 = (np.max(V1) - np.min(V1)) / 2
        A2_0 = (np.max(V2) - np.min(V2)) / 2
        phi1_0 = np.arcsin(V1[0] / A1_0) * 180 / np.pi
        phi1_0 = phi1_0 if V1[0] < V1[5] else 180 - phi1_0
        if np.abs(V2[0] / A2_0) > 1:
            phi2_0 = 90 if V2[0] > 0 else 270
        else:
            phi2_0 = np.arcsin(V2[0] / A2_0) * 180 / np.pi
            phi2_0 = phi2_0 if V2[0] < V2[5] else 180 - phi2_0
        try:
            popt1, pcov1 = curve_fit(seno, t, V1, p0=(A1_0, f, phi1_0))
            popt2, pcov2 = curve_fit(seno, t, V2, p0=(A2_0, f, phi2_0))
        except RuntimeError:
            # plt.errorbar(t, V1, fmt=".", zorder=1)
            plt.errorbar(t, V2, fmt=".", zorder=2)
            plt.title(f"f = {f:.2e}")
            plt.show()
            raise RuntimeError(f"Ajuste falló para f = {f}")
        A1[i], f_med_1[i], phi_1[i] = popt1
        A2[i], f_med_2[i], phi_2[i] = popt2
        if A1[i] < 0:
            A1[i] = -A1[i]
            phi_1[i] += 180
        if A2[i] < 0:
            A2[i] = -A2[i]
            phi_2[i] += 180
        DA1[i], Df_med_1[i], Dphi_1[i] = np.sqrt(np.diag(pcov1))
        DA2[i], Df_med_2[i], Dphi_2[i] = np.sqrt(np.diag(pcov2))
        R2_1[i] = r2_score(V1, seno(t, *popt1))
        R2_2[i] = r2_score(V2, seno(t, *popt2))
        if plot:
            plt.errorbar(t, V1, fmt=".", zorder=1)
            plt.plot(t, seno(t, *popt1), zorder=3)
            plt.errorbar(t, V2, fmt=".", zorder=2)
            plt.plot(t, seno(t, *popt2), zorder=4)
            plt.title(f"f = {f:.2e}")
            plt.show()
    return (A1, DA1, A2, DA2, phi_1, Dphi_1, phi_2, Dphi_2, R2_1, R2_2, frecs)


# %% BARRIDO
barrido = "grueso"  # "grueso" o "fino" o "m3"
df = select_data(barrido)
A1, DA1, A2, DA2, phi_1, Dphi_1, phi_2, Dphi_2, R2_1, R2_2, frecs = procesar_data(
    df=df, plot=False
)
# %% AJUSTE MODELO SIMPLE
T = A2 / A1
print(np.max(A1))
DT = np.sqrt((DA1 * A2 / A1**2) ** 2 + (DA2 * A2 / A1) ** 2) * 20 / np.log(10)
# At = 20 * np.log10(T)
# DAt = np.sqrt((DA1 / A1) ** 2 + (DA2 / A2) ** 2) * 20 / np.log(10)
phi = phi_2 - phi_1
phi_d = phi % 360
Dphi_d = np.sqrt((Dphi_1**2 + Dphi_2**2))
phi_d[phi_d >= 180] -= 360
mas_cercano_m1 = np.argmin(np.abs(frecs - 50.96e3))
# %% Modelo simple
fig, axs = plt.subplots(2, 1, sharex=True, gridspec_kw={"hspace": 0.05})
ax1, ax2 = axs
ax1.set_xscale("log")
ax1.set_xlim(0.8 * 1e3, 2.5e7 * 1.2)


# Transferencia
ax1.set_yscale("log")
ax1.errorbar(frecs, T, fmt=".", yerr=DT, color=w["verde"], label="Datos")
ax1.vlines(
    50.096e3,
    np.min(T),
    np.max(T),
    linestyles="--",
    color=w["rojo"],
    label="$f_0 = 50.10$ kHz",
)
ax1.set_ylabel("Transferencia")
# ax1.legend(loc=3)

# Fase
ax2.set_xscale("log")
ax2.set_xlim(0.8 * 1e3, 2.5e7 * 1.2)
ax2.errorbar(frecs, phi_d, fmt=".", yerr=Dphi_d, color=w["verde"], label="Datos")
ax2.set_xlabel("Frecuencia [ kHz ]")
ax2.set_ylabel("Defasaje [ $^\\circ$ ]")
ax2.vlines(
    50.096e3,
    np.min(phi_d),
    np.max(phi_d),
    linestyles="--",
    color=w["rojo"],
    label="$f_0 = 50.10$ kHz",
)
ax2.legend(loc=3)
fig.tight_layout()
fig.savefig(image_folder + f"grafico_barrido_gurueso.pdf", bbox_inches="tight")
#
