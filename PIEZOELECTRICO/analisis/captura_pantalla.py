# -*- coding: utf-8 -*-
"""
Created on Fri Feb 13 15:47:10 2026

@author: Publico
"""

#imports, buscar instrumenots
#%%
import pyvisa as visa
import numpy as np
import matplotlib.pyplot as plt
import time
import pandas as pd
from instrumental import AFG3021B, TDS1002B

# Abro el resource manager
rm = visa.ResourceManager()
# Me fijo que instrumentos tengo conectados
print(rm.list_resources())
# Nombro cada instrumento
#%%

#imports, setear instrumentos
#%%
osci = TDS1002B('USB0::0x0699::0x0363::C065087::INSTR')
fungen = AFG3021B("USB0::0x0699::0x0346::C034166::INSTR")
#%%
# Creamos listas vacias para guardar los datos
tiempos = []
datach1 = []
datach2 = []
deltaVCH1 = []
deltaVCH2 = []


    

tiempo, data1, ymu1 = osci.read_data(1)
_, data2, ymu2 = osci.read_data(2)


frecuencias_lista.extend([freq] * len(tiempo))
tiempos.extend(tiempo)

datach1.extend(data1)
datach2.extend(data2)
deltaVCH1.extend([ymu1] * len(tiempo))
deltaVCH2.extend([ymu2] * len(tiempo)) 

#Graficamos para ir viendo
plt.plot(tiempo, data1, label=str(freq)+"Hz")
plt.plot(tiempo, data2, label="CH2")
plt.legend(loc=1)
plt.show()
    
# Create DataFrame in one step
df = pd.DataFrame({
    "Tiempo": tiempos,
    "VoltajeCH1": datach1,
    "VoltajeCH2": datach2, 
    "ResolucionVCH1": deltaVCH1, 
    "ResolucionVCH2": deltaVCH2
})

save_folder = 'C:/Users/publico/Documents/l4-g6-2026-1C/piezo/datos/'
df.to_csv(save_folder+"respuesta_pulso_4.csv", index=False, header=True)