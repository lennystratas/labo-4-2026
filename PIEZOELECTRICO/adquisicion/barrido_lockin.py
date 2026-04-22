# -*- coding: utf-8 -*-
"""
Created on Wed Apr 22 16:16:56 2026

@author: Publico
"""
#%% Setup
from instrumental import SR830, AFG3021B

import pyvisa as visa
import numpy as np
import pandas as pd
import time
import maptplotlib.pyplot as plt
rm = visa.ResourceManager()
rm.list_resources()

li = SR830("GPIB0::8::INSTR")
gen = AFG3021B("USB0::0x0699::0x0346::C036493::INSTR")


#%% Barrido

frecuencias = np.linspace(50e3, 50.4e3, 100)
# frecuencias = np.linspace(50.275e3, 50.295e3, 300)
amplitudes = []
fases = []
escalas = []

for f in frecuencias:
    print(f"Adquiriendo  f = {f}")
    gen.setFrequency(f)    
    time.sleep(0.25) 
    R, tita, escala = li.auto_scale()
    amplitudes.append(R)
    fases.append(tita)
    escalas.append(escala)
    
df = pd.DataFrame({
    "Frecuencia": frecuencias,
    "Amplitud": np.array(amplitudes),
    "Fase": np.array(fases),
    "Escala": np.array(escalas),

})
plt.plot(frecuencias, amplitudes, ".")
plt.title("Amplitud vs frecuencia")
plt.yscale("log")
plt.show()
plt.title("Fase vs frecuencia")
plt.plot(frecuencias, fases, ".")
plt.show()
#%% Guardado
save_folder = 'C:/Users/publico/Documents/l4-g6-2026-1C/piezo/datos/'
df.to_csv(save_folder+"barrido_lockin_entrada.csv", index=False, header=True)

