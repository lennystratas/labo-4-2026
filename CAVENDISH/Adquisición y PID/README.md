# Adquisición y PID — Cavendish con realimentación electrostática

Mantiene el péndulo de torsión **quieto en el nulo** con un PID que comanda
**2 canales de una fuente de tensión** (cada canal alimenta 2 capacitores que
actúan juntos; también sirven 2 fuentes separadas). La **fuerza de control**
necesaria para tenerlo quieto *es la medición*: al acercar la masa, cambia.

La posición se mide por **palanca óptica**: una cámara filma el spot del láser
y se calcula su **centroide** (sin asumir forma del spot).

```
cámara → centroide → PID → fuerza pedida → 2 tensiones → (se registra todo)
```

---

## Puesta en marcha rápida

Todo lo que se instala extra (solo para el hardware real):
```
pip install pyserial
```
(`numpy`, `opencv` y `matplotlib` ya están.) La fuente es una **Hantek PPS2320A**
por puerto serie (USB), usando sus **2 canales** (CH1, CH2) como las 2 fuentes.

**1) Calibrar (solo clicks):**
```
python calibracion.py
```
- `f` (sin láser) → captura el fondo.
- Subí el slider **umbral** hasta ver solo el haz (tecla `v` para ver la imagen limpia).
- `1` y clic en una marca real; `2` y clic en otra a **distancia conocida**; subí el slider **dist mm** a esa distancia → el mm/px se calcula solo.
- `o` y clic donde quieras el **cero**.
- `s` → **guarda** (en `calibracion/`). `q` → salir.

**2) Correr el lazo:**
```
python control_loop.py                 # cámara + fuentes + PID
python control_loop.py --sin-fuentes   # solo medir y mostrar (sin fuentes, para probar la cámara)
python control_loop.py --sin-ventana   # sin ventana (headless)
```
Los datos se guardan en `../Datos/medicionNN/`. `q` cierra la ventana.

**Calculadora de fuerza (suelta):**
```
python fuerza.py --V 25 --b 0.05 --d 1e-3 --brazo 0.03
```

---

## Si la fuente no responde — `probar_fuente.py`

**Ojo:** el log muestra la tensión que el PID *pide* (lo que `aplicar()` comanda),
**no** lo que la fuente confirma. Así que ver "la tensión cambiando" en el log
**no** prueba que la comunicación ande. Para confirmar de verdad, este script
**lee de vuelta** de la fuente:

```
pip install pyserial                       # (una vez)
python probar_fuente.py                     # lista los puertos COM
python probar_fuente.py --puerto COM3       # diagnostico: setea y LEE de vuelta
python probar_fuente.py --puerto COM3 --barrer        # prueba varios bauds
python probar_fuente.py --puerto COM3 --backend visa  # probar pyvisa (pip install pyvisa pyvisa-py)
python probar_fuente.py --puerto COM3 --dtr off --rts off
```

Si `modelo` trae texto y el `preset después` refleja lo seteado → comunicación OK.
Causas típicas si no anda (en orden): **baud** equivocado (usá `--barrer`),
**puerto** equivocado, **DTR/RTS** (probá `--dtr off --rts off`), o falta
`pyserial`. Cuando encuentres lo que funciona, ponelo en `parametros.py`
(`PUERTO_FUENTE`, `BAUD_FUENTE`, `BACKEND_FUENTE`, `DTR_FUENTE`, `RTS_FUENTE`).

> Sobre pyvisa: si la fuente es un puerto COM, pyvisa (ASRL) usa pyserial por
> debajo, así que rara vez cambia el resultado; está como opción por las dudas.

**Confirmado (con pyvisa):** la PPS2320A responde **una línea a cada comando**
(los `set` devuelven `ok`). Por eso hay que **leer esa respuesta después de cada
comando** (lockstep); si no, las lecturas salen desfasadas. Ya está resuelto en
`ActuadorPPS2320A` (`_set`/`_query`) y en `probar_fuente.py`. El formato de
lectura es en **centésimas de V** (`2121` = 21.21 V).

---

## El único archivo de números: `parametros.py`

Ahí cambiás (solo el número después del `=`): geometría de los capacitores
(`b`, `d`, brazo…), tensiones (`V_MAX`, `V_BIAS`), ganancias del PID y rutas.
**La calibración de la cámara NO va ahí** (se hace en `calibracion.py`).

---

## Modelo de fuerza (Fig. 13)

Fuerza lateral de un capacitor:  **F = FACTOR · ε_r · ε₀ · V² · b / d**
(no depende del solapamiento `x`). `FACTOR=1.0` = fórmula de la guía;
poné `0.5` si tu cátedra usa la convención con ½. El par push-pull da
`F_neta = 2k(V_A² − V_B²)`, lineal en el comando del PID.

---

## Datos que se registran

`Datos/medicionNN/medicionNN_nnnn.txt` (tab-separated, encabezado comentado con `#`):

```
t_s  x_mm  y_mm  valido  setpoint_mm  error_mm  cmd  V_A  V_B  F_neta_N  V_A_leido  V_B_leido
```

Las 3 primeras columnas siguen el formato viejo (compatibles con los análisis
existentes). `F_neta_N` es la fuerza de control: **la medición del experimento.**
`V_A`/`V_B` son las tensiones **comandadas**; `V_A_leido`/`V_B_leido` son las
**medidas en la fuente** (confirman el hardware; quedan `nan` si `LEER_TENSION_REAL=False`
en `parametros.py`, o si la lectura falla).

---

## Tuneo del PID

La salida del PID es un **comando en [−1, 1]** = fracción de la fuerza máxima.
Las ganancias de `parametros.py` (`KP=2.8, KI=0.8, KD=5.6`) están **validadas en
el simulador** (ver `verificacion_simulada/verificacion.png`) y son un **punto de
partida**. En el laboratorio el período del péndulo, la palanca óptica (mm/rad)
y la escala de fuerza son distintos, así que reajustá:

1. Empezá con `KI=0` y `KP` chico; subí `KP` hasta que reaccione.
2. Subí `KD` hasta que deje de oscilar (amortigua; es la clave).
3. Subí `KI` de a poco para borrar el error de régimen (sin que oscile).

`KD` grande con ruido de cámara → subí `TAU_DERIV` (filtra la derivada).

---

## Para MAÑANA en el laboratorio (checklist)

- [ ] `parametros.py`: cargar **geometría real** (`b`, `d`, `BRAZO`) y `V_MAX`, `V_BIAS`.
- [ ] `parametros.py`: poner el **puerto** (`PUERTO_FUENTE`, p.ej. `COM3`) y el
      **baud** (`BAUD_FUENTE`). Para ver los puertos:
      `python -m serial.tools.list_ports`
- [ ] Confirmar el baud: al correr `control_loop.py` imprime el **modelo** de la
      fuente (comando `a`). Si sale vacío/basura, probá `BAUD_FUENTE` = 2400 / 4800 / 115200.
- [ ] Verificar que la salida prende: el equipo usa `O1` (ON) / `O0` (OFF). Si los
      canales no salen independientes, descomentá `self._cmd("O2")` en `ActuadorPPS2320A`.
- [ ] `python calibracion.py` con la cámara real.
- [ ] `python control_loop.py --sin-fuentes` para chequear la medición antes de actuar.
- [ ] Reajustar el PID (ver arriba).

---

## Tests

```
python tests/correr_todos.py
```
Corren sin pytest (Python puro). Cubren fuerza, PID (anti-windup, derivada),
visión (centroide, calibración), mapeo de tensiones y el registro.

## `verificacion_simulada/` (se puede borrar)

El simulador del péndulo y el script de verificación que usé para comprobar que
el lazo funciona **sin hardware**. No hace falta para el laboratorio; está acá
por si querés re-verificar o re-derivar ganancias. Para correrlo:
```
python verificacion_simulada/verificar_sim.py
```
