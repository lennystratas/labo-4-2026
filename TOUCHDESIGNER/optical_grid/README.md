# Optical Grid — TouchDesigner (solo nodos nativos, sin GLSL)

Una grilla de celdas que se deforma en tiempo real según el optical flow de lo que pasa dentro de cada una. Está inspirado en el patch de *unavisionagradable*.

## Cómo usarlo

1. Abrí un proyecto en TouchDesigner (2023+ recomendado).
2. Ejecutá `build_optical_grid.py` de alguna de estas formas:
   - **Text DAT (recomendado)**: creá un Text DAT, poné la ruta del `.py` en su parámetro *File*, y click derecho → *Run Script*.
   - **Textport**, escribiendo *solo esta línea* (no pegues el contenido del script en el Textport: la consola corta los bloques en las líneas vacías y tira `IndentationError`):
     `exec(open(r'C:/ruta/a/build_optical_grid.py', encoding='utf-8').read())`
   - **MCP de TouchDesigner**: mandá el archivo a la herramienta que ejecuta Python dentro de TD.
3. Se crea `/project1/opticalGrid`. La salida es el nodo `OUT`.
4. Un segundo después aparece en el Textport un **reporte de verificación**. Si algo sale `FALLA` o figura un parámetro que no se pudo setear, está indicado ahí.

> Este script no se pudo correr dentro de TouchDesigner al escribirlo, porque no había acceso a TD. Por eso el builder prueba varios nombres de parámetros y verifica numéricamente las texturas clave, y en el caso de la orientación en Y la corrige solo.

## Parámetros (página *Optical Grid* del Base COMP)

| Parámetro | Qué hace |
|---|---|
| Columnas / Filas | Tamaño de la grilla (en vivo, no hace falta reconstruir) |
| Fuente | Cámara (Video Device In) o archivo (Movie File In) |
| Optical flow | `NVIDIA` = Optical Flow TOP (Windows + RTX 30xx o más nueva). `Nativo` = aproximación con Slope TOP × diferencia de frames (anda en cualquier GPU y en Mac) |
| Push | Las fronteras se mueven **en la dirección** del flow. Negativo = en contra |
| Grow | La celda con más movimiento (energía \|flow\|²) **se agranda** y empuja a las vecinas. Negativo = se achica |
| Límite | Máximo desplazamiento de cada frontera, en celdas (< 0.5). Con 0.45 una celda puede ir de 0.1× a 1.9× su tamaño |
| Suavizado flow | EMA sobre las estadísticas de flow por celda (0 = crudo, 0.99 = muy lento) |
| Suavizado grilla | EMA sobre la geometría final |
| Opacidad líneas | Las líneas blancas entre celdas |

## Cómo funciona

```
video ─► Optical Flow ─► (fx, fy, fx²+fy²) ─► Resolution → Cols×Rows (promedio por celda) ─► EMA
                                                        │
          ┌─────────────────────────────────────────────┴───────────────────┐
   fronteras de columna (por fila)                       fronteras de fila (globales)
   Dh = clamp(Push·(fx_i+fx_i+1)/2 + Grow·(E_i−E_i+1))    Dv = ídem con fy y el promedio de la fila
   × máscara (última columna = 0) ─► EMA                  × máscara (última fila = 0) ─► EMA
          └──────────────────────────► layout (x0, y0, w, h) por celda ◄──────┘
                                              │
            Geometry COMP con instancing por TOP (1 pixel = 1 quad)
            Render A: gradiente local × (1/N, 1/M)   Render B: color = origen de la celda fuente
                                              │
                         A + B = mapa UV ─► Remap TOP(video, mapa) ─► + líneas (Wireframe MAT) ─► OUT
```

### 1. Bordes fijos
Solo se desplazan las **fronteras interiores**. `Dh` guarda la frontera derecha de cada celda, y la de la última columna se multiplica por una máscara en cero. La frontera izquierda (`Dh_left`) es `Dh` corrida un pixel con *extend = zero*, así que la primera columna arranca siempre en 0.

### 2. Sin superposición, y lo que crece una celda lo pierde la vecina
Cada frontera se mueve como máximo `±Límite` (< 0.5 celda) alrededor de su posición de reposo, así que nunca puede cruzar a la siguiente:

- `x0 = (i + Dh_left)/N`
- `w = (1 + Dh − Dh_left)/N`

La celda `i` termina exactamente donde empieza la `i+1`, porque las dos usan el mismo valor de frontera. Si una se agranda, la vecina se achica en la misma cantidad. Las filas funcionan igual en vertical. El layout es *slice-and-dice*: la altura de las filas es global y las columnas se deforman de forma independiente en cada fila, como en la referencia.

### 3. Suavizado temporal
Hay dos EMAs hechas con Feedback TOP + Cross TOP:
1. Sobre las estadísticas de flow, para sacar el ruido del sensor.
2. Sobre los desplazamientos finales. Un promedio convexo de layouts válidos también es un layout válido, así que el suavizado **no puede** generar solapes.

### Por qué un mapa UV y no texturas por instancia
El instancing de TD solo puede **trasladar** las coordenadas de textura de cada instancia, no escalarlas. Por eso se renderizan dos pasadas en float32:
- una con el gradiente local de cada quad escalado a `(1/N, 1/M)`;
- otra con el origen de la celda fuente como color de instancia.

Sumadas dan, para cada pixel de salida, la coordenada de la imagen fuente que tiene que mostrar. El Remap TOP hace el resto: cada celda muestra su porción original de la imagen, estirada o comprimida.

## Ideas para seguir
- Más contraste: bajá Columnas/Filas o subí Grow. Si el movimiento se siente "al revés", invertí el signo de Push.
- Subdivisión recursiva (celdas dentro de celdas, como en la referencia): duplicá la etapa de layout con una grilla más fina dentro de cada fila.
- Overlays de texto con los valores de flow: `Text TOP` + `TOP to CHOP` de `stats_ema`.
