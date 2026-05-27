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
transformar(m3, Dm3)
# El valor para la antiresonancia no es razonable? Pero la formula parece estar bien?

# %% GRAFICO 2x2: R, L, C, C2 vs f0
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

f0_list = []
Df0_list = []
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
C_fF = C_vals * 1e15  # capacitancia en femtofarads
C_fF_err = C_errs * 1e15
C2_pF = C2_vals * 1e12
C2_pF_err = C2_errs * 1e12

panel_color = {
    "R": w["violeta"],
    "L": w["violeta"],
    "C": w["violeta"],
    "C2": w["amarillo"],
}

fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.0), sharex=True, constrained_layout=True)
ax_R, ax_L, ax_C, ax_C2 = axes[0, 0], axes[0, 1], axes[1, 0], axes[1, 1]

paneles = [
    (ax_R, R_kOhm, R_kOhm_err, panel_color["R"], r"$R$ [k$\Omega$]"),
    (ax_L, L_vals, L_errs, panel_color["L"], r"$L$ [H]"),
    (ax_C, C_fF, C_fF_err, panel_color["C"], r"$C$ [fF]"),
    (ax_C2, C2_pF, C2_pF_err, panel_color["C2"], r"$C_2$ [pF]"),
]

for ax, vals, errs, color, ylabel in paneles:
    ax.errorbar(
        f0_kHz,
        vals,
        xerr=Df0_kHz,
        yerr=errs,
        fmt="o",
        color=color,
        markersize=11,
        capsize=4,
    )
    ax.set_ylabel(ylabel)

for ax in (ax_C, ax_C2):
    ax.set_xlabel(r"$f_0$ [kHz]")

image_folder = get_base_path() + "poster/figuras/"
fig.savefig(image_folder + "grafico_parametros_ajuste.svg", bbox_inches="tight")
plt.show()
# %% Diferencia con multiplos impares
print(f0_arr, Df0_arr)
mult_f0 = np.array([m * f0_arr[0] for m in [1, 3, 5]])
print(mult_f0)
print(np.abs(f0_arr - mult_f0) / (f0_arr + mult_f0) * 2 * 100)
# %% Valor k

h = 2e-3
v_inf = 3800
v_sup = 4100
eta_0 = f0_arr * 2 * np.pi / v_sup
k = np.sqrt(h * eta_0 / np.tan(h * eta_0))
print(k)
# %% Valor k con v vaiable
from scipy.optimize import minimize

h = 2e-3


def varianza(v):
    eta_0 = f0_arr * 2 * np.pi / v
    k = np.sqrt(h * eta_0 / np.tan(h * eta_0))
    return np.var(k) / np.mean(k) ** 2


vs = np.linspace(1000, 10000, 1000)
plt.plot(vs, [varianza(v) for v in vs], ".")
plt.yscale("log")
# from scipy.optimize import brentq


# def solve_eta(k, h, num_roots=5):
#     """
#     Finds the first 'num_roots' positive numerical solutions for eta
#     in the equation tan(eta * h) = (eta * h) / k^2.

#     Optimized for k << 1 by transforming the equation to avoid tan(x) singularities.
#     """
#     roots_eta = []

#     for n in range(1, num_roots + 1):
#         # The n-th root lies in the interval ((n-1)*pi, (n-0.5)*pi) for x = eta * h
#         lower_bound = (n - 1) * np.pi
#         upper_bound = (n - 0.5) * np.pi

#         # Avoid division by zero at x = 0 for the first root
#         if n == 1:
#             lower_bound = 1e-15

#         # Transformed objective function: cos(x) - (k^2 / x) * sin(x) = 0
#         f = lambda x: np.cos(x) - (k**2 / x) * np.sin(x)

#         # Brent's method is guaranteed to converge if signs at bounds differ
#         x_root = brentq(f, lower_bound, upper_bound)

#         # Convert x back to eta (eta = x / h)
#         roots_eta.append(x_root / h)

#     return np.array(roots_eta)


# def k_correspondiente(h, f0_med, fn_med, n_root):
#     m = n_root + 1
#     num_roots = n_root
#     h = 2e-3
#     for k in np.logspace(-5, 0, 5):
#         roots = solve_eta(k, h=h, num_roots=num_roots)
#         # ideal_roots = np.array([np.pi/(2*h) *(2*m+1)  form in range(num_roots)])
#         ideal_roots = np.array([roots[0] * (2 * m + 1) for m in range(num_roots)])
