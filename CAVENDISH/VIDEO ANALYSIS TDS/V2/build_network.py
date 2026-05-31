# =====================================================================
#  BUILDER - Medidor de posicion de laser
#  Pegar TODO este texto en un Text DAT y hacer click derecho > Run
#  (o tecla Ctrl+R con el DAT seleccionado).
#
#  Crea y cablea toda la red, escribe los codigos en los DATs y
#  configura los parametros. Es idempotente: si volves a correrlo,
#  borra los nodos que ya existen (con estos nombres) y los recrea.
#  NO toca tu DAT builder ni otros nodos con nombres distintos.
# =====================================================================

D = parent()              # donde se construye = padre de este DAT
report = []               # mensajes de exito/fallo
created = {}

# ----------------------- helpers ------------------------------------
def make(t, name, x=0, y=0):
    ex = D.op(name)
    if ex:
        try: ex.destroy()
        except Exception as e: report.append('DESTROY FAIL %s: %s' % (name, e))
    try:
        o = D.create(t, name)
        o.nodeX = x; o.nodeY = y
        created[name] = o
        return o
    except Exception as e:
        report.append('CREATE FAIL %s: %s' % (name, e))
        return None

def wire(src, dst, idx=0):
    if src and dst:
        try:
            dst.inputConnectors[idx].connect(src)
        except Exception as e:
            report.append('WIRE FAIL %s->%s[%d]: %s' % (
                getattr(src,'name','?'), getattr(dst,'name','?'), idx, e))

def setp(o, name, val):
    if not o: return
    try:
        getattr(o.par, name).val = val
    except Exception as e:
        report.append('PAR FAIL %s.%s = %r : %s' % (o.name, name, val, e))

def setexpr(o, name, expr):
    if not o: return
    try:
        p = getattr(o.par, name)
        p.expr = expr
        p.mode = ParMode.EXPRESSION
    except Exception as e:
        report.append('EXPR FAIL %s.%s : %s' % (o.name, name, e))

def setq(o, name, val):
    # como setp pero silencioso (para parametros cuyo nombre varia por version)
    if not o: return
    try: getattr(o.par, name).val = val
    except Exception: pass

# ----------------------- TOPs (procesamiento) -----------------------
# 'source' es la FUENTE de todo: la camara entra aca, pero podes enchufarle
# un Movie File In para probar con un video pregrabado (ver GUIA).
cam    = make(videodeviceinTOP, 'cam',    -200, 0)
source = make(nullTOP,          'source',  0,   0)
lum    = make(monochromeTOP,    'lum',     200, 0)
bg     = make(moviefileinTOP,   'bg',      200, -150)
sub    = make(compositeTOP,     'sub',     400, 0)
clean  = make(levelTOP,         'clean',   600, 0)

wire(cam,    source, 0)
wire(source, lum,    0)
wire(lum,    sub,    0)
wire(bg,     sub,    1)
wire(sub,    clean,  0)

# bg: archivo de fondo (se crea al apretar el boton "Fondo")
setp(bg, 'file', project.folder + '/bg.png')

# sub = lum - bg (clampea negativos a 0). Resolucion = source (ancla de dimensiones):
# fuerza a que toda la cadena tenga las dimensiones del source, sin importar bg.
setp(sub, 'operand', 'subtract')
setp(sub, 'outputresolution', 'custom')
setexpr(sub, 'resolutionw', "op('source').width")
setexpr(sub, 'resolutionh', "op('source').height")

# clean: umbral (sube Black Level) -> pone a 0 lo que esta por debajo del umbral,
# asi el centroide NO se sesga por el fondo. Hereda resolucion de sub (=source).
setexpr(clean, 'blacklevel', "op('CONTROL').par.Threshold")
# 32-bit float para precision (si tu version no permite ese nombre, se ignora)
setq(clean, 'format', 'rgba32float')

# ----------------------- Script CHOP (centroide) --------------------
# El centroide se calcula EXACTO con numpy sobre 'clean': suma ponderada por
# intensidad sobre TODOS los pixeles. No depende de filtros de downscale, asi
# que es igual de robusto en X y en Y. 'chopexec' lo vigila -> cocina cada frame.
measure = make(scriptCHOP, 'measure', 800, 0)

# ----------------------- CONTROL (parametros) -----------------------
ctrl = make(baseCOMP, 'CONTROL', 600, 250)
if ctrl:
    try:
        pg = ctrl.appendCustomPage('Medidor')

        th = pg.appendFloat('Threshold', label='Umbral (0-1)')
        th[0].normMin = 0; th[0].normMax = 1; th[0].default = 0.08; th[0].val = 0.08

        sp = pg.appendFloat('Saveperiod', label='Guardar cada (s)')
        sp[0].normMin = 1; sp[0].normMax = 600; sp[0].default = 60; sp[0].val = 60

        kd = pg.appendFloat('Knowndist', label='Dist. conocida (mm)')
        kd[0].normMin = 1; kd[0].normMax = 1000; kd[0].default = 100; kd[0].val = 100

        for nm, dv in (('Marker1x',0.3),('Marker1y',0.5),('Marker2x',0.7),('Marker2y',0.5)):
            mp = pg.appendFloat(nm)
            mp[0].normMin = 0; mp[0].normMax = 1; mp[0].default = dv; mp[0].val = dv

        mpp = pg.appendFloat('Mmperpx', label='mm/px (auto)')
        mpp[0].expr = ("me.par.Knowndist / max(("
                       "((me.par.Marker2x-me.par.Marker1x)*op('source').width)**2 + "
                       "((me.par.Marker2y-me.par.Marker1y)*op('source').height)**2)**0.5, 1e-9)")
        mpp[0].mode = ParMode.EXPRESSION
        mpp[0].readOnly = True

        # --- estado (lo actualiza el recorder; no editar a mano) ---
        # NO read-only: asi el recorder puede escribirlos con seguridad en
        # cualquier version. El tinte rojo de 'view' depende de 'Recording'.
        rp = pg.appendToggle('Recording', label='GRABANDO')
        stp = pg.appendStr('Status', label='Estado')
        stp[0].val = 'detenido'
    except Exception as e:
        report.append('CUSTOM PARS FAIL: %s' % e)

# ----------------------- Buffer + grabacion -------------------------
tbl      = make(tableDAT,        'tabla_datos', 1200, 250)
recorder = make(textDAT,         'recorder',    1000, 250)
chopexec = make(chopexecuteDAT,  'chopexec',    1400, 250)

# ----------------------- Botones (panel) -----------------------------
# Ambos botones MOMENTARY (tipo por defecto, fiable). El comportamiento
# "toggle" de Record (un click arranca, otro para) se hace por software
# en panelexec, asi NO dependemos del tipo de boton (que varia por version).
recbtn   = make(buttonCOMP,      'Record',         600, 450)
bgbtn    = make(buttonCOMP,      'Fondo',          900, 450)
panelex  = make(panelexecuteDAT, 'panelexec',      750, 450)
panelbg  = make(panelexecuteDAT, 'panelexec_bg',  1050, 450)
setq(recbtn, 'buttontype', 'momentary')
setq(bgbtn,  'buttontype', 'momentary')
setp(recbtn, 'w', 240); setp(recbtn, 'h', 120)
setp(bgbtn,  'w', 160); setp(bgbtn,  'h', 120)

# ----------------------- overlay de marcadores (calibracion) --------
mark1   = make(circleTOP,    'mark1',   400, 250)
mark2   = make(circleTOP,    'mark2',   400, 150)
monitor = make(compositeTOP, 'monitor', 800, 250)
for mk, sx, sy in ((mark1,'Marker1x','Marker1y'), (mark2,'Marker2x','Marker2y')):
    # resolucion = source para que NO se deforme al componer sobre la imagen
    setp(mk, 'outputresolution', 'custom')
    setexpr(mk, 'resolutionw', "op('source').width")
    setexpr(mk, 'resolutionh', "op('source').height")
    # punto redondo: corrige el aspecto -> radiox = radioy * (H/W)
    setp(mk, 'radiusy', 0.02)
    setexpr(mk, 'radiusx', "0.02*op('source').height/op('source').width")
    setexpr(mk, 'centerx', "op('CONTROL').par.%s*2-1" % sx)
    setexpr(mk, 'centery', "1-op('CONTROL').par.%s*2" % sy)   # y de imagen va al reves
    setp(mk, 'fillcolorr', 1); setp(mk, 'fillcolorg', 0); setp(mk, 'fillcolorb', 0)
wire(source, monitor, 0)
wire(mark1,  monitor, 1)
wire(mark2,  monitor, 2)
setp(monitor, 'operand', 'over')
setp(monitor, 'outputresolution', 'custom')
setexpr(monitor, 'resolutionw', "op('source').width")
setexpr(monitor, 'resolutionh', "op('source').height")

# ----------------------- indicador visual de grabacion --------------
# 'view' = imagen + marcadores + TINTE ROJO cuando se esta grabando.
# El tinte aparece solo si CONTROL.Recording == 1 (alpha = 0 si no graba).
rec_led = make(constantTOP, 'rec_led', 800, 100)
setp(rec_led, 'colorr', 1); setp(rec_led, 'colorg', 0); setp(rec_led, 'colorb', 0)
setexpr(rec_led, 'alpha', "op('CONTROL').par.Recording*0.30")
setp(rec_led, 'outputresolution', 'custom')
setexpr(rec_led, 'resolutionw', "op('source').width")
setexpr(rec_led, 'resolutionh', "op('source').height")

view = make(compositeTOP, 'view', 1000, 250)
wire(monitor, view, 0)     # abajo: imagen + marcadores
wire(rec_led, view, 1)     # arriba: tinte rojo (solo si graba)
setp(view, 'operand', 'over')
setp(view, 'outputresolution', 'custom')
setexpr(view, 'resolutionw', "op('source').width")
setexpr(view, 'resolutionh', "op('source').height")

# =====================================================================
#                      CODIGO DE LOS DATs
# =====================================================================

# --- recorder (modulo) ------------------------------------------------
if recorder:
    recorder.text = r'''# recorder - graba la trayectoria a chunks .txt
#
# LA TABLA es el DAT "tabla_datos": fila 0 = encabezado (t_s, x_mm, y_mm),
# y debajo se van agregando las muestras en vivo. Cada "Guardar cada (s)"
# se exportan SOLO las filas de datos a un .txt y la tabla se reinicia
# (se conserva el encabezado). Al parar, se exporta lo que haya quedado.
#
# TIEMPO: se usa el reloj real (absTime.seconds), NO el numero de frame,
# asi el tiempo es verdadero aunque TD dropee frames -> robusto.
import os

DATOS  = r"C:\Users\lenny\OneDrive\Documents\FISICA\LABO 4\labo-4-2026\CAVENDISH\Datos"
HEADER = ['t_s', 'x_mm', 'y_mm']

def _ctrl(): return op('CONTROL')
def _tbl():  return op('tabla_datos')

def _setpar(name, val):
    # actualiza un parametro de estado (aunque sea read-only, desde script anda)
    try: getattr(_ctrl().par, name).val = val
    except Exception: pass

def _state():
    s = _ctrl().fetch('rec', None)
    if s is None:
        s = {'on': False, 'chunk': 0, 'folder': '', 'nn': 0, 't0': 0.0}
        _ctrl().store('rec', s)
    return s

def isRecording():
    return _state()['on']

def capture_bg():
    # guarda el frame actual de 'lum' como fondo y recarga el TOP 'bg'
    bgpath = op('bg').par.file.eval() or (project.folder + '/bg.png')
    op('lum').save(bgpath)
    op('bg').par.file = bgpath
    try:    op('bg').par.reloadpulse.pulse()
    except: pass
    print('fondo capturado ->', bgpath)

def _reset_table():
    t = _tbl()
    t.clear()
    t.appendRow(HEADER)          # encabezado visible en TD

def _next_medicion(base):
    nn = 0
    while True:
        p = os.path.join(base, 'medicion%02d' % nn)
        if not os.path.exists(p):
            return nn, p
        nn += 1

def _write_meta(s, mmpx):
    import datetime
    src = op('source')
    path = os.path.join(s['folder'], 'medicion%02d_meta.txt' % s['nn'])
    try:
        with open(path, 'w') as f:
            f.write('# metadatos de la medicion\n')
            f.write('fecha\t%s\n' % datetime.datetime.now().isoformat(timespec='seconds'))
            f.write('mm_por_px\t%.10g\n' % mmpx)
            f.write('width_px\t%d\n'  % (src.width or 0))
            f.write('height_px\t%d\n' % (src.height or 0))
            f.write('umbral\t%.6g\n'  % float(_ctrl().par.Threshold))
            f.write('guardar_cada_s\t%.6g\n' % float(_ctrl().par.Saveperiod))
            f.write('columnas\t%s\n' % '\t'.join(HEADER))
    except Exception as e:
        print('meta no escrito:', e)

def start():
    s = _state()
    if s['on']:
        return
    if not os.path.isdir(DATOS):
        os.makedirs(DATOS)
    nn, folder = _next_medicion(DATOS)
    os.makedirs(folder)
    try:    mmpx = float(_ctrl().par.Mmperpx)
    except: mmpx = 0.0
    s.update({'on': True, 'chunk': 0, 'nn': nn, 'folder': folder,
              't0': absTime.seconds})
    _ctrl().store('rec', s)
    _reset_table()
    _write_meta(s, mmpx)
    op('/').time.frame = 1          # timeline a 0 (visual)
    _setpar('Recording', 1)
    _setpar('Status', 'GRABANDO  ' + os.path.basename(folder))
    print('REC start ->', folder)

def tick():
    s = _state()
    if not s['on']:
        return
    m = op('measure')
    try:
        x = m['x_mm'][0]; y = m['y_mm'][0]
    except Exception:
        return
    t = absTime.seconds - s['t0']   # tiempo REAL desde que arranco la grabacion
    _tbl().appendRow(['%.6f' % t, '%.6f' % x, '%.6f' % y])
    _setpar('Status', 'GRABANDO  %.1f s  |  chunk %d  |  %s'
            % (t, s['chunk'], os.path.basename(s['folder'])))
    period = float(_ctrl().par.Saveperiod)
    if period > 0 and t >= (s['chunk'] + 1) * period:
        _save_chunk(s)
        s['chunk'] += 1
        _ctrl().store('rec', s)

def _save_chunk(s):
    t = _tbl()
    rows = t.rows()[1:]             # saltea el encabezado
    if not rows:
        return
    path = os.path.join(s['folder'], 'medicion%02d_%04d.txt' % (s['nn'], s['chunk']))
    with open(path, 'w') as f:      # escritura manual: sin header, tab-separated
        for r in rows:
            f.write('\t'.join(c.val for c in r) + '\n')
    _reset_table()                  # reinicia datos, conserva encabezado
    print('guardado', path, '(%d filas)' % len(rows))

def stop():
    s = _state()
    if not s['on']:
        return
    _save_chunk(s)                  # flush del ultimo chunk parcial
    s['on'] = False
    _ctrl().store('rec', s)
    _setpar('Recording', 0)
    _setpar('Status', 'detenido')
    print('REC stop')
'''

# --- measure (Script CHOP callbacks) ---------------------------------
mcb = make(textDAT, 'measure_callbacks', 1200, 150)
if mcb:
    mcb.text = r'''# measure - centroide ponderado por intensidad, EXACTO, con numpy.
# Lee el TOP 'clean' (imagen ya con fondo restado + umbral) y calcula el centro
# de masa sobre TODOS los pixeles. Salida (canales):
#   x_mm, y_mm      posicion en mm (lo que se graba)
#   x_px, y_px      posicion en pixeles (diagnostico)
#   intensity       suma total de intensidad (diagnostico / control de senal)
#   valid           1 si habia senal sobre el umbral, 0 si no
import numpy as np

def onCook(scriptOp):
    scriptOp.clear()
    scriptOp.numSamples = 1
    ctrl = op('CONTROL')
    try:    mmpx = float(ctrl.par.Mmperpx)
    except: mmpx = 0.0

    a = op('clean').numpyArray(delayed=False)     # (H, W, canales), origen abajo-izq
    if a is None:
        return
    I = a[:, :, 0].astype('float64')              # intensidad (canal R)
    H, W = I.shape

    col = I.sum(axis=0)                           # perfil horizontal (largo W)
    row = I.sum(axis=1)                           # perfil vertical   (largo H)
    total = float(I.sum())

    valid = 1.0 if total > 1e-9 else 0.0
    if valid:
        xidx = float((col * np.arange(W)).sum() / total)            # 0..W-1
        yidx = float((row * np.arange(H)).sum() / total)            # 0..H-1 (abajo->arriba)
        x_px = xidx
        y_px = (H - 1) - yidx                     # paso a origen arriba-izq (como la imagen)
        scriptOp.store('lx', x_px); scriptOp.store('ly', y_px)
    else:
        x_px = scriptOp.fetch('lx', (W - 1) / 2.0)
        y_px = scriptOp.fetch('ly', (H - 1) / 2.0)

    scriptOp.appendChan('x_mm')[0]      = x_px * mmpx
    scriptOp.appendChan('y_mm')[0]      = y_px * mmpx
    scriptOp.appendChan('x_px')[0]      = x_px
    scriptOp.appendChan('y_px')[0]      = y_px
    scriptOp.appendChan('intensity')[0] = total
    scriptOp.appendChan('valid')[0]     = valid
    scriptOp.appendChan('clock')[0]     = absTime.frame   # cambia cada frame -> dispara chopexec
    return
'''
    setp(measure, 'callbacks', 'measure_callbacks')

# --- chopexec (CHOP Execute DAT) -> registra una muestra cada frame --
# Vigila 'measure' (que cocina cada frame por el canal 'clock'=frame) y
# llama recorder.tick() UNA vez por frame (dedupe por numero de frame),
# sin importar que callback dispare. Reemplaza al Execute DAT onFrameEnd.
if chopexec:
    chopexec.text = r'''def _tick_once():
    cur = absTime.frame
    if me.fetch('lf', -1) != cur:
        me.store('lf', cur)
        op('recorder').module.tick()

def onValueChange(channel, sampleIndex, val, prev):
    _tick_once()
    return

def whileOn(channel, sampleIndex, val, prev):
    _tick_once()
    return
'''
    setp(chopexec, 'chop', 'measure')
    setq(chopexec, 'active', True)
    setq(chopexec, 'channels', 'clock')      # vigila solo el reloj (si el nombre varia, igual anda)
    for tgl in ('valuechange', 'whileon'):
        setq(chopexec, tgl, True)

# --- panelexec (Panel Execute DAT en el boton Record) ----------------
if panelex:
    panelex.text = r'''# cada click en Record alterna grabar/parar (toggle por software)
def onOffToOn(panelValue):
    rec = op('recorder').module
    if rec.isRecording():
        rec.stop()
    else:
        rec.start()
    return
'''
    setp(panelex, 'panel', 'Record')
    setp(panelex, 'offtoon', True)

# --- panelexec_bg (Panel Execute DAT en el boton Fondo) --------------
if panelbg:
    panelbg.text = r'''# captura el fondo al apretar el boton Fondo
def onOffToOn(panelValue):
    op('recorder').module.capture_bg()
    return
'''
    setp(panelbg, 'panel', 'Fondo')
    setp(panelbg, 'offtoon', True)

# --- LEEME (instrucciones dentro de la red) --------------------------
readme = make(textDAT, 'LEEME', 0, 450)
if readme:
    readme.text = r'''================================================================
  MEDIDOR DE POSICION DE LASER  -  COMO USAR
================================================================

FUENTE
  Todo lee del Null "source". La camara "cam" entra ahi.
  Para usar un video pregrabado: crea un Movie File In, elegi el
  archivo, y conecta su salida a la entrada de "source" (en lugar
  de "cam"). Todo lo demas (resolucion, calibracion, centroide)
  se adapta solo a las dimensiones del source.

PASO A PASO
  1) En "cam" elegi tu webcam (parametro Device), o enchufa un
     video al "source" como se explico arriba.
  2) Capturar fondo: SIN laser, apreta el boton "Fondo".
     Guarda el frame actual como fondo y lo resta (saca luz ambiente
     fija). Repetilo si cambia la iluminacion.
  3) Calibrar (pasar de pixeles a mm). Objetivo: decirle cuantos mm
     mide cada pixel.
     a. Pone en la pantalla (donde cae el laser) DOS marcas reales a
        una distancia que conozcas. Ej: pega una regla y usa la marca
        de 0 mm y la de 100 mm  ->  distancia = 100 mm.
     b. Selecciona el TOP "view": veras la imagen con DOS PUNTOS
        rojos (marcador 1 y 2). (view es la vista principal a mirar.)
     c. En "CONTROL", move los sliders Marker1x / Marker1y para poner
        el punto 1 sobre la primer marca, y Marker2x / Marker2y para
        el punto 2 sobre la segunda. Los sliders van de 0 a 1:
        x: 0=izquierda, 1=derecha ;  y: 0=arriba, 1=abajo.
     d. Escribi en "Dist. conocida (mm)" la distancia real (ej 100).
     e. Listo: "mm/px (auto)" se calcula solo y ya mide en mm.
        Cuanto mejor alinees los puntos, mas precisa la medicion.
  4) Umbral: en CONTROL subi "Umbral (0-1)" hasta que el TOP
     "clean" muestre SOLO el haz (fondo totalmente negro). El
     centroide ignora todo lo que este por debajo del umbral, asi
     que esto evita que el fondo sesgue la medicion.
     Control de senal: en "measure", el canal "intensity" debe ser
     claramente > 0 y "valid" = 1 cuando el laser esta presente.
  5) GRABAR: el boton "Record" funciona como toggle:
       1 click = ARRANCA  /  otro click = PARA.
     COMO SABES QUE ESTA GRABANDO (3 senales claras):
       - la vista "view" se TINE DE ROJO
       - en CONTROL, el checkbox "GRABANDO" se prende y "Estado"
         muestra el tiempo y el chunk (ej: GRABANDO 12.3 s | chunk 2)
       - "tabla_datos" crece fila por fila
     Al arrancar:
       - timeline a 0
       - crea Datos\medicionNN  (+ medicionNN_meta.txt con calibracion)
       - cada "Guardar cada (s)" (def 60) exporta medicionNN_nnnn.txt
         y reinicia la tabla (conserva el encabezado)
     Al parar exporta el chunk parcial (no se pierde nada).

  PRUEBA RAPIDA: pone "Guardar cada (s)" = 5 para ver aparecer varios
  archivos en pocos segundos y confirmar que graba bien.

LA TABLA
  El DAT "tabla_datos" es la tabla que se va llenando:
    fila 0 = encabezado (t_s, x_mm, y_mm)
    debajo = una fila por muestra, en vivo
  Al exportar un chunk se guardan SOLO las filas de datos (sin
  encabezado) y la tabla se vacia (queda el encabezado).

TIEMPO
  La columna t_s es tiempo de RELOJ REAL (segundos desde que
  apretaste Record), no el numero de frame. Asi es correcto aunque
  TD no llegue exacto a 15 FPS.

SALIDA
  Datos\medicionNN\medicionNN_nnnn.txt   (tab-separated, SIN header)
    columnas:  t_s <TAB> x_mm <TAB> y_mm
  Datos\medicionNN\medicionNN_meta.txt   (calibracion y parametros)
  Concatenas los nnnn en orden para la curva completa.

NODOS CLAVE
  source ........ fuente (swap aca para usar video)
  view .......... VISTA PRINCIPAL: imagen + marcadores + tinte ROJO al grabar
  monitor ....... imagen + puntos de calibracion (interno; mira "view")
  clean ......... imagen umbralizada (de aca se calcula el centroide)
  measure ....... centroide en vivo: x_mm, y_mm, x_px, y_px,
                  intensity (senal total), valid (1/0)
  tabla_datos ... LA TABLA que se graba y exporta
  chopexec ...... dispara el registro de una muestra por frame
  CONTROL ....... todos los parametros (incl. checkbox GRABANDO + Estado)
  Record ........ boton grande: 1 click arranca, otro para (toggle)
  Fondo ......... boton: captura el fondo (restar luz ambiente)

Detalle completo en GUIA.md (carpeta del proyecto).
================================================================
'''

# --- viewers activos en los nodos clave (para verlos sin click) ------
for nm in ('view', 'clean', 'measure', 'tabla_datos'):
    o = D.op(nm)
    if o:
        try: o.viewer = True
        except Exception as e: report.append('VIEWER FAIL %s: %s' % (nm, e))

# ----------------------- tabla y proyecto ----------------------------
# encabezado inicial de la tabla (para que se vea que columnas tiene)
if tbl:
    try:
        tbl.clear()
        tbl.appendRow(['t_s', 'x_mm', 'y_mm'])
    except Exception as e: report.append('TBL INIT FAIL: %s' % e)

# proyecto a 15 FPS
try:
    op('/').time.rate = 15
except Exception as e:
    report.append('RATE FAIL: %s' % e)

# ----------------------- reporte final -------------------------------
print('=' * 60)
print('BUILD TERMINADO. Nodos creados:', ', '.join(sorted(created.keys())))
if report:
    print('--- AVISOS (revisar a mano) ---')
    for r in report:
        print(' -', r)
else:
    print('Sin avisos: todo OK.')
print('=' * 60)
print('Lee el nodo "LEEME" para las instrucciones de uso.')
print('PASOS: 1) en "cam" elegi tu webcam (o enchufa un video al "source").')
print('       2) apreta "Fondo".  3) calibra (markers + dist conocida).')
print('       4) ajusta Umbral.   5) apreta Record.')
