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
    f0_fr = 1 / np.sqrt(L * C) / (2 * np.pi) - np.sqrt(1 / L * (1 / C + 1 / C2)) / (
        2 * np.pi
    )
    A = R2 / (R2 + R)
    Df = (R + R2) / L / (2 * np.pi)
    C_eq = 1 / (1 / C + 1 / C2)

    # --- Error for f0 ---
    df0_dL = -f0 / (2 * L)
    df0_dC = -f0 / (2 * C)
    Df0 = np.sqrt((df0_dL * DL) ** 2 + (df0_dC * DC) ** 2)

    # --- Error for f0_fr ---
    # Split into f0 term and the series combination term (f_series = 1 / (2 * pi * sqrt(L * C_eq)))
    f_series = 1 / (2 * np.pi * np.sqrt(L * C_eq))

    df0fr_dL = df0_dL - (-f_series / (2 * L))
    df0fr_dC = df0_dC - (-f_series / (2 * C**2 * (1 / C + 1 / C2)))
    df0fr_dC2 = -(-f_series / (2 * C2**2 * (1 / C + 1 / C2)))

    Df0_fr = np.sqrt(
        (df0fr_dL * DL) ** 2 + (df0fr_dC * DC) ** 2 + (df0fr_dC2 * DC2) ** 2
    )

    # --- Error for A ---
    dA_dR = -R2 / (R2 + R) ** 2
    DA = np.abs(dA_dR * DR)

    # --- Error for Df (Bandwidth) ---
    dDf_dR = 1 / (2 * np.pi * L)
    dDf_dL = -(R + R2) / (2 * np.pi * L**2)
    DDf = np.sqrt((dDf_dR * DR) ** 2 + (dDf_dL * DL) ** 2)

    # Return both the values and their respective propagated uncertainties
    return (f0, f0_fr, A, Df), (Df0, Df0_fr, DA, DDf)


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
