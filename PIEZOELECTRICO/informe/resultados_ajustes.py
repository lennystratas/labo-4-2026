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
        "xtick.labelsize": fontsize - 1,
        "ytick.labelsize": fontsize - 1,
        "legend.fontsize": fontsize - 1,
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


R2 = 9.8e3  # Ohm
DR2 = 130  # Ohm


def transformar(m, Dm):
    R, C, L, C2 = m
    DR, DC, DL, DC2 = Dm
    f0 = 1 / np.sqrt(L * C) / (2 * np.pi)
    fr = np.sqrt(1 / L * (1 / C + 1 / C2)) / (2 * np.pi)
    fr_f0 = fr - f0
    A = R2 / (R2 + R)
    Df = (R + R2) / L / (2 * np.pi)
    C_eq = 1 / (1 / C + 1 / C2)
    # --- Error for f0 ---
    df0_dL = -f0 / (2 * L)
    df0_dC = -f0 / (2 * C)
    Df0 = np.sqrt((df0_dL * DL) ** 2 + (df0_dC * DC) ** 2)

    # --- Error for f0_fr ---
    dfr_dL = np.sqrt((1 / C + 1 / C2)) * (-1 / 2) * (L ** (-3 / 2)) / (2 * np.pi)
    dfr_dC = (
        np.sqrt(1 / L)
        / (2 * np.sqrt((1 / C + 1 / C2)))
        * (-1 / 2)
        * (C ** (-3 / 2))
        / (2 * np.pi)
    )
    dfr_dC2 = (
        np.sqrt(1 / L)
        / (2 * np.sqrt((1 / C + 1 / C2)))
        * (-1 / 2)
        * (C2 ** (-3 / 2))
        / (2 * np.pi)
    )

    dfr_f0_dL = dfr_dL - df0_dL
    dfr_f0_dC = dfr_dC - df0_dC
    dfr_f0_dC2 = dfr_dC2

    Dfr_f0 = np.sqrt(
        (dfr_f0_dL * DL) ** 2 + (dfr_f0_dC * DC) ** 2 + (dfr_f0_dC2 * DC2) ** 2
    )

    # --- Error for A ---
    dA_dR = -R2 / (R2 + R) ** 2
    dA_dR2 = R / (R2 + R) ** 2
    DA = np.sqrt((dA_dR * DR**2 + dA_dR2 * DR2**2))

    # --- Error for Df (Bandwidth) ---
    dDf_dR = 1 / (2 * np.pi * L)
    dDf_dL = -(R + R2) / (2 * np.pi * L**2)
    DDf = np.sqrt((dDf_dR * DR) ** 2 + (dDf_dL * DL) ** 2)

    # Return both the values and their respective propagated uncertainties
    return (f0, fr_f0, A, Df), (Df0, Dfr_f0, DA, DDf)


# %% DATOS
# R, L, C, C2
m1 = [
    np.float64(10125.98946540047),
    np.float64(581.0847245753963),
    np.float64(1.7369384494786573e-14),
    np.float64(2.3188889290836265e-12),
]
Dm1 = [
    np.float64(66.55971358761785),
    np.float64(0.697169082618691),
    np.float64(2.0843514236383848e-17),
    np.float64(2.725211860034147e-15),
]
m3 = [
    np.float64(12396.20282002559),
    np.float64(780.0870612580512),
    np.float64(1.4400942634739919e-15),
    np.float64(1.7023002939269935e-12),
]
Dm3 = [
    np.float64(324.5867355151398),
    np.float64(2.8226187128751334),
    np.float64(5.2110304052222626e-18),
    np.float64(5.923576569912511e-15),
]
m5 = [
    np.float64(27137.719533964384),
    np.float64(1166.2426762284429),
    np.float64(3.5232721934934955e-16),
    np.float64(1.2127747248621597e-12),
]
Dm5 = [
    np.float64(334.26393714281585),
    np.float64(2.8465138892832713),
    np.float64(8.599903727233739e-19),
    np.float64(2.4961501395149355e-15),
]
# %% GRAFICO 4x1: R, L, C, C2 vs f0
# Para cada modo computo f0 (resonancia) y su error a partir de los parametros ajustados
modos = [("m1", m1, Dm1), ("m3", m3, Dm3), ("m5", m5, Dm5)]

R_vals = np.array([m[0] for _, m, _ in modos])
L_vals = np.array([m[1] for _, m, _ in modos])
C_vals = np.array([m[2] for _, m, _ in modos])
C2_vals = np.array([m[3] for _, m, _ in modos])

R_errs = np.array([d[0] for _, _, d in modos])
L_errs = np.array([d[1] for _, _, d in modos])
C_errs = np.array([d[2] for _, _, d in modos])
C2_errs = np.array([d[3] for _, _, d in modos])

f0_list, Df0_list = [], []
for _, m, Dm in modos:
    (f0, _, _, _), (Df0, _, _, _) = transformar(m, Dm)
    f0_list.append(f0)
    Df0_list.append(Df0)
f0_arr = np.array(f0_list)
Df0_arr = np.array(Df0_list)

# Conversiones a unidades "lindas"
f0_kHz = f0_arr / 1e3
Df0_kHz = Df0_arr / 1e3
R_kOhm = R_vals / 1e3
R_kOhm_err = R_errs / 1e3
C_fF = C_vals * 1e15
C_fF_err = C_errs * 1e15
C2_pF = C2_vals * 1e12
C2_pF_err = C2_errs * 1e12

color_main = w["violeta"]
color_alt = w["amarillo"]

fig, axes = plt.subplots(
    2, 2, figsize=(8.5, 6.0), sharex=True,
    gridspec_kw={"hspace": 0.12, "wspace": 0.42},
)
ax_R, ax_L = axes[0]
ax_C, ax_C2 = axes[1]

paneles = [
    (ax_R,  R_kOhm, R_kOhm_err, color_main, r"$R$ [k$\Omega$]"),
    (ax_L,  L_vals, L_errs,     color_main, r"$L$ [H]"),
    (ax_C,  C_fF,   C_fF_err,   color_main, r"$C$ [fF]"),
    (ax_C2, C2_pF,  C2_pF_err,  color_alt,  r"$C_2$ [pF]"),
]

for ax, vals, errs, color, ylabel in paneles:
    ax.errorbar(
        f0_kHz, vals,
        xerr=Df0_kHz, yerr=errs,
        fmt="o",
        color=color,
        markersize=4,
        markeredgewidth=0.9,
        elinewidth=1.0,
        capsize=3,
        capthick=1.0,
        zorder=10,
    )
    ax.set_ylabel(ylabel)
    # Margen vertical y limite de cantidad de ticks
    v_lo = np.min(vals - errs)
    v_hi = np.max(vals + errs)
    margen = 0.18 * (v_hi - v_lo)
    ax.set_ylim(v_lo - margen, v_hi + margen)
    ax.yaxis.set_major_locator(ticker.MaxNLocator(nbins=4, prune="both"))

# C abarca casi dos ordenes de magnitud -> escala log para que se lean los tres puntos
ax_C.set_yscale("log")
ax_C.set_ylim(C_fF.min() / 3, C_fF.max() * 3)
ax_C.yaxis.set_major_locator(ticker.LogLocator(base=10, numticks=4))
ax_C.yaxis.set_minor_locator(
    ticker.LogLocator(base=10, subs=np.arange(2, 10) * 0.1, numticks=12)
)
ax_C.yaxis.set_minor_formatter(ticker.NullFormatter())

# Formatos compactos para los demas paneles
ax_R.yaxis.set_major_formatter(ticker.FormatStrFormatter("%.0f"))
ax_L.yaxis.set_major_formatter(ticker.FormatStrFormatter("%.0f"))
ax_C2.yaxis.set_major_formatter(ticker.FormatStrFormatter("%.1f"))

# Linea de referencia para C2 (valor nominal del capacitor externo)
C2_ref = 2.02
C2_ref_err = 0.04
ax_C2.axhspan(
    C2_ref - C2_ref_err, C2_ref + C2_ref_err,
    color=w["rojo"], alpha=0.15, zorder=1,
)
ax_C2.axhline(
    C2_ref, color=w["rojo"], linestyle="--", linewidth=1.2, zorder=2,
    label=rf"$C_2^{{pp}} = ({C2_ref:.2f} \pm {C2_ref_err:.2f})$ pF",
)
ax_C2.legend(loc="best", fontsize=11, framealpha=0.9)

# Ticks del eje x alineados a los valores medidos de f0 (en ambas columnas)
x_min, x_max = f0_kHz.min(), f0_kHz.max()
pad = 0.08 * (x_max - x_min)
for ax in (ax_C, ax_C2):
    ax.set_xticks(f0_kHz)
    ax.set_xticklabels([f"{f:.2f}" for f in f0_kHz])
    ax.xaxis.set_minor_locator(ticker.NullLocator())
    ax.set_xlim(x_min - pad, x_max + pad)
    ax.set_xlabel(r"$f_0$ [kHz]")

image_folder = get_base_path() + "informe/figuras/"
os.makedirs(image_folder, exist_ok=True)
fig.savefig(image_folder + "grafico_parametros_ajuste.pdf", bbox_inches="tight")
plt.show()
