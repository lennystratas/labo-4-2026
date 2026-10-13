# OSSYRAVE — flyer animado en TouchDesigner

Documento de traspaso para otro asistente (o persona) que siga trabajando en este proyecto.
Explica qué quiere el usuario, cómo está armada la red y por qué, qué se probó y qué no funcionó.

- **Script que construye toda la red:** `touchdesigner/ossyrave_flyer.py` (único archivo fuente).
- **Vista previa sin TouchDesigner:** `touchdesigner/preview/` (corre los mismos shaders en WebGL2 con Chromium).
- **Humo:** adaptado de "Dry ice 2" de David Gallardo (xjorma), https://www.shadertoy.com/view/WlVyRV — licencia CC BY-NC-SA 3.0 (no comercial; mantener la atribución).

---

## 1. Qué quiere el usuario

Un **flyer animado vertical de 12 s** para la fiesta "OSSYRAVE", hecho en TouchDesigner, que se vea **elegante y profesional**, con una **red limpia y ordenada**. Requisitos acumulados a lo largo de la conversación (todos siguen vigentes salvo que diga lo contrario):

**Imagen**
- Se basa en una foto en blanco y negro/sepia de una bailarina con traje plateado y casco, que tenía humo pintado abajo. Debe **verse como la foto original**, pero con **humo animado delante y detrás de ella**.
- El usuario dio tres imágenes del mismo encuadre (1116×2000): la foto original (`foto.jpg`), un recorte de la chica con alfa (`recorte.png`) y un mapa de profundidad (`profundidad.png`, blanco = cerca). Después agregó un logo (`logo.png`, trazo blanco fino sobre transparente).
- Los archivos están **sueltos al lado del `.toe`**, no en una subcarpeta.

**Humo**
- Basado en el shader de Shadertoy, **sin las bolas ni el piso** del original, y **sin los huecos negros** que dejaban las bolas en el humo.
- Con **zonas vacías** (no una bruma pareja).
- **Fijo abajo desde el primer frame**, para que nunca se vea el corte del recorte a la altura de los pies.
- Que **suba hasta arriba, rápido**. Pidió dos veces más altura y velocidad; la última versión es la que le gustó ("Bien").
- **Lo que desplaza el humo es el texto**: las letras, al moverse, empujan el humo solas. Cualquier animación que el usuario haga a las letras tiene que empujar el humo sin tocar nada más.

**Título y logo**
- El texto es **OSSYRAVE**, en **una sola línea**.
- Estética **rave**: letras negras extendidas. **No le gustó** la primera versión (letras que subían desde abajo, estilo sobrio).
- Las letras **entran desde los costados** (no desde abajo).
- **Primero aparece el logo**, medio chico, arriba al centro; **después OSSYRAVE encima** (se interpretó como superpuesto y centrado sobre el logo; el usuario no lo objetó).
- **Sin glitch / separación RGB**: se agregó y el usuario pidió sacarlo.
- **Contraste siempre**: sobre negro el texto es blanco y sobre blanco es negro, **usando un Composite TOP**.
- **Animar las letras tiene que ser fácil.**

**Técnico**
- Timeline **fijo en 12 s** (60 fps, frames 1–720).
- **Determinista**: el mismo resultado en cada reproducción de esos 12 s.
- Se permitía usar Higgsfield (generación de imágenes) si hacía falta. Se intentó para un fondo limpio sin humo, pero el proxy del entorno bloqueó la subida; se resolvió con un shader.

**Cómo prefiere trabajar el usuario:** habla en español rioplatense, prueba en su TouchDesigner y pega los errores del textport. Agradece entregas de un solo script que se pega en un Text DAT y se corre ("Run Script").

---

## 2. Cómo se usa

1. Poner `foto.jpg`, `recorte.png`, `profundidad.png` y `logo.png` al lado del `.toe`.
2. Pegar **todo** `ossyrave_flyer.py` en un Text DAT → click derecho → **Run Script**.
   - Borra y recrea `/project1/ossyrave`.
   - Configura el timeline raíz: 60 fps, frames 1–720.
   - Al final verifica las conexiones e imprime `Flyer creado en /project1/ossyrave`, o líneas `ATENCION: …` si alguna entrada quedó mal.
3. Ajustar desde la página de parámetros **Flyer** del COMP `ossyrave`.
4. Animar las letras en `ossyrave/titulo/animacion`.
5. Exportar con el botón **Exportar 12 s** (graba `ossyrave.mov`).

Fuera de TouchDesigner el script no construye nada (`try: op / except NameError`). Eso permite importarlo para leer los shaders, que es lo que hace la vista previa.

---

## 3. Mapa de la red

```
/project1/ossyrave   (baseCOMP, parentshortcut = "Flyer", página de parámetros "Flyer")
│
├─ foto, recorte, profundidad, logo        Movie File In TOP (rutas = parámetros del COMP)
│
├─ titulo/  (baseCOMP)
│    animacion (Text DAT, módulo Python)   ← acá se anima todo
│    letra1..8 (Text TOP) → mov1..8 (Transform TOP) → letras (Composite TOP, over) → out1
│
├─ titulo_out (Select TOP → titulo/out1)
│
├─ humo/  (baseCOMP)
│    texto (Select TOP → ../titulo/out1) → mascara (Blur TOP, a resolución SIM)
│    negro (Constant TOP, rgba32float, alfa 0)  → sim_a_anterior, sim_d_anterior (Feedback TOP)
│    sim_a → sim_b → sim_c → sim_d             (GLSL TOP, rgba32float, resolución SIM)
│    render (GLSL TOP, resolución RES) → out1
│
├─ humo_out (Select TOP → humo/out1)
│
├─ humo_partido  (GLSL)  humo_out + profundidad + recorte   → qué parte del humo va detrás
├─ capas         (GLSL)  foto + recorte + humo_partido      → fondo limpio, humo atrás, chica, humo adelante
├─ fondo         (GLSL)  capas + logo                       → logo
├─ contraste     (Composite TOP, operand = difference)  fondo + titulo_out
├─ terminacion   (GLSL)  contraste                          → viñeta + grano, alfa = 1
├─ final         (Null TOP, viewer)
├─ grabar        (Movie File Out TOP, ossyrave.mov)
├─ exportar      (Parameter Execute DAT, pulso "Exportar")
└─ control_grabacion (Execute DAT, onFrameEnd)
```

Constantes al principio del script:

| Constante | Valor | Uso |
|---|---|---|
| `RES` | 1116×2000 | Resolución del flyer, igual a la de las imágenes |
| `SIM` | 558×1000 | Resolución de la simulación (mitad) |
| `FPS` / `DURACION` | 60 / 12 | Timeline |
| `TITULO` | `'OSSYRAVE'` | Crea un Text TOP por letra |

---

## 4. Convención de shaders (Shadertoy → GLSL TOP)

Todos los GLSL TOP se escriben al estilo Shadertoy (`mainImage(out vec4, in vec2)`). `glsl_source()` les agrega:

- **`HEADER`**:
  - `uniform vec4 uTime` (x = iTime, y = iTimeDelta, z = iFrame) y `uniform vec4 uP` (4 parámetros de la pasada).
  - Macros `iTime`, `iFrame`, `iResolution` (sale de `uTDOutputInfo.res.zw`).
  - Salida `_stOut`.
  - Un reemplazo de `texelFetch` que devuelve 0 fuera de la textura. En WebGL es así por defecto; en desktop GL no está definido y desestabilizaba el solver de presión.
- **Macros por canal:** `#define iChannelN sTD2DInputs[N]`.
- **`COMMON`**: constantes del humo, `hash12`, `hash41`, `noise`, `lightPath`, `dist2`.
- **`FOOTER`**: `main()` que llama a `mainImage` con `gl_FragCoord` y escribe `TDOutputSwizzle`.

`glsl_pass()` crea el Text DAT `<nombre>_glsl` y el GLSL TOP. Configura:
- **Vectors 0** = `uTime` con expresiones del timeline raíz: `(me.time.frame - me.time.start)/me.time.rate`, `1/me.time.rate`, `me.time.frame - me.time.start`.
- **Vectors 1** = `uP` con las expresiones que se le pasen (normalmente `parent.Flyer.par.X`).
- **Vectors 2** = opcional (`extra`), lo usa `fondo` para `uLogo`.

---

## 5. Componentes, uno por uno

### 5.1 Entradas
Movie File In TOP con `file` = `parent.Flyer.par.Foto/Recorte/Profundidad/Logo`. Las rutas son relativas a la carpeta del `.toe`.

### 5.2 `titulo/` — letras y animación
- **Un Text TOP por letra** (`letra1..8`, resolución RES completa, letra centrada, fondo con alfa 0, color blanco puro 1,1,1).
  - Fuente: `parent.Flyer.par.Fuente` (Arial Black).
  - Tamaño: `parent.Flyer.par.Tamano` (125).
  - Opacidad: `fontalpha` por expresión.
- **Un Transform TOP por letra** (`mov1..8`): `tx`, `ty` (fracción de pantalla, 0 = centro), `rotate`, `sx`, `sy`. Todo por expresión:
  `mod.animacion.letra(i, me.time.frame)['x' | 'y' | 'rot' | 'escala_x' | 'escala_y' | 'opacidad']`.
- `letras` (Composite TOP, over) → `out1`.

**`animacion` (Text DAT usado como módulo).** Función pura del frame, y por eso determinista. API:

| Función | Devuelve |
|---|---|
| `letra(i, frame)` | `{'x', 'y', 'escala_x', 'escala_y', 'rot', 'opacidad'}` de la letra `i` |
| `logo(frame)` | `{'opacidad', 'tamano', 'y'}` del logo (lo usa `fondo` vía `uLogo`) |

Comportamiento actual:
- **Logo:**
  - Aparece entre los segundos 0,4 y 1,6 (`LOGO_ENTRADA`, `LOGO_FUNDIDO`), con fundido, crecimiento de 92% a 100% y parpadeo al principio.
  - Mide 36% del ancho (`LOGO_TAMANO`) y está centrado en `y = 0.5 + Y`, detrás del título.
- **Título:**
  - Una línea a la altura `Y = 0.32` (fracción desde el centro, cerca de 18% desde arriba), con letras extendidas (`ESTIRAR = 1.2`) y separación `ANCHO = 0.116` del ancho.
  - Desde el segundo 2 (`ENTRADA`), "OSSY" entra desde la izquierda y "RAVE" desde la derecha. Arrancan justo afuera de la pantalla (`x = ±0.62`) y entra primero la letra con más recorrido.
  - Curva smoothstep de `VIAJE = 2` s, `DESFASE = 0.1` s entre letras.
  - Mientras se mueve, la letra se estira (hasta ×1,5 en X y 0,85 en Y). Al llegar parpadea durante `DESTELLO = 0.3` s.

**Para animar a mano:** se puede editar el módulo o poner keyframes / "Edit Animation" sobre los parámetros de `mov1..8` y `letra1..8` (reemplazando la expresión). Cualquier cambio de posición, escala u opacidad de las letras empuja el humo automáticamente (§5.3).

> La velocidad de las letras importa. Por encima de unos 8–10 px por frame (a resolución SIM) el empuje del humo sale "acanalado", porque la máscara salta más que su borde suavizado. Por eso las curvas son de aceleración y frenado, no de entrada brusca.

### 5.3 `humo/` — simulación de fluido 2D (en espacio de pantalla)
Es un solver de fluidos tipo Shadertoy con 4 pasadas a resolución SIM, todas en rgba32float. El espacio de la simulación coincide con la pantalla: el uv de la simulación es el uv del flyer.

| Nodo | Entradas | Salida | Qué hace |
|---|---|---|---|
| `texto` | Select de `../titulo/out1` | RGBA | Letras |
| `mascara` | texto | RGBA a SIM | Blur `size = 12`: máscara suave de las letras |
| `sim_a` | 0: `sim_d_anterior` (presión), 1: `sim_a_anterior`, 2: `mascara` | xy velocidad, z densidad, **w máscara de este frame** | Advección + inyección + flotación + empuje del texto |
| `sim_b` | 0: sim_a | x divergencia | Divergencia |
| `sim_c` | 0: sim_b, 1: `sim_d_anterior` | x presión, y divergencia | Solver de presión, 1ª iteración |
| `sim_d` | 0: sim_c | x presión | Solver de presión, 2ª iteración |
| `render` | 0: sim_a, 1: sim_d (no se usa) | RGBA premultiplicado a RES | Render volumétrico del humo |

- **Feedback TOPs** (`sim_a_anterior`, `sim_d_anterior`): la entrada es `negro` y el target es sim_a / sim_d. Su `reset` tiene la expresión `me.time.frame <= me.time.start`, así que el frame 1 siempre arranca de cero.
- **`render` tiene sim_d conectado como entrada 1, sin usarlo.** Sirve para que sim_d se calcule cada frame, porque si no nadie lo pide. No sacar esa conexión.
- **sim_c / sim_d:** las sumas `getDiv()` y `getPre()` (≈300 lecturas) son tablas del autor. El script las **genera en Python** (`_tables()`, `_sum_func()`) con los mismos coeficientes (verificado contra el original).

**sim_a en detalle** (parámetros `uP` = Densidad, Empuje, Subida):
1. **Advección** de Euler, igual que el original (con `dissipation = 0.95`).
2. **Colchón fijo de humo** sobre el piso: `colchon = (1 − smoothstep(0, 0.17, y)) · (0.55 + 0.45·noise)`.
   - En `iFrame == 0`, densidad = colchón y velocidad = 0.
   - Cada frame, densidad = `max(densidad, colchon)`.
   - Es lo que tapa el corte del recorte en los pies desde el primer frame.
3. **Flotación en columnas:** `velocity.y += 0.12 · SUBIDA · densidad · columnas`, donde `columnas` (0,4–1) es un ruido que se desplaza. Después `velocity *= 0.995`.
4. **Inyección** en la zona baja (`piso = 1 − smoothstep(0.02, 0.30, y)`):
   - Ruido fino: `0.004 · piso · DENSIDAD`.
   - Ruido grande con umbral: `smoothstep(0.10, 0.26, |ruido|) · 0.04 · piso · DENSIDAD`. El umbral deja zonas vacías.
5. **Empuje del texto** (flujo óptico de la máscara):
   - `m` = máscara actual, `mp` = máscara del frame anterior (leída del **alfa** de `sim_a_anterior`), `g` = gradiente de `m`.
   - `vText = −(m − mp)·g / (|g|² + 1e-3)`, limitada a 10 px por frame.
   - `velocity = mix(velocity, vText·EMPUJE, m)` y `density *= 1 − m`: las letras son obstáculos sólidos que arrastran el humo y lo apartan.
6. **Disipación** que aumenta con la altura: `density *= 0.997 − 0.010·y`. Además, un 4% extra en el 20% superior, para que no se acumule contra el borde.
7. Salida: `vec4(velocidad, densidad, m)`.

**render** (`HUMO`):
- La cámara mira el campo de densidad casi desde arriba (`rd = normalize(0, −1, 0.35)`). Cada píxel de pantalla corresponde al mismo uv de la simulación.
- La densidad se trata como un campo de alturas (×`fogHeigth`) y se recorre en 24 rebanadas, con sombras propias hacia una luz.
- La **luz se mueve** siguiendo `lightPath(iFrame)`, que es el recorrido de la bola blanca del shader original (el usuario pidió conservar la luz moviéndose cuando se sacaron las bolas).
- Exposición: `l = sqrt(1 − exp(−E·3·BRILLO))`, más `ambiente = 0.25` para que las sombras del humo no se vean sucias.
- Sale `vec4(l·a, l·a, l·a, a)`: monocromo y premultiplicado.

### 5.4 Composición
Cada GLSL TOP tiene **3 entradas como máximo** (ver §8).

- **`humo_partido`** (humo, profundidad, recorte; `uP.x` = Corte). Decide, por píxel, qué parte del humo queda **detrás** de la chica.
  - Profundidad del humo: `mix(0.2, 0.95, smoothstep(CORTE, 0, y))` + ruido ±0,125. Abajo el humo está cerca de cámara y arriba lejos.
  - `delante = smoothstep(−0.05, 0.05, profHumo − profundidad)`.
  - `atras = (1 − delante) · alfa_chica` (alfa con el mismo fundido de pies que en `capas`).
  - Salida rgba16float: x = luz del humo, y = opacidad, z = fracción detrás.
- **`capas`** (foto, recorte, humo_partido; `uP.x` = Limpieza):
  - **Fondo limpio:** oscurece el humo pintado de la foto en la zona baja: `foto *= 1 − smoothstep(0.12, 0.45, lum)·(1 − smoothstep(0.45, 0.66, y))·LIMPIEZA`.
  - **Recorte:** premultiplicado, con fundido en los pies `smoothstep(0.055, 0.14, y)`.
  - **Humo:** teñido sepia `(1, 0.95, 0.86)` y separado en dos capas.
  - **Orden:** foto → humo atrás → chica → humo adelante.
- **`fondo`** (capas, logo; `uLogo` = opacidad, tamaño, altura). Dibuja el logo centrado en x con su alfa ×2,2 (el trazo original es tenue, alfa máximo 179/255), en color `(0.97, 0.96, 0.93)`. El logo **no** se invierte con el contraste y **no** empuja el humo.
- **`contraste`** (Composite TOP, `operand = 'difference'`; fondo, titulo_out). Con el título en blanco puro da `|fondo − título|`: sobre negro → blanco, sobre humo blanco → negro. Es lo que pidió el usuario con un Composite TOP.
- **`terminacion`** (contraste; `uP.x` = Grano):
  - Viñeta suave y grano determinista `hash12(fragCoord + iFrame·17.31)`.
  - Fuerza alfa = 1 por si el Difference del Composite TOP altera el alfa (no verificado en TD).
- **`final`** (Null) → **`grabar`** (Movie File Out).

### 5.5 Parámetros de la página "Flyer"

| Parámetro | Defecto | Va a |
|---|---|---|
| Foto / Recorte / Profundidad / Logo | `foto.jpg`, `recorte.png`, `profundidad.png`, `logo.png` | Movie File In |
| Densidad | 1 | sim_a `uP.x` (inyección) |
| Empuje | 1 | sim_a `uP.y` (fuerza del texto sobre el humo) |
| Subida | 1 | sim_a `uP.z` (flotación). Más o menos arriba de 1,3–1,5 el humo empieza a llenar todo el cuadro |
| Brillo | 1 | render `uP.x` |
| Corte | 0.38 | humo_partido `uP.x` (hasta qué altura el humo pasa por delante de ella) |
| Limpieza | 1 | capas `uP.x` (borrar el humo pintado de la foto) |
| Grano | 0.04 | terminacion `uP.x` |
| Fuente / Tamano | Arial Black / 125 | Text TOPs |
| Exportar 12 s | pulso | parameterexecuteDAT `exportar` |

---

## 6. Determinismo y exportación
- **Tiempo:** todo depende de `me.time.frame` del timeline raíz, nunca de `absTime`. El script deja el timeline en 60 fps, 1–720.
- **Arranque:** los Feedback TOP se resetean en el frame 1 y sim_a inicializa el colchón en `iFrame == 0`.
- **Sin azar externo:** todo el ruido es por hash del frame y la posición.
- **La simulación tiene memoria:** para reproducir exactamente hay que **reproducir desde el frame 1 sin saltear frames**. Si se scrubea o se recalcula en pausa, la simulación se desfasa.
- **Exportar:**
  - `exportar` (onPulse): `project.realTime = False`, va al frame de inicio, prende `grabar.par.record` y da play.
  - `control_grabacion` (onFrameEnd): al llegar al último frame apaga la grabación y vuelve a poner `realTime = True`.

---

## 7. Vista previa sin TouchDesigner (`touchdesigner/preview/`)
Corre **los mismos shaders**, extraídos del script, en WebGL2 dentro de Chromium headless (Playwright), con las imágenes reales. Así se validó todo, porque en el entorno de desarrollo no hay TouchDesigner.

```bash
cd touchdesigner/preview
python3 gen.py ../ossyrave_flyer.py /tmp/passes.json      # shaders + animación por frame
node run.js /tmp/passes.json /tmp/out 120,300,720 0.5 0.5 '{"Subida":1}' /ruta/a/imagenes
#            datos          salida  frames a guardar  simScale outScale  parámetros       carpeta con foto.jpg, recorte.png, profundidad.png, logo.png
```

- **`simScale = 1`** es la resolución real de la simulación (558×1000), pero es lenta (~1,5 s por frame con SwiftShader). Con `0.5` alcanza para iterar (~0,4 s por frame, sin el detalle fino).
- **`page.js` imita la red:**
  - Mismas pasadas y entradas, feedbacks por ping-pong.
  - Las letras se dibujan con Canvas 2D (fuente Inter Black en lugar de Arial Black) usando los valores de `animacion.letra()`.
  - El Blur TOP se aproxima con `blur(5px·simScale)` de canvas.
  - El Composite TOP Difference se emula con un shader propio (`passes['diff']`).
- **Si cambia la red** (pasadas, entradas, uniforms), hay que actualizar `gen.py` (lista de pasadas y cantidad de canales) y `page.js` (función `renderOut` / `step`).
- **Las imágenes no están en el repo** (es una foto de una persona real). Se las pide al usuario.

---

## 8. Lecciones de TouchDesigner (no repetir errores)
- **Un GLSL TOP no aceptaba una 4.ª entrada conectada desde Python.** `inputConnectors[3]` daba `IndexError`, y la alternativa `connect(op)` tampoco la agregaba. Se vio dos veces (sim_a y composición). No se averiguó la causa.
  - **Regla:** máximo 3 entradas por nodo.
  - Por eso la máscara del frame anterior viaja en el alfa de sim_a, y la composición está partida en `humo_partido` / `capas` / `fondo`.
- **Los cables entre COMPs** (salida de `titulo`/`humo` hacia nodos de afuera) no se conectaban. Se reemplazaron por **Select TOP** por ruta.
- **`wire()`** registra cada conexión esperada y **`check_wiring()`** la verifica al final, imprimiendo `ATENCION` si alguna falla. El error típico de una entrada faltante es `array index out of range 'N'` al compilar el GLSL.
- **Nombres de parámetros de TD sin probar:** se escribieron de memoria y funcionaron en la versión del usuario hasta donde llegó. La exportación (`project.realTime`, `root.time.*`, Movie File Out) **no se confirmó** que funcione.
- **El modo Difference del Composite TOP** con alfa no está verificado; por eso `terminacion` fuerza alfa = 1.
- **Las imágenes `.webp` originales** se convirtieron a PNG porque no se sabe si TD lee webp.
- **El script tiene que pegarse completo:** pegar desde la mitad del archivo da `IndentationError`.

---

## 9. Historial de ajuste del humo (para no repetir pruebas)
- **Flotación pareja y fuerte** (0,10–0,15 por densidad, disipación 0,996): el humo **llena todo el flyer** y lava la imagen. Rechazado.
- **Flotación solo del humo nuevo** (sin el colchón) **o columnas con umbral duro**: el humo **casi no sube**.
- **0,096 + disipación `0.997 − 0.008·y`**: llega al título hacia el segundo 5. El usuario pidió más.
- **Actual, 0,12 + frenado 0,995 + disipación `0.997 − 0.010·y`**: llega al título en ~2 s y se sostiene con zonas oscuras hasta el segundo 12. Una variante con 0,13 / 0,996 / 0,012 era más pesada abajo.
- **Inyección:** con 0,07 el humo arrancaba como una mancha plana saturada. Con 0,04 y umbral tiene estructura.

---

## 10. Pendientes / ideas abiertas
- **Probar en TD:** el botón Exportar y que el resultado de dos exportaciones sea idéntico.
- **Contraste del logo:** si el usuario quiere que el logo también se invierta sobre el humo, pasarlo por el mismo `contraste`.
- **Fuente:** si las letras se tocan con Arial Black, bajar `Tamano` o subir `ANCHO` en `animacion`.
- **Resolución:** el flyer sale a 1116×2000, la medida de las imágenes. Si hace falta 1080×1920 para Instagram, reescalar o recortar al final.
