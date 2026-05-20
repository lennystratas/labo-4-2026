# %% AJUSTES
from matplotlib import ticker
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.metrics import r2_score
from scipy.optimize import curve_fit
import os
# import wesanderson as ws


plt.style.use("seaborn-v0_8")

fontsize = 14
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
        "xtick.labelsize": 13,
        "ytick.labelsize": 13,
        "legend.fontsize": 14,
    }
)


w = {"amarillo": "#F3AA0C", "verde": "#055E49", "violeta": "#35274A", "rojo": "#F2300F"}


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
    return f"{valor / 1000:.1f}"


formatok = ticker.FuncFormatter(formato_kilo)


def formato_exp(valor, posicion):
    # Dividimos entre 1000 y le decimos que muestre 1 decimal (.1f)
    return f"${valor * 100:.0f}.10^{{-2}}$"


formatok = ticker.FuncFormatter(formato_kilo)

formatexp = ticker.FuncFormatter(formato_kilo)

# %% DEFINO MODELOS


def saved_div(x, y, default):
    return np.divide(x, y, out=np.full_like(x, default, dtype=float), where=y != 0)


def seno(t, A, f, phi):
    return A * np.sin(2 * np.pi * f * t + phi * np.pi / 180)


def transferencia_RLC(f, f0, Df, A):
    w = 2 * np.pi * f
    w0, Dw = np.array([f0, Df]) * 2 * np.pi
    T = A * (w * Dw) / np.sqrt((w0**2 - w**2) ** 2 + (w * Dw) ** 2)
    return T


def fase_RLC(f, f0, Df, phi_0):
    w = 2 * np.pi * f
    w0, Dw = np.array([f0, Df]) * 2 * np.pi
    phi_prov = np.arctan(saved_div(w0**2 - w**2, w * Dw, default=0)) * 180 / np.pi
    return phi_prov + phi_0


def Z_C2(w, R, L, C, C2):
    a = w * L - 1 / (w * C)
    Y = R / (R**2 + a**2) + 1j * (w * C2 - a / (R**2 + a**2))
    return 1 / Y


def V2_div_V1(f, R, L, C, C2, R2):
    w = 2 * np.pi * f
    Z = Z_C2(w, R, L, C, C2)
    return R2 / (Z + R2)


def fase_C2(f, R, L, C, C2, R2, phi_0):
    return (
        np.angle(
            V2_div_V1(
                f,
                R,
                L,
                C,
                C2,
                R2,
            ),
            deg=True,
        )
        + phi_0
    )


def transferencia_C2(f, R, L, C, C2, R2):
    return np.abs(
        V2_div_V1(
            f,
            R,
            L,
            C,
            C2,
            R2,
        )
    )


# %% DEFINO PARAMETROS
base_path = get_base_path()

save_folder = base_path + "datos/"
image_folder = base_path + "poster/figuras/"


# %% ARCHIVOS
def select_data(filtro):
    if filtro == "m1":
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
            save_folder + "barrido_osciloscopio_m3_2_v2.csv",
            index_col=["Frecuencias", "Tiempo"],
        )
        df3 = pd.read_csv(
            save_folder + "barrido_osciloscopio_m3_3.csv",
            index_col=["Frecuencias", "Tiempo"],
        )
        df4 = pd.read_csv(
            save_folder + "barrido_osciloscopio_m3_4_v2.csv",
            index_col=["Frecuencias", "Tiempo"],
        )
        df = pd.concat([df1, df2, df3, df4])
    elif filtro == "m5":
        df1 = pd.read_csv(
            save_folder + "barrido_osciloscopio_m5_1.csv",
            index_col=["Frecuencias", "Tiempo"],
        )
        df2 = pd.read_csv(
            save_folder + "barrido_osciloscopio_m5_2_v2.csv",
            index_col=["Frecuencias", "Tiempo"],
        )
        df3 = pd.read_csv(
            save_folder + "barrido_osciloscopio_m5_3.csv",
            index_col=["Frecuencias", "Tiempo"],
        )
        df4 = pd.read_csv(
            save_folder + "barrido_osciloscopio_m5_4.csv",
            index_col=["Frecuencias", "Tiempo"],
        )
        df = pd.concat([df1, df2, df3, df4])
    elif filtro == "m2":
        df1 = pd.read_csv(
            save_folder + "barrido_osciloscopio_m2_1.csv",
            index_col=["Frecuencias", "Tiempo"],
        )
        df = pd.concat([df1])
    elif filtro == "m7":
        df1 = pd.read_csv(
            save_folder + "barrido_osciloscopio_m7_1.csv",
            index_col=["Frecuencias", "Tiempo"],
        )
        df2 = pd.read_csv(
            save_folder + "barrido_osciloscopio_m7_2.csv",
            index_col=["Frecuencias", "Tiempo"],
        )
        df = pd.concat([df1, df2])
    else:
        raise NameError(f"Filtro {filtro} no encontrado. Filtros disponibles: RLC")
    df = df.sort_index(level="Frecuencias")
    return df


# %% PROCESAR DATA
def procesar_data(df, plot=False, print_frecs=True):
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
        if print_frecs:
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
def generar_grafico(barrido, ax, guardar=False):
    df = select_data(barrido)
    A1, DA1, A2, DA2, phi_1, Dphi_1, phi_2, Dphi_2, R2_1, R2_2, frecs = procesar_data(
        df=df, plot=False, print_frecs=False
    )
    # AJUSTE MODELO SIMPLE
    T = A2 / A1
    # phi = (phi_2-phi_1) % 360
    # Dphi = Dphi_2
    # phi[phi >= 180] -= 360
    DT = np.sqrt((DA1 * A2 / A1**2) ** 2 + (DA2 * A2 / A1) ** 2) * 20 / np.log(10)
    rangos = {
        "m1": (50.05e3, 50.15e3),
        "m3": (150.145e3, 150.175e3),
        "m5": (248.27e3, 248.30e3),
        "m7": (349.1e3, 349.19e3),
    }
    lim_inf, lim_sup = rangos[barrido]
    rango = (frecs >= lim_inf) & (frecs <= lim_sup)
    popt1, pcov1 = curve_fit(
        transferencia_RLC,
        frecs[rango],
        T[rango],
        p0=((lim_sup + lim_inf) / 2, 200, 0.5),
    )
    popt1 = np.abs(popt1)
    # popt1_p, pcov1_p = curve_fit(fase_RLC, frecs[rango], phi[rango], p0=((lim_sup + lim_inf) / 2, 200, -25))
    # print(popt1_p)
    # AJUSTE MODELO COMPLEJO
    f0, Df, A = np.abs(
        popt1
    )  # Si A y Df son ambos negativos da lo mismo para el ajuste, tomamos positivos
    R2 = 9.8e3  # Ohm
    Rs = R2 * (1 - A) / A
    Ls = (Rs + R2) / (Df * 2 * np.pi)
    Cs = 1 / (4 * np.pi**2 * Ls * f0**2)
    T_aj = lambda f, C2: transferencia_C2(f, Rs, Ls, Cs, C2, R2)
    phi_aj = lambda f, C2, phi_0: fase_C2(f, Rs, Ls, Cs, C2, R2, phi_0)
    p0 = (2.3e-12,)
    print(barrido, popt1)
    popt2, pcov2 = curve_fit(T_aj, frecs, T, p0=p0, sigma=DT)
    # Ajuste modelo complejo logaritmico
    T_aj_c = lambda f, R, L, C, C2: transferencia_C2(f, R, L, C, C2, R2)
    T_aj_log = lambda f, R, L, C, C2: np.log10(transferencia_C2(f, R, L, C, C2, R2))
    p0 = (Rs, Ls, Cs, 2.3e-12)
    popt3, pcov3 = curve_fit(T_aj_log, frecs, np.log10(T), p0=p0)
    #  GRAFICOS

    # Transferencia
    ax.set_yscale("log")
    ax.errorbar(frecs, T, fmt=".", yerr=DT, color=w["verde"], label="Datos", zorder=5)
    # ax.plot(
    #     frecs,
    #     transferencia_RLC(frecs, *popt1),
    #     color=w["rojo"],
    #     label="Ajuste RLC",
    #     lw=1.5,
    #     zorder=9,
    # )
    if barrido != "m7":
        ax.plot(
            frecs,
            T_aj_c(frecs, *popt3),
            color=w["amarillo"],
            label="Ajuste con $C_2$",
            lw=2,
            zorder=10,
        )

    # ax.vlines(
    #     [lim_inf, lim_sup],
    #     np.min(T),
    #     np.max(T),
    #     linestyles="dashed",
    #     label="Límite ajuste",
    #     colors=w["violeta"],
    #     alpha=0.65,
    # )
    # ax.vlines(
    #     popt1[0],
    #     np.min(T),
    #     np.max(T),
    #     linestyles="dashed",
    #     label=f"$f_0 = {popt1[0] / 1000:.2f}$ kHz",
    #     colors=w["amarillo"],
    #     alpha=1,
    # )
    if barrido == "m3":
        ax.set_xlim(149.95e3, 150.35e3)
    ax.set_xlabel("Frecuencia [ kHz ]")
    ax.xaxis.set_major_formatter(formatok)
    legend_locs = {"m3": 3, "m5": 1, "m7": 1}
    if barrido == "m3":
        ax.set_ylabel("Transferencia")
        ax.legend(loc=legend_locs[barrido])
    if barrido == "m7":
        ax.set_yticks(np.logspace(-2, -1.2339332168313084, 3))
        ax.set_yticklabels(np.logspace(-2, -1.2339332168313084, 3))
        ax.yaxis.set_major_formatter(formato_exp)
    if guardar:
        fig.savefig(
            image_folder + f"grafico_barrido_{barrido}.svg", bbox_inches="tight"
        )


# %%
barridos = ["m3", "m5"]  # "m1" o "m3" o "m5" o "m7"
fig, axs = plt.subplots(
    1,
    2,
    sharey=True,
    figsize=(9, 3),
    gridspec_kw={"wspace": 0.05},
)
for barrido, ax in zip(barridos, axs):
    generar_grafico(barrido, guardar=False, ax=ax)
fig.savefig(image_folder + f"grafico_barrido_m3_m5.svg", bbox_inches="tight")
# %%
fig, ax7 = plt.subplots(
    figsize=(4, 3),
)
generar_grafico("m7", guardar=False, ax=ax7)


fig.savefig(image_folder + f"grafico_barrido_m7.svg", bbox_inches="tight")
# %% Modos 3 y 7
# %%
barridos = ["m3", "m7"]  # "m1" o "m3" o "m5" o "m7"
fig, axs = plt.subplots(
    1,
    2,
    figsize=(9.4, 3),
    gridspec_kw={"wspace": 0.25},
)
for barrido, ax in zip(barridos, axs):
    generar_grafico(barrido, guardar=False, ax=ax)
fig.savefig(image_folder + f"grafico_barrido_m3_m7.svg", bbox_inches="tight")
