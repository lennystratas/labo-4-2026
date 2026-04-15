# %%
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.metrics import r2_score
from scipy.optimize import curve_fit

plt.style.use("seaborn-v0_8")

fontsize = 17
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


# def p_value(x, y_obs, yerr, func, popt):
#     from scipy.stats import chi2

#     y_pred = func(x, *popt)
#     chi_cuadrado = np.sum(((y_obs - y_pred) / yerr) ** 2)
#     grados_libertad = len(x) - len(popt)
#     return chi2.sf(chi_cuadrado, grados_libertad)


# %%


def seno(t, A, f, phi):
    return A * np.sin(2 * np.pi * f * t + phi * np.pi / 180)


def transferencia_RLC(f, f0, Df):
    w = 2 * np.pi * f
    w0, Dw = np.array([f0, Df]) * 2 * np.pi
    T = (w * Dw) / np.sqrt((w0**2 - w**2) ** 2 + (w * Dw) ** 2)
    return T
def atenuacion_RLC(f, f0, Df):
    w = 2 * np.pi * f
    w0, Dw = np.array([f0, Df]) * 2 * np.pi
    T = (w * Dw) / np.sqrt((w0**2 - w**2) ** 2 + (w * Dw) ** 2)
    return 20 * np.log10(T)


def fase_RLC(f, f0, Df):
    w = 2 * np.pi * f
    w0, Dw = np.array([f0, Df]) * 2 * np.pi
    phi_prov = 90 - np.arctan((w * Dw) / (w0**2 - w**2)) * 180 / np.pi
    return phi_prov


# %%

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

save_folder = (
    "C:/Users/publico/Documents/l4-g6-2026-1C/piezo/datos/"
)
image_folder = (
    "C:/Users/olive/OneDrive/Documentos/UBA/Física/Laboratorio 3/RLC serie/graficos/"
)

# %%


def select_data(filtro):
    if filtro == "grueso":
        df1 = pd.read_csv(
            save_folder + "barrido_osciloscopio_1.csv", index_col=["Frecuencias", "Tiempo"]
        )
        df2 = pd.read_csv(
            save_folder + "barrido_osciloscopio_2.csv", index_col=["Frecuencias", "Tiempo"]
        )
        df = pd.concat([df1, df2])

    if filtro == "fino":
        df1 = pd.read_csv(
            save_folder + "barrido_osciloscopio_fino_1.csv", index_col=["Frecuencias", "Tiempo"]
        )
        df2 = pd.read_csv(
            save_folder + "barrido_osciloscopio_fino_2.csv", index_col=["Frecuencias", "Tiempo"]
        )
        df3 = pd.read_csv(
            save_folder + "barrido_osciloscopio_fino_3v2.csv", index_col=["Frecuencias", "Tiempo"]
        )
        df = pd.concat([df1, df2, df3])

        # df3 = pd.read_csv(
        #     save_folder + "data_RLC_3.csv", index_col=["Frecuencias", "Tiempo"]
        # )
        # df4 = pd.read_csv(
        #     save_folder + "data_RLC_4.csv", index_col=["Frecuencias", "Tiempo"]
        # )[: -4 * 2500]
        # df5 = pd.read_csv(
        #     save_folder + "data_RLC_5.csv", index_col=["Frecuencias", "Tiempo"]
        # )

        df = df.sort_index(level="Frecuencias")
    else:
        raise NameError(f"Filtro {filtro} no encontrado. Filtros disponibles: RLC")
    return df


# %%


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
        V1 -= np.mean(V1)
        V2 -= np.mean(V2)
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


# %%
barrido = "fino"
df = select_data(barrido)
A1, DA1, A2, DA2, phi_1, Dphi_1, phi_2, Dphi_2, R2_1, R2_2, frecs = procesar_data(
    df=df, plot=False
)
# %%
T = A2 / A1
DT = np.sqrt((DA1 * A2 / A1**2) ** 2 + (DA2 * A2 / A1) ** 2) * 20 / np.log(10)
At = 20 * np.log10(T)
DAt = np.sqrt((DA1 / A1) ** 2 + (DA2 / A2) ** 2) * 20 / np.log(10)
phi = phi_2 - phi_1
phi_d = phi % 360
Dphi_d = np.sqrt((Dphi_1**2 + Dphi_2**2))
phi_d[phi_d >= 180] -= 360

# f0_med = frecs[np.argmin(np.abs(phi_d))]
# phi_f0 = np.min(np.abs(phi_d))
# print(f0_med)
# limite_sup = np.min(frecs[frecs <= 1e5][phi_d[frecs <= 1e5] < 0 - 5])
# limite_inf = np.max(frecs[frecs <= 1e5][phi_d[frecs <= 1e5] > 0 + 5])
# Df0_med = limite_sup - limite_inf
# print(Df0_med)

# for i, p in enumerate(phi_d):
#     if p >= -50 and frecs[i] >= 1e5:
#         phi_d[i] -= 360
popt1, pcov1 = curve_fit(transferencia_RLC, frecs, T, p0 = (50.1e3, 200))
popt2, pcov2 = curve_fit(fase_RLC, frecs, phi_d, p0 = (50.1e3, 200))
#%% Transferencia
fig, axs = plt.subplots(2,1, sharex=True, gridspec_kw={'hspace': 0.05})
ax1, ax2 = axs
if barrido == "grueso":
    ax1.set_xscale("log")
ax1.set_yscale("log")
ax1.errorbar(frecs, T, fmt=".", yerr=DT, label="Datos", color="darkblue")
ax1.plot(frecs, transferencia_RLC(frecs, *popt1))
# plt.xlim(100 * 0.8, 25 * 10**6 * 1.2)
# plt.ylim(0,0.03)
# ax1.set_xlabel("Frecuencia [ Hz ]")
ax1.set_ylabel("Transferencia")
ax1.legend(loc=3)
if barrido == "grueso":
    ax2.set_xscale("log")
# ax.set_yscale("log")
ax2.errorbar(frecs, phi_d, fmt=".", yerr=DT, label="Datos", color="darkblue")
ax1.plot(frecs, transferencia_RLC(frecs, *popt1))
# plt.xlim(100 * 0.8, 25 * 10**6 * 1.2)
# plt.ylim(0,0.03)
ax2.set_xlabel("Frecuencia [ Hz ]")
ax2.set_ylabel("Defasaje [ $^\\circ$ ]")
ax2.legend(loc=3)
fig.tight_layout()
# %% Atenuación
tamaño = (8.5, 4.5)
ax = [None, None]
fig1, ax[0] = plt.subplots(figsize=tamaño)

# fig, ax = plt.subplots(1, 2, figsize=(15, 5))

ax[0].set_xscale("log")
ax[0].errorbar(frecs, At, fmt=".", yerr=DAt, label="Datos", color="darkblue")
popt, pcov = curve_fit(
    atenuacion_RLC,
    frecs[frecs <= 1e5],
    At[frecs <= 1e5],
    # sigma=DAt[frecs <= 1e5],
    p0=(5400, 1500),
)
recorte = frecs <= 1e5
ax[0].plot(
    frecs,
    atenuacion_RLC(frecs, *popt),
    color="mediumseagreen",
    label="Ajuste $A(f)$",
)

ax[0].set_xlim(1e2 * 0.8, 25 * 10**6 * 1.2)
# ax[0].set_ylim(-85, 10)
ax[0].set_xlabel("Frecuencia [ Hz ]")
ax[0].set_ylabel("Atenuación [ dB ]")
ax[0].vlines(
    f0,
    -85,
    0,
    # label=f"$f_0^{'{\\, est}'} = ({f0 / 1000:.1f} \\pm {Df0 / 1000:.1f})$ kHz",
    label=f"$f_0^{'{\\, est}'}$",
    colors="goldenrod",
    linestyles="--",
)
# ax[0].vlines(
#     f0_med,
#     np.min(At),
#     np.max(At),
#     label=f"$f_0^{'{\\, est}'} = ({f0_med / 1000:.1f} \\pm {Df0_med / 1000:.1f})$ kHz",
#     colors="maroon",
#     linestyles="--",
# )

ax[0].legend(loc=(0.505, 0.635))
print(popt)
print(np.sqrt(np.diag(pcov)))
# print(
#     f"p-value = {p_value(frecs[recorte], At[recorte], DAt[recorte], atenuacion_RLC, popt)}"
# )
# plt.show()
# fig, ax = plt.subplots()
# ax.set_xscale("log")
# plt.errorbar(
#     frecs[recorte],
#     atenuacion_RLC(frecs[recorte], *popt) - At[recorte],
#     yerr=np.abs(At * 0.02)[recorte],
#     fmt=".",
# )ç
fig1.savefig(image_folder + "A_pasabandas.png", bbox_inches="tight")
fig2, ax[1] = plt.subplots(figsize=tamaño)
ax[1].set_xscale("log")
ax[1].errorbar(frecs, phi_d, yerr=Dphi_d, fmt=".", label="Datos", color="darkblue")
popt, pcov = curve_fit(
    fase_RLC,
    frecs[frecs <= 1e5],
    phi_d[frecs <= 1e5],
    sigma=Dphi_d[frecs <= 1e5],
    p0=(5400, 1400),
)
ax[1].plot(
    frecs, fase_RLC(frecs, *popt), color="mediumseagreen", label="Ajuste $\\phi(f)$"
)
ax[1].set_xlim(1e2 * 0.8, 25 * 10**6 * 1.2)
ax[1].set_xlabel("Frecuencia [ Hz ]")
ax[1].set_ylabel("Defasaje [ $^\\circ$ ]")

ax[1].vlines(
    f0,
    np.min(phi_d),
    np.max(phi_d),
    # label=f"$f_0^{'{\\, est}'} = ({f0 / 1000:.1f} \\pm {Df0 / 1000:.1f})$ kHz",
    label=f"$f_0^{'{\\, est}'}$",
    colors="goldenrod",
    linestyles="--",
)
# ax[1].vlines(
#     f0_med,
#     np.min(phi_d),
#     np.max(phi_d),
#     label=f"$f_0^{'{\\, est}'} = ({f0_med / 1000:.1f} \\pm {Df0_med / 1000:.1f})$ kHz",
#     colors="maroon",
#     linestyles="--",
# )

ax[1].legend(loc=(0.4, 0.5))
fig2.savefig(image_folder + "phi_pasabandas.png", bbox_inches="tight")
print(popt)
print(np.sqrt(np.diag(pcov)))
# print(popt)
# print(np.sqrt(np.diag(pcov)))
# print(
#     f"p-value = {p_value(frecs[recorte], phi_d[recorte], *phi_d[recorte], fase_RLC, popt)}"
# )
# fig, ax = plt.subplots()
# ax.set_xscale("log")
# plt.errorbar(
#     frecs[recorte],
#     fase_RLC(frecs[recorte], *popt) - phi_d[recorte],
#     yerr=Dphi_d[recorte],
#     fmt=".",
# )
