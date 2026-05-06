# %% AJUSTES
from matplotlib import ticker
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.metrics import r2_score
from scipy.optimize import curve_fit
import os
#import wesanderson as ws


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


w = {"amarillo": "#F3AA0C", "verde": "#055E49", "violeta": '#35274A', "rojo": '#F2300F'}

def get_base_path():
    paths = [
        "C:/Users/publico/Documents/l4-g6-2026-1C/labo-4-2026/PIEZOELECTRICO/",  # compu labo
        "C:/Users/olive/Documents/labo-4-2026/PIEZOELECTRICO/",  # Oli
        "C:/Users/lenny/OneDrive/Documents/FISICA/LABO 4/labo-4-2026/PIEZOELECTRICO/" #Lenny        
    ]
    for path in paths:
        if os.path.isdir(path):
            return path
    else:
        raise OSError("None of the paths are valid")


# def p_value(x, y_obs, yerr, func, popt):
#     from scipy.stats import chi2

#     y_pred = func(x, *popt)
#     chi_cuadrado = np.sum(((y_obs - y_pred) / yerr) ** 2)
#     grados_libertad = len(x) - len(popt)
#     return chi2.sf(chi_cuadrado, grados_libertad)

def formato_kilo(valor, posicion):
    # Dividimos entre 1000 y le decimos que muestre 1 decimal (.1f)
    return f"{valor / 1000:.2f}"
formatok = ticker.FuncFormatter(formato_kilo)



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
    return np.angle(
        V2_div_V1(
            f,
            R,
            L,
            C,
            C2,
            R2,
        ),
        deg=True,
    ) + phi_0


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

R = 101
DR = 1
L = 10e-3
DL = 1e-3
C = 86.7e-9
DC = 0.7e-9

f0 = 1 / (np.sqrt(L * C) * 2 * np.pi)
Df = R / (L * 2 * np.pi)
Df0 = np.sqrt(
    (0.5 * L**-1.5 * C**-0.5 * DL) ** 2 + (0.5 * L**-0.5 * C**-1.5 * DC) ** 2
) / (2 * np.pi)
DDf = np.sqrt((DR / L) ** 2 + (R / L**2 * DL) ** 2) / (2 * np.pi)
print(f"f0 = {f0} +- {Df0} ")
print(f"Df = {Df} +- {DDf} ")

base_path = get_base_path()

save_folder = base_path + "datos/"
image_folder = base_path + "graficos/"


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
barrido = "m3" # "grueso" o "fino" o "m3"
df = select_data(barrido)
A1, DA1, A2, DA2, phi_1, Dphi_1, phi_2, Dphi_2, R2_1, R2_2, frecs = procesar_data(
    df=df, plot=False
)
# %% AJUSTE MODELO SIMPLE
T = A2 / A1
DT = np.sqrt((DA1 * A2 / A1**2) ** 2 + (DA2 * A2 / A1) ** 2) * 20 / np.log(10)
# At = 20 * np.log10(T)
# DAt = np.sqrt((DA1 / A1) ** 2 + (DA2 / A2) ** 2) * 20 / np.log(10)
phi = phi_2 - phi_1
phi_d = phi % 360
Dphi_d = np.sqrt((Dphi_1**2 + Dphi_2**2))
phi_d[phi_d >= 180] -= 360

rango = frecs <= 50.2e3
popt1, pcov1 = curve_fit(
    transferencia_RLC, frecs[rango], T[rango], p0=(50.1e3, 200, 0.5)
)
popt2, pcov2 = curve_fit(fase_RLC, frecs[rango], phi_d[rango], p0=(50.1e3, 200, 10))
# %% Modelo simple
fig, axs = plt.subplots(2, 1, sharex=True, gridspec_kw={"hspace": 0.05})
ax1, ax2 = axs
plt.title("ajuste modelo RLC")
if barrido == "grueso":
    ax1.set_xscale("log")
    ax1.set_xlim(0.8*1e3, 2.5e7*1.2)


# Transferencia
ax1.set_yscale("log")
ax1.errorbar(frecs, T, fmt=".", yerr=DT, color=w["rojo"], label="Datos")
if barrido !="grueso":
    ax1.plot(frecs, transferencia_RLC(frecs, *popt1), color=w["verde"], label="Ajuste", lw=2)
ax1.set_ylabel("Transferencia")
ax1.legend(loc=3)

# Fase
if barrido == "grueso":
    ax2.set_xscale("log")
    ax2.set_xlim(0.8*1e3, 2.5e7*1.2)
ax2.errorbar(frecs, phi_d, fmt=".", yerr=Dphi_d, color=w["rojo"], label="Datos")
if barrido == "fino":
    ax2.plot(frecs, fase_RLC(frecs, *popt2), color=w["verde"], lw=2, label="Ajuste")
ax2.xaxis.set_major_formatter(formatok)
ax2.set_xlabel("Frecuencia [ kHz ]")
ax2.set_ylabel("Defasaje [ $^\\circ$ ]")
ax2.legend(loc=3)
fig.tight_layout()

# Residuos
fig, axs = plt.subplots(2, 1, sharex=True, gridspec_kw={"hspace": 0.05})
ax1, ax2 = axs
if barrido == "grueso":
    ax1.set_xscale("log")

# Transferencia
# ax1.set_yscale("log")
ax1.errorbar(frecs[rango], T[rango]-transferencia_RLC(frecs[rango], *popt1), fmt=".", yerr=DT, color=w["rojo"], label="Datos")
ax1.set_ylabel("Transferencia")
ax1.legend(loc=3)

# Fase
if barrido == "grueso":
    ax2.set_xscale("log")
ax2.errorbar(frecs[rango], phi_d[rango]-fase_RLC(frecs[rango], *popt2), fmt=".", yerr=Dphi_d, color=w["rojo"], label="Datos")
ax2.xaxis.set_major_formatter(formatok)
ax2.set_xlabel("Frecuencia [ kHz ]")
ax2.set_ylabel("Defasaje [ $^\\circ$ ]")
ax2.legend(loc=3)
fig.tight_layout()

# %% Modelo complejo
f0, Df, A = np.abs(
    popt1
)  # Si A y Df son ambos negativos da lo mismo para el ajuste, tomamos positivos
R2 = 9.8e3  # Ohm
Rs = R2 * (1 - A) / A
Ls = (Rs+R2) / (Df * 2* np.pi)  # o debería ser sobre 2 pi? Esto funciona
Cs = 1 / (4 * np.pi**2 * Ls * f0**2)
print(Rs, Ls, Cs)
# T_aj = lambda f, R, L, C, C2: transferencia_C2(f, R, L, C, C2, R2)
# phi_aj  = lambda f, R, L, C, C2: fase_C2(f, R, L, C, C2, R2)
# p0 = (Rs, Ls, Cs, 1e-11)
# p0_phi = (Rs, Ls, Cs, 1e-11, popt2[2])
T_aj = lambda f, C2: transferencia_C2(f, Rs, Ls, Cs, C2, R2)
phi_aj = lambda f, C2, phi_0: fase_C2(f, Rs, Ls, Cs, C2, R2, phi_0)
p0 = (1e-11,)
p0_phi =(1e-11, popt2[2])
popt3, pcov3 = curve_fit(T_aj, frecs, T, p0=p0, sigma=DT)
popt4, pcov4 = curve_fit(phi_aj, frecs, phi_d, p0=p0_phi, sigma=Dphi_d)
# %% Graficos modelo complejo
fig, axs = plt.subplots(2, 1, sharex=True, gridspec_kw={"hspace": 0.05})
ax1, ax2 = axs
if barrido == "grueso":
    ax1.set_xscale("log")

# Transferencia
ax1.set_yscale("log")
ax1.errorbar(frecs, T, fmt=".", yerr=DT, color=w["rojo"], label="Datos")
ax1.plot(frecs, T_aj(frecs, *popt3), color =w["verde"], label="Ajuste", lw=2, zorder = 10)
ax1.set_ylabel("Transferencia")
ax1.legend(loc=3)

# Fase
if barrido == "grueso":
    ax2.set_xscale("log")
ax2.errorbar(frecs, phi_d, fmt=".", yerr=Dphi_d, color=w["rojo"], label="Datos")
ax2.plot(frecs, phi_aj(frecs, *popt4), color=w["verde"], lw=2, label="Ajuste", zorder=10)
ax2.xaxis.set_major_formatter(formatok)
ax2.set_xlabel("Frecuencia [ kHz ]")
ax2.set_ylabel("Defasaje [ $^\\circ$ ]")
ax2.legend(loc=3)
fig.tight_layout()

# Residuos
fig, axs = plt.subplots(2, 1, sharex=True, gridspec_kw={"hspace": 0.05})
ax1, ax2 = axs
if barrido == "grueso":
    ax1.set_xscale("log")

# Transferencia
# ax1.set_yscale("log")
ax1.errorbar(frecs, T-T_aj(frecs, *popt3)/DT, fmt=".", yerr=DT, color=w["rojo"], label="Datos")
ax1.set_ylabel("Transferencia")
ax1.legend(loc=3)

# Fase
if barrido == "grueso":
    ax2.set_xscale("log")
ax2.errorbar(frecs, phi_d-phi_aj(frecs, *popt4)/Dphi_d, fmt=".", yerr=Dphi_d, color=w["rojo"], label="Datos")
ax2.xaxis.set_major_formatter(formatok)
ax2.set_xlabel("Frecuencia [ kHz ]")
ax2.set_ylabel("Defasaje")
ax2.legend(loc=3)
fig.tight_layout()

#%% Modelo complejo logaritmico
T_aj = lambda f, R, L, C, C2: transferencia_C2(f, R, L, C, C2, R2)
T_aj_log = lambda f, R, L, C, C2: np.log10(transferencia_C2(f, R, L, C, C2, R2))
phi_aj  = lambda f, R, L, C, C2, phi_0: fase_C2(f, R, L, C, C2, R2, phi_0)
p0 = (Rs, Ls, Cs, 1e-11)
p0_phi = (Rs, Ls, Cs, 1e-11, popt2[2])
popt5, pcov5 = curve_fit(T_aj_log, frecs, np.log10(T), p0=p0, sigma=np.log(DT))
# popt6, pcov6 = curve_fit(phi_aj, frecs, phi_d, p0=p0_phi, sigma=Dphi_d)
# %% Graficos modelo complejo logaritmico
fig, axs = plt.subplots(2, 1, sharex=True, gridspec_kw={"hspace": 0.05})
ax1, ax2 = axs
if barrido == "grueso":
    ax1.set_xscale("log")

# Transferencia
ax1.set_yscale("log")
ax1.errorbar(frecs, T, fmt=".", yerr=DT, color=w["rojo"], label="Datos")
ax1.plot(frecs, T_aj(frecs, *popt5), color =w["verde"], label="Ajuste", lw=2, zorder=5)
ax1.set_ylabel("Transferencia")
ax1.legend(loc=3)

# Fase
# if barrido == "grueso":
#     ax2.set_xscale("log")
# ax2.errorbar(frecs, phi_d, fmt=".", yerr=Dphi_d, color=w["rojo"], label="Datos")
# ax2.plot(frecs, phi_aj(frecs, *popt6), color=w["verde"], lw=2, label="Ajuste")
# ax2.xaxis.set_major_formatter(formatok)
# ax2.set_xlabel("Frecuencia [ kHz ]")
# ax2.set_ylabel("Defasaje [ $^\\circ$ ]")
# ax2.legend(loc=3)
fig.tight_layout()

# Residuos
fig, axs = plt.subplots(2, 1, sharex=True, gridspec_kw={"hspace": 0.05})
ax1, ax2 = axs
if barrido == "grueso":
    ax1.set_xscale("log")

# Transferencia
# ax1.set_yscale("log")
ax1.errorbar(frecs, (T-T_aj(frecs, *popt5))/DT, fmt=".", yerr=DT, color=w["rojo"], label="Datos")
ax1.set_ylabel("Transferencia")
ax1.legend(loc=3)

# Fase
# if barrido == "grueso":
#     ax2.set_xscale("log")
# ax2.errorbar(frecs, phi_d-phi_aj(frecs, *popt6), fmt=".", yerr=Dphi_d, color=w["rojo"], label="Datos")
# ax2.xaxis.set_major_formatter(formatok)
# ax2.set_xlabel("Frecuencia [ kHz ]")
# ax2.set_ylabel("Defasaje [ $^\\circ$ ]")
# ax2.legend(loc=3)
# fig.tight_layout()
