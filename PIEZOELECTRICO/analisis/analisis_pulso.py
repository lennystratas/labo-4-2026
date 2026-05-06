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
save_folder = "C:/Users/publico/Documents/l4-g6-2026-1C/labo-4-2026/PIEZOELECTRICO/datos/"
#%%
def select_data():
    df = pd.read_csv(
    save_folder + "respuesta_pulso_8.csv", index_col=["Tiempo"]
    )
    return df
#%%
df = select_data()
t = df.index.values

#☺tmask = (t > -0.1) & (t < 2) 
#t = t[tmask]


dt = np.mean(np.diff(t))
V1 = df["VoltajeCH1"]
V2 = df["VoltajeCH2"]
V2_ext = np.concatenate((np.zeros(1250), V2.values, np.zeros(1250)))
# V2_ext = V2
#V2 = V2[tmask]

fft_amp_ext = np.abs(np.fft.fft(V2_ext))
fft_frec_ext = np.fft.fftfreq(len(V2_ext), d=dt)

mask = fft_frec_ext > 0
fft_frec_ext = fft_frec_ext[mask]
fft_amp_ext = fft_amp_ext[mask]

plt.figure()
plt.plot(fft_frec_ext, fft_amp_ext, ".--")
plt.vlines(50150, 0, 1, color="r")
# plt.xscale("log")
# plt.xlim(80e3, 170e3)
plt.xlim(240e3, 270e3)
# plt.xlim(280e3, 380e3)

plt.ylim(0, 1)
fft_amp = np.abs(np.fft.fft(V2))
fft_frec = np.fft.fftfreq(len(V2), d=dt)

mask = fft_frec > 0
fft_frec = fft_frec[mask]
fft_amp = fft_amp[mask]

plt.plot(fft_frec, fft_amp, ".--")
plt.vlines(50150, 0, 1, color="r")



reson = np.argmax(fft_amp)

seleccion = (fft_frec >= 240e3) & (fft_frec <= 250e3)
#%%
plt.plot(t, V2)
# plt.plot(t, V1)

# %%
