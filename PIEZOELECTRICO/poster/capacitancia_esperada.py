# %%
import numpy as np
from scipy.constants import epsilon_0 as e_0

d = 4e-3
l = 50e-3
Dl = 1e-3
e_r = (4.6 + 4.51) / 2
De_r = (4.6 - 4.51) / 2
# C2 =  e_r* e_o * A/d = e_r* e_o * d*l/d = e_r, e_0 * l
C2 = e_r * e_0 * l
# Incertezas
dC2_dl = e_r * e_0
dC2_de_r = e_0 * l
DC2 = np.sqrt((dC2_dl * Dl) ** 2 + (dC2_de_r * De_r) ** 2)
print(f"$C2_{{esp}} = ({C2 * 1e12:.2f} \\pm  {DC2 * 1e12:.2f})$ pF")


# C2_esp es  e_r* e_o * A/d = e_r* e_o * d*l/d = e_r, e_0 * l
