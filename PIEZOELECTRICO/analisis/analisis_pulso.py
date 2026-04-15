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
save_folder = 'C:/Users/publico/Documents/l4-g6-2026-1C/piezo/datos/'
#%%
def select_data():
    df = pd.read_csv(
    save_folder + "respuesta_pulso_4.csv", index_col=["Tiempo"]
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

#V2 = V2[tmask]

fft_amp = np.abs(np.fft.fft(V2))
fft_frec = np.fft.fftfreq(len(V2), d=dt)

mask = fft_frec > 0
fft_frec = fft_frec[mask]
fft_amp = fft_amp[mask]

plt.figure()
plt.plot(fft_frec, fft_amp, ".--")
plt.vlines(50150, 0, 1, color="r")
plt.xscale("log")

reson = np.argmax(fft_amp)

print(fft_frec[reson])
#%%
plt.plot(t, V2)