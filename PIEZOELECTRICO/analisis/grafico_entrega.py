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
    return f"{valor / 1000:.2f}"


def formato_exp(valor, posicion):
    if valor == 0:
        return "0"
    else:
        return f"{valor * 1000:.0f}e-3"


formatok = ticker.FuncFormatter(formato_kilo)
formato_1e = ticker.FuncFormatter(formato_exp)


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
image_folder = base_path + "figuras/"


# %% ARCHIVOS
def select_data(filtro):
    if filtro == "entrada":
        df = pd.read_csv(
            save_folder + "barrido_lockin_entrada.csv",
            index_col=["Frecuencia"],
        )
    elif filtro == "cas":
        df1 = pd.read_csv(
            save_folder + "barrido_lockin_cas_1.csv",
            index_col=["Frecuencia"],
        )
        df2 = pd.read_csv(
            save_folder + "barrido_lockin_cas_2.csv",
            index_col=["Frecuencia"],
        )
        df = pd.concat([df1, df2])
    else:
        raise NameError(
            f"Filtro {filtro} no encontrado. Filtros disponibles: entrada, cas"
        )
    df = df.sort_index(level="Frecuencias")
    return df


# %% BARRIDO
barrido = "fino"  # "grueso" o "fino"
df_entrada = select_data("entrada")
A1 = np.mean(df_entrada["Amplitud"].values)
DA1 = np.std(df_entrada["Amplitud"].values)
df_barrido = select_data("cas")
frecs = df_barrido.index.values
A2 = df_barrido["Amplitud"].values
DA2 = df_barrido["Escala"].values / 2**16

phi_2 = df_barrido["Fase"].values
Dphi_2 = np.sqrt(
    (1 / (1 + np.cos(A2) ** 2) * DA2) ** 2 + (1 / (1 + np.cos(A2) ** 2) * DA2) ** 2
)

# %% AJUSTE MODELO SIMPLE
T = A2 / A1
DT = np.sqrt((DA1 * A2 / A1**2) ** 2 + (DA2 * A2 / A1) ** 2) * 20 / np.log(10)
phi = phi_2 % 360
Dphi = Dphi_2
phi[phi >= 180] -= 360

limite_inf = 50.05e3
limite_sup = 50.15e3
rango = (frecs <= limite_sup) & (frecs >= limite_inf)
popt1, pcov1 = curve_fit(
    transferencia_RLC, frecs[rango], T[rango], p0=(50.1e3, 200, 0.5)
)
popt2, pcov2 = curve_fit(fase_RLC, frecs[rango], phi[rango], p0=(50.1e3, 200, 10))
# %% AJUSTE MODELO COMPLEJO
f0, Df, A = np.abs(
    popt1
)  # Si A y Df son ambos negativos da lo mismo para el ajuste, tomamos positivos
R2 = 9.8e3  # Ohm
Rs = R2 * (1 - A) / A
Ls = (Rs + R2) / (Df * 2 * np.pi)
Cs = 1 / (4 * np.pi**2 * Ls * f0**2)
print(Rs, Ls, Cs)
T_aj = lambda f, C2: transferencia_C2(f, Rs, Ls, Cs, C2, R2)
phi_aj = lambda f, C2, phi_0: fase_C2(f, Rs, Ls, Cs, C2, R2, phi_0)
p0 = (2.3e-12,)
p0_phi = (2.3e-12, popt2[2])
popt3, pcov3 = curve_fit(T_aj, frecs, T, p0=p0, sigma=DT)
popt4, pcov4 = curve_fit(phi_aj, frecs, phi, p0=p0_phi)

# %% GRAFICOS
fig, axs = plt.subplots(2, 1, sharex=True, gridspec_kw={"hspace": 0.05})
ax1, ax2 = axs

# Transferencia
ax1.set_yscale("log")
ax1.errorbar(frecs, T, fmt=".", yerr=DT, color=w["verde"], label="Datos", zorder=5)
ax1.plot(
    frecs,
    transferencia_RLC(frecs, *popt1),
    color=w["rojo"],
    label="Ajuste RLC",
    lw=1.5,
    zorder=9,
)
# ax1.plot(

#     frecs,
#     T_aj(frecs, *popt3),
#     color=w["amarillo"],
#     label="Ajuste con $C_2$",
#     lw=2,
#     zorder=10,
# )
ax1.set_ylabel("Transferencia")
ax1.vlines(
    [limite_inf, limite_sup],
    np.min(T),
    np.max(T),
    linestyles="dashed",
    label="Límite ajuste",
    colors=w["violeta"],
    alpha=0.65,
)
ax1.vlines(
    popt1[0],
    np.min(T),
    np.max(T),
    linestyles="dashed",
    label="$f_0$ ajuste",
    colors=w["amarillo"],
    alpha=1,
)

# ax1.legend(loc=1)

# Fase
ax2.errorbar(frecs, phi, fmt=".", yerr=Dphi, color=w["verde"], label="Datos", zorder=5)
ax2.plot(
    frecs,
    fase_RLC(frecs, *popt2),
    color=w["rojo"],
    lw=1.5,
    label="Ajuste RLC",
    zorder=9,
)
# ax2.plot(
#     frecs,
#     phi_aj(frecs, *popt4),
#     color=w["amarillo"],
#     lw=2,
#     label="Ajuste con $C_2$",
#     zorder=10,
# )
ax2.xaxis.set_major_formatter(formatok)
ax2.set_xlabel("Frecuencia [ kHz ]")
ax2.set_ylabel("Defasaje [ $^\\circ$ ]")
ax2.vlines(
    [limite_inf, limite_sup],
    np.min(phi),
    np.max(phi),
    linestyles="dashed",
    label="Límite ajuste",
    colors=w["violeta"],
    alpha=0.65,
)
ax2.vlines(
    popt2[0],
    np.min(phi),
    np.max(phi),
    linestyles="dashed",
    # label=f"$f_0 = ({popt2[0]/1000:.1f} \\pm {np.sqrt(np.diag(pcov2))[0]/1000:.f}$) Hz ",
    label=f"$f_0$ ajuste",
    colors=w["amarillo"],
    alpha=1,
)
# ax2.legend(loc=(0.33, 0.3))
ax2.legend(loc="best")
fig.tight_layout()
fig.savefig(image_folder + "grafico_entrega.pdf", bbox_inches="tight")

# %% RESIDUOS
fig, axs = plt.subplots(
    2,
    1,
    sharex=True,
    gridspec_kw={"hspace": 0.05},
    figsize=(6.4, 4.8 * 496 / 396 * 0.93),
)
ax1, ax2 = axs

# Transferencia
# ax1.set_yscale("log")
ax1.errorbar(
    frecs[rango],
    (T[rango] - transferencia_RLC(frecs[rango], *popt1)),
    fmt=".",
    yerr=DT[rango],
    color=w["verde"],
    label="Residuos",
    # label="Residuos sin $C_2$",
    zorder=10,
)
# ax1.errorbar(
#     frecs,
#     (T - T_aj(frecs, *popt3)),
#     fmt=".",
#     yerr=DT,
#     color=w["amarillo"],
#     label="Residuos con $C_2$",
# )
# ax1.set_ylabel("Transferencia")
ax1.legend(loc=1)
ax1.hlines(0, frecs[rango][0], frecs[rango][-1], lw=1.5, color=w["rojo"])
ax1.yaxis.set_major_formatter(formato_1e)

# Fase
ax2.errorbar(
    frecs[rango],
    phi[rango] - fase_RLC(frecs[rango], *popt2),
    fmt=".",
    yerr=Dphi[rango],
    color=w["verde"],
    label="Residuos sin $C_2$",
    zorder=10,
)
# ax2.errorbar(
#     frecs,
#     (phi - phi_aj(frecs, *popt4)),
#     fmt=".",
#     yerr=Dphi,
#     color=w["amarillo"],
#     label="Residuos con $C_2$",
# )
ax2.xaxis.set_major_formatter(formatok)
ax2.set_xlabel("Frecuencia [ kHz ]")
# ax2.set_ylabel("Defasaje [ $^\\circ$ ]")
ax2.hlines(0, frecs[rango][0], frecs[rango][-1], lw=1.5, color=w["rojo"])
# ax2.legend(loc=3)
fig.tight_layout()
fig.savefig(image_folder + "residuos_entrega.pdf", bbox_inches="tight")

# INSETS

# # --- Top inset (Transferencia) ---
# axins1 = inset_axes(ax1, width="35%", height="35%", loc="lower right")

# # same data as ax1
# axins1.errorbar(
#     frecs[rango],
#     (T[rango] - transferencia_RLC(frecs[rango], *popt1)),
#     fmt=".",
#     yerr=DT[rango],
#     color=w["verde"],
# )
# axins1.errorbar(frecs, (T - T_aj(frecs, *popt3)), fmt=".", yerr=DT, color=w["amarillo"])
# axins1.xaxis.set_major_formatter(formatok)

# # zoom region around 50250
# x1_top, x2_top = 50200, 50300
# axins1.set_xlim(x1_top, x2_top)


# # auto y-limits based on that window
# mask_top = (frecs >= x1_top) & (frecs <= x2_top)
# ydata_top = (T - T_aj(frecs, *popt3))[mask_top]
# axins1.set_ylim(ydata_top.min(), ydata_top.max())

# mark_inset(ax1, axins1, loc1=2, loc2=4, fc="none", ec="0.5")


# # --- Bottom inset (Fase) ---
# axins2 = inset_axes(
#     ax2,
#     width="20%",
#     height="20%",
#     loc="upper left",
#     bbox_to_anchor=(0.12, -0.05, 1, 1),
#     bbox_transform=ax2.transAxes,
# )  # box in normalized coords


# axins2.errorbar(
#     frecs[rango],
#     phi[rango] - fase_RLC(frecs[rango], *popt2),
#     fmt=".",
#     yerr=Dphi[rango],
#     color=w["verde"],
# )
# axins2.errorbar(
#     frecs, (phi - phi_aj(frecs, *popt4)), fmt=".", yerr=Dphi, color=w["amarillo"]
# )

# # zoom region around 50100
# x1_bot, x2_bot = 50050, 50150
# axins2.set_xlim(x1_bot, x2_bot)
# axins2.set_xticks([50050, 50150])

# axins2.set_yticks([-0.25, 0.25])

# axins2.xaxis.set_major_formatter(formatok)


# axins2.set_ylim(-2, 2)

# mark_inset(ax2, axins2, loc1=2, loc2=4, fc="none", ec="0.5", zorder = 20)

# %%
