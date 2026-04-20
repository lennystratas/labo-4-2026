# %%
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.metrics import r2_score
from scipy.optimize import curve_fit
import os

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
def get_base_path():
    paths = [
        "C:/Users/publico/Documents/l4-g6-2026-1C/piezo/", # compu labo
        "C:/Users/olive/Documents/labo-4-2026/PIEZOELECTRICO/", # Oli
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


# %%

def saved_div(x, y, default):
    return np.divide(x, y, out=np.full_like(x, default, dtype=float), where=y!=0)


def seno(t, A, f, phi):
    return A * np.sin(2 * np.pi * f * t + phi * np.pi / 180)


def transferencia_RLC(f, f0, Df, A):
    w = 2 * np.pi * f
    w0, Dw = np.array([f0, Df]) * 2 * np.pi
    T = A * (w * Dw) / np.sqrt((w0**2 - w**2) ** 2 + (w * Dw) ** 2)
    return T

def Z_C2(w, R, L, C, C2):
    a = w*L-1/(w*C)
    Y = R / (R**2+a**2) + 1j * (w*C2 - a/(R**2+ a**2))
    return 1/Y

def Z_tot(Z, Rf, R1, R2):
    return Rf + 1/(1/R1+1/(Z+R2))

def V2_div_V1(f, R, L, C, Rf, R1, R2, C2):
    w = 2*np.pi*f
    Z = Z_C2(w, R, L, C, C2)
    Zt = Z_tot(Z, Rf, R1, R2)
    return 1- Z*R1/((Zt-Rf)*(R1+R2+Z))


def fase_C2(f, R, L, C, C2, Rf, R1, R2):
    return np.angle(V2_div_V1(f, R, L, C, Rf, R1, R2, C2), deg = True)

def transferencia_C2(f, R, L, C, C2, Rf, R1, R2):
    # v1 =  np.abs(V2_div_V1(f, R, L, C, Rf, R1, R2, C2))
    # v2 = np.abs(analizar_circuito_pzt(f, R, L, C, C2, R1, R2, Rf))    
    # print(np.all(np.abs((v1-v2)/(v1+v2) * 2) < 1e-10))
    # return np.abs(V2_div_V1(f, R, L, C, C2, R1, R2, Rf))
    return np.abs(V2_div_V1(f, R, L, C, C2, R1, R2, Rf))


def fase_RLC(f, f0, Df):
    w = 2 * np.pi * f
    w0, Dw = np.array([f0, Df]) * 2 * np.pi
    phi_prov = np.arctan(saved_div(w0**2 - w**2, w * Dw, default=0)) * 180 / np.pi
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

base_path = get_base_path()

save_folder = base_path + "datos/"
image_folder = base_path + "graficos/"

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


# %%
barrido = "fino"
df = select_data(barrido)
A1, DA1, A2, DA2, phi_1, Dphi_1, phi_2, Dphi_2, R2_1, R2_2, frecs = procesar_data(
    df=df, plot=False
)
# %%
T = A2 / A1
DT = np.sqrt((DA1 * A2 / A1**2) ** 2 + (DA2 * A2 / A1) ** 2) * 20 / np.log(10)
# At = 20 * np.log10(T)
# DAt = np.sqrt((DA1 / A1) ** 2 + (DA2 / A2) ** 2) * 20 / np.log(10)
phi = phi_2 - phi_1
phi_d = phi % 360
Dphi_d = np.sqrt((Dphi_1**2 + Dphi_2**2))
phi_d[phi_d >= 180] -= 360

rango = frecs <= 50.2e3 
popt1, pcov1 = curve_fit(transferencia_RLC, frecs[rango], T[rango], p0 = (50.1e3, 200, 0.5))
popt2, pcov2 = curve_fit(fase_RLC, frecs[rango], phi_d[rango], p0 = (50.1e3, 200))
#%% Modelo simple
fig, axs = plt.subplots(2,1, sharex=True, gridspec_kw={'hspace': 0.05})
ax1, ax2 = axs
if barrido == "grueso":
    ax1.set_xscale("log")

# Transferencia
ax1.set_yscale("log")
ax1.errorbar(frecs, T, fmt=".", yerr=DT, label="Datos", color="darkblue")
ax1.plot(frecs, transferencia_RLC(frecs, *popt1))
ax1.set_ylabel("Transferencia")
ax1.legend(loc=3)

# Fase
if barrido == "grueso":
    ax2.set_xscale("log")
ax2.errorbar(frecs, phi_d, fmt=".", yerr=Dphi_d label="Datos", color="darkblue")
ax2.plot(frecs, fase_RLC(frecs, *popt2))
ax2.set_xlabel("Frecuencia [ Hz ]")
ax2.set_ylabel("Defasaje [ $^\\circ$ ]")
ax2.legend(loc=3)
fig.tight_layout()
#%% Modelo complejo
f0, Df, A = np.abs(popt1) # Si A y Df son ambos negativos da lo mismo para el ajuste, tomamos positivos
Rf = 50 # Ohm
R1 = 9.8e3 #Ohm
R2 = 9.8e3 #Ohm
Rs = R2*(1-A)/A
Ls = Rs/(Df*2*np.pi)
Cs = 1/(4*np.pi**2 * L* f0**2)
print(Rs, Ls, Cs)
# T_aj = lambda f, R, L, C, C2: transferencia_C2(f, R, L, C, C2, Rf, R1, R2)
# phi_aj  = lambda f, R, L, C, C2: fase_C2(f, R, L, C, C2, Rf, R1, R2)
# p0 = (Rs, Ls, Cs, 1e-9)
T_aj = lambda f, C2: transferencia_C2(f, Rs, Ls, Cs, C2, Rf, R1, R2)
phi_aj  = lambda f, C2: fase_C2(f, Rs, Ls, Cs, C2, Rf, R1, R2)
p0 = (1,)
popt3, pcov3 = curve_fit(T_aj, frecs, T, p0 = p0, sigma = DT)
popt4, pcov4 = curve_fit(phi_aj, frecs, phi_d, p0 = p0, sigma = DT)
#%% Graficos modelo complejo
fig, axs = plt.subplots(2,1, sharex=True, gridspec_kw={'hspace': 0.05})
ax1, ax2 = axs
if barrido == "grueso":
    ax1.set_xscale("log")

# Transferencia
ax1.set_yscale("log")
ax1.errorbar(frecs, T, fmt=".", yerr=DT, label="Datos", color="darkblue")
ax1.plot(frecs, T_aj(frecs, *p0))
ax1.set_ylabel("Transferencia")
ax1.legend(loc=3)

# Fase
if barrido == "grueso":
    ax2.set_xscale("log")
ax2.errorbar(frecs, phi_d, fmt=".", yerr=Dphi_d, label="Datos", color="darkblue")
ax2.plot(frecs, phi_aj(frecs, *popt4))
ax2.set_xlabel("Frecuencia [ Hz ]")
ax2.set_ylabel("Defasaje [ $^\\circ$ ]")
ax2.legend(loc=3)
fig.tight_layout()
#%%
# Version de gemini, da lo mismo que el mio (np.all(np.abs((v1-v2)/(v1+v2) * 2) < 1e-10) == True
# Para R, L y C sacados del ajuste, R1, R2 y Rf conocidos y C = 1e-9) pero el ajuste o graficar
# con p0 da cualquier cosa. Incluso el límite R1 = inf, C2 = 0, Rf = 0  que debería recuperar
# lo anterior no funciona con nignuno de los dos. 
def analizar_circuito_pzt(f, R, L, C, C2, R1, R2, Rf):
    """
    Calcula la transferencia considerando la resistencia de la fuente y la carga.
    """
    w = 2 * np.pi * f
    # Impedancias básicas
    # Usamos 1e-20 para evitar divisiones por cero en f=0
    z_c = 1 / (1j * w * C)
    z_c2 = 1 / (1j * w * C2)
    z_l = 1j * w * L
    
    # 1. Rama PZT
    z_pzt = R + z_l + z_c
    
    # 2. Impedancia del puente (PZT || C2)
    z_bridge = (z_pzt * z_c2) / (z_pzt + z_c2)
    
    # 3. Impedancia a la derecha de V1 (Puente + R2)
    z_right = z_bridge + R2
    
    # 4. Impedancia total vista desde el nodo V1 (R1 || z_right)
    z_in_node = (R1 * z_right) / (R1 + z_right)
    
    # --- RESULTADOS ---
    
    # Relación V1 respecto a la fuente ideal V (debido a Rf y carga)
    v1_v = z_in_node / (Rf + z_in_node)
    
    # Relación V2 / V1 (la que pediste)
    v2_v1 = R2 / (z_bridge + R2)
    
    # Relación total V2 / V
    v2_v = v2_v1 * v1_v
    
    return v2_v1