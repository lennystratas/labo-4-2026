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
osci = TDS1002B("USB0::0x0699::0x0363::C108013::INSTR")
fungen = AFG3021B("USB0::0x0699::0x0346::C034166::INSTR")
#%%
# Creamos listas vacias para guardar los datos
frecuencias_lista = []
tiempos = []
datach1 = []
datach2 = []
deltaVCH1 = []
deltaVCH2 = []

#frecuencias del barrido

frecuencias = np.linspace(349.1e3, 349.15e3, 150)
osci.set_time(1/(2*frecuencias[0]))
time.sleep(0.5)
escala_2 = np.diff(osci.get_range(2)).item()/10

for freq in frecuencias:    
    ############# TEKTRONIX ###############
    fungen.setFrequency(freq)
    
    ############# SIGLENT ###############
    # fungen.write('C1:BSWV FRQ,{:f}'.format(freq))
    print(f"Barriendo: FREQ {freq:.0f}") 
    

            
    ############# Osci ###############
    # if freq < 20:
    #     osci.set_time(20e-3)   
    # else:
    #     time.sleep(1) #Esperar a que el oscilo reciba la nueva señal, antes de pedirle que calcule el autoset 
    #     osci.autoset() # autoset necesario

    # time.sleep(4)
    
    
    # osci.set_time(1/(2*freq))
    # time.sleep(0.5)

    
    tiempo, data1, ymu1, uso_escala_1 = osci.read_data(1)
    _, data2, ymu2, uso_escala_2 = osci.read_data(2)
    
    while uso_escala_2 <= 0.4 or uso_escala_2 >= 0.8:
        if escala_2 < 20e-3 and uso_escala_2 <= 0.4:
            break
        escala_2 = escala_2/0.6 * uso_escala_2
        print(f"Nueva escala 2: {escala_2}")
        osci.set_channel(2, escala_2)
        time.sleep(0.5)
        _, data2, ymu2, uso_escala_2 = osci.read_data(2)
        

    #Guardamos lo medido
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
    "Frecuencias": frecuencias_lista,
    "Tiempo": tiempos,
    "VoltajeCH1": datach1,
    "VoltajeCH2": datach2, 
    "ResolucionVCH1": deltaVCH1, 
    "ResolucionVCH2": deltaVCH2
})

#%%Guardado
save_folder = "C:/Users/publico/Documents/l4-g6-2026-1C/labo-4-2026/PIEZOELECTRICO/datos/"
df.to_csv(save_folder+"barrido_osciloscopio_m7_3.csv", index=False, header=True)

#%% Capturar pantalla
# osci.write('DAT:ENC RPB')
# osci.write('DAT:WID 1')

# # Creamos listas vacias para guardar los datos
# frecuencias_lista = []
# tiempos = []
# datach1 = []
# datach2 = []
# deltaVCH1 = []
# deltaVCH2 = []

# fungen.write('DAT:SOU CH1') 
# # freq = fungen.query()

# #Canal 1
# osci.write('DAT:SOU CH1') 
# xze1, xin1, yze1, ymu1, yoff1 = osci.query_ascii_values('WFMPRE:XZE?;XIN?;YZE?;YMU?;YOFF?;', separator=';')
# data1 = osci.query_binary_values('CURV?', datatype='B', container=np.array)

# #Canal 2
# osci.write('DAT:SOU CH2') 
# xze2, xin2, yze2, ymu2, yoff2 = osci.query_ascii_values('WFMPRE:XZE?;XIN?;YZE?;YMU?;YOFF?;', separator=';')
# data2 = osci.query_binary_values('CURV?', datatype='B', container=np.array)

# #Conversion a voltaje
# tiempo = xze1 + np.arange(len(data1)) * xin1 #tiempo de ch1 y ch2 son iguales
# data1v = (data1 - yoff1) * ymu1 + yze1
# data2v = (data2 - yoff2) * ymu2 + yze2

# #Guardamos lo medido
# frecuencias_lista.extend([freq] * len(tiempo))
# tiempos.extend(tiempo)

# datach1.extend(data1v)
# datach2.extend(data2v)
# deltaVCH1.extend([ymu1] * len(tiempo))
# deltaVCH2.extend([ymu2] * len(tiempo)) 

# #Graficamos para ir viendo
# plt.plot(tiempo, data1v, label=str(freq)+"Hz")
# plt.plot(tiempo, data2v, label="CH2")
# plt.legend(loc=1)
# plt.show()
    
# # Create DataFrame in one step
# df = pd.DataFrame({
#     "Frecuencias": frecuencias_lista,
#     "Tiempo": tiempos,
#     "VoltajeCH1": datach1,
#     "VoltajeCH2": datach2, 
#     "ResolucionVCH1": deltaVCH1, 
#     "ResolucionVCH2": deltaVCH2
# })

# #Guardado
# save_folder = 'C:/Users/publico.LABORATORIOS/Documents/Verano 2026/RLC serie/'
# df.to_csv(save_folder+"data_RLC_pasbanda_6.csv", index=False, header=True)
#%%