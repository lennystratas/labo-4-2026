"""
OPTICAL GRID — constructor de red para TouchDesigner (solo nodos nativos, sin GLSL)
Pegar en un Text DAT y click derecho > Run Script.

Optical flow: componente opticalFlow de la Palette.
  - Arrastralo desde la Palette a /project1 (fuera de opticalGrid), dejale el nombre
    'opticalFlow' (o cualquier nombre que empiece con 'opticalFlow').
  - El script lo detecta, le conecta el video (salida de opticalGrid) y lee su salida.
  - Si todavía no está, la red usa el flow nativo; cuando lo agregues, volvé a correr el script
    (o conectalo a mano y apuntá el Select TOP 'flow_in' a su salida).
Crea /project1/opticalGrid (lo reemplaza si existe) y ~1 s después imprime
un reporte de verificación en el Textport.
"""

import td

ROOT_PATH = '/project1'
NAME = 'opticalGrid'
PALETTE_PREFIX = 'opticalFlow'
P = 'parent.OG.par.'          # prefijo para expresiones (parentshortcut del Base COMP)
N = P + 'Cols'
M = P + 'Rows'
LOG = []


# ----------------------------------------------------------------------------- helpers
def _par(o, names):
    for n in ([names] if isinstance(names, str) else names):
        p = getattr(o.par, n, None)
        if p is not None:
            return p
    return None


def setp(o, names, value=None, expr=None):
    """Setea el primer parámetro que exista entre `names` (valor o expresión)."""
    p = _par(o, names)
    if p is None:
        LOG.append('{}: no existe ninguno de {}'.format(o.path, names))
        return None
    try:
        if expr is not None:
            p.expr = expr
        else:
            p.val = value
    except Exception as e:
        LOG.append('{}.{}: {}'.format(o.path, p.name, e))
    return p


def setmenu(o, names, *keywords):
    """Setea un menú eligiendo la primera opción cuyo nombre/label contenga una keyword."""
    p = _par(o, names)
    if p is None or not p.isMenu:
        LOG.append('{}: menú {} no encontrado'.format(o.path, names))
        return None
    opts = [(str(a), str(b)) for a, b in zip(p.menuNames or [], p.menuLabels or [])]
    choice = None
    for kw in keywords:
        for name, label in opts:
            if kw.lower() == name.lower():
                choice = name
                break
        if choice:
            break
    if choice is None:
        for kw in keywords:
            for name, label in opts:
                if kw.lower() in name.lower() or kw.lower() in label.lower():
                    choice = name
                    break
            if choice:
                break
    if choice is None:
        LOG.append('{}.{}: ninguna opción {} en {}'.format(o.path, p.name, keywords, p.menuNames))
        return p
    try:
        p.val = choice
    except Exception as e:
        LOG.append('{}.{}: {}'.format(o.path, p.name, e))
    return p


def mk(parent_op, typ, name, x, y, inputs=()):
    cls = getattr(td, typ, None)
    if cls is None:
        raise RuntimeError('Tipo de operador no disponible: ' + typ)
    o = parent_op.create(cls, name)
    o.nodeX, o.nodeY = x * 180, -y * 140
    for i, src in enumerate(inputs):
        o.inputConnectors[i].connect(src)
    return o


def res(o, w, h, fmt='rgba32float', filt=None):
    """Resolución custom (w/h: expresiones string) + formato de pixel."""
    setmenu(o, 'outputresolution', 'custom')
    setp(o, 'resolutionw', expr=str(w))
    setp(o, 'resolutionh', expr=str(h))
    f32(o, fmt)
    if filt:
        setmenu(o, 'inputfiltertype', filt)


def f32(o, fmt='rgba32float'):
    setmenu(o, 'format', fmt, '32-bit float (rgba)', '32')


def chmix(parent_op, name, x, y, src, **w):
    """Channel Mix TOP con matriz en cero salvo los pesos dados (valor o expresión str)."""
    o = mk(parent_op, 'channelmixTOP', name, x, y, [src])
    for ch in ('red', 'green', 'blue', 'alpha'):
        for k in range(1, 5):
            setp(o, ch + str(k), 0)
    for k, v in w.items():
        if isinstance(v, str):
            setp(o, k, expr=v)
        else:
            setp(o, k, v)
    f32(o)
    return o


def ema(parent_op, name, x, y, src, amount_expr):
    """Media móvil exponencial: out = mix(prev, src, amount). Feedback TOP + Cross TOP."""
    fb = mk(parent_op, 'feedbackTOP', name + '_fb', x, y, [src])
    cr = mk(parent_op, 'crossTOP', name, x + 1, y, [fb, src])
    setp(fb, 'top', cr.path)
    setp(cr, 'cross', expr=amount_expr)
    f32(fb)
    f32(cr)
    return cr


def shift(parent_op, name, x, y, src, tx='0', ty='0'):
    """Corre la textura (tx, ty en fracción de la imagen), rellenando con cero."""
    o = mk(parent_op, 'transformTOP', name, x, y, [src])
    setp(o, 'tx', expr=tx)
    setp(o, 'ty', expr=ty)
    setmenu(o, 'extend', 'zero')
    setmenu(o, 'inputfiltertype', 'nearest')
    f32(o)
    return o


def clamp_top(parent_op, name, x, y, src, lim_expr):
    o = mk(parent_op, 'limitTOP', name, x, y, [src])
    for p in o.pars():
        if not p.isMenu or p.page.name == 'Common':
            continue
        names = [n for n in (p.menuNames or []) if 'clamp' in str(n).lower()]
        if names:
            try:
                p.val = names[0]
            except Exception as e:
                LOG.append('{}.{}: {}'.format(o.path, p.name, e))
    setp(o, ['min', 'minimum', 'minval'], expr='-' + lim_expr)
    setp(o, ['max', 'maximum', 'maxval'], expr=lim_expr)
    f32(o)
    return o


def add(parent_op, name, x, y, *srcs):
    o = mk(parent_op, 'compositeTOP', name, x, y, list(srcs))
    setmenu(o, 'operand', 'add')
    f32(o)
    return o


def mul(parent_op, name, x, y, a, b):
    o = mk(parent_op, 'compositeTOP', name, x, y, [a, b])
    setmenu(o, 'operand', 'multiply')
    f32(o)
    return o


def prefix_count(parent_op, tag, x, y, ones, axis, count_expr):
    """Textura con el índice entero de cada pixel (0,1,2,...) a lo largo de `axis`.
    Suma prefija por duplicación: se parte de 'unos corridos 1 px' y se suman copias
    corridas 1, 2, 4, ... px (con extend = zero). Todo con Transform + Composite."""
    key = 'tx' if axis == 'x' else 'ty'
    acc = shift(parent_op, 'idx_{}_s0'.format(tag), x, y, ones, **{key: '1/' + count_expr})
    for k in range(6):                     # 2^6 = 64 > máximo de 48 celdas
        sh = shift(parent_op, 'idx_{}_sh{}'.format(tag, k), x + 1 + k, y + 1, acc,
                   **{key: '{}/{}'.format(2 ** k, count_expr)})
        acc = add(parent_op, 'idx_{}_sum{}'.format(tag, k), x + 1 + k, y, acc, sh)
    return acc


# ----------------------------------------------------------------------------- build
def build():
    root = op(ROOT_PATH)
    old = root.op(NAME)
    if old:
        old.destroy()
    og = root.create(td.baseCOMP, NAME)
    og.par.parentshortcut = 'OG'
    og.nodeX, og.nodeY = 0, 0

    palette = None
    for c in root.children:
        if c.name.startswith(PALETTE_PREFIX) and c.isCOMP:
            palette = c
            break

    # --- parámetros custom
    pg = og.appendCustomPage('Optical Grid')

    def cpar(kind, name, label, val, lo=None, hi=None):
        p = getattr(pg, 'append' + kind)(name, label=label)[0]
        if kind in ('Int', 'Float'):
            if lo is not None:
                p.normMin = p.min = lo
                p.clampMin = kind == 'Int'
            if hi is not None:
                p.normMax = hi
        p.default = val
        p.val = val
        return p

    cpar('Int', 'Cols', 'Columnas', 12, 2, 48)
    cpar('Int', 'Rows', 'Filas', 8, 2, 48)
    cpar('Int', 'Resw', 'Resolución W', 1280, 64, 3840)
    cpar('Int', 'Resh', 'Resolución H', 720, 64, 2160)
    src_p = pg.appendMenu('Source', label='Fuente')[0]
    src_p.menuNames = ['camera', 'movie']
    src_p.menuLabels = ['Cámara (Video Device In)', 'Archivo (Movie File In)']
    pg.appendFile('Moviefile', label='Archivo de video')
    fm = pg.appendMenu('Flowmode', label='Optical flow')[0]
    fm.menuNames = ['palette', 'native']
    fm.menuLabels = ['Palette opticalFlow', 'Nativo (gradiente x diferencia)']
    fm.val = 'palette' if palette else 'native'
    cpar('Float', 'Flowoffset', 'Offset flow palette (0 ó 0.5)', 0.0, 0, 1)
    cpar('Float', 'Flowgain', 'Ganancia flow palette', 1.0, 0, 50)
    cpar('Float', 'Nativegain', 'Ganancia flow nativo', 20.0, 0, 200)
    cpar('Float', 'Push', 'Push (dirección del flow)', 1.5, -10, 10)
    cpar('Float', 'Grow', 'Grow (energía -> tamaño)', 4.0, -20, 20)
    cpar('Float', 'Limit', 'Límite desplazamiento (celdas)', 0.45, 0, 0.49)
    cpar('Float', 'Smoothstats', 'Suavizado flow', 0.6, 0, 0.99)
    cpar('Float', 'Smoothgrid', 'Suavizado grilla', 0.85, 0, 0.99)
    cpar('Float', 'Lines', 'Opacidad líneas', 1.0, 0, 1)

    W, H = P + 'Resw', P + 'Resh'

    # ================================================================ 1. FUENTE
    cam = mk(og, 'videodeviceinTOP', 'cam_in', 0, 0)
    mov = mk(og, 'moviefileinTOP', 'movie_in', 0, 1)
    setp(mov, 'file', expr=P + 'Moviefile.eval() or me.par.file.default')
    srcsw = mk(og, 'switchTOP', 'src_switch', 1, 0, [cam, mov])
    setp(srcsw, 'index', expr=P + 'Source.menuIndex')
    video = mk(og, 'resolutionTOP', 'video', 2, 0, [srcsw])
    res(video, W, H, fmt='rgba8fixed')
    video_out = mk(og, 'outTOP', 'video_out', 3, -2, [video])   # salida 0 de opticalGrid -> palette

    # ================================================================ 2. OPTICAL FLOW
    # 2a. Palette opticalFlow: R = movimiento izq->der, G = abajo->arriba.
    #     Si en reposo da ~0.5 en vez de ~0 (salida codificada), poné Flowoffset = 0.5.
    flow_in = mk(og, 'selectTOP', 'flow_in', 3, -1)
    f32(flow_in)
    if palette is not None:
        try:
            palette.inputConnectors[0].connect(og.outputConnectors[0])
        except Exception as e:
            LOG.append('no pude conectar video -> {}: {}'.format(palette.path, e))
        outs = [c for c in palette.children if c.OPType == 'outTOP']
        target = outs[0] if outs else palette
        setp(flow_in, 'top', target.path)
        palette.nodeX, palette.nodeY = 250, 0
    else:
        LOG.append('No encontré /project1/{}*: usando flow nativo. Agregá el componente de '
                   'la Palette y volvé a correr el script.'.format(PALETTE_PREFIX))
    off = mk(og, 'constantTOP', 'flow_offset', 4, -2)
    res(off, '8', '8')
    setp(off, 'colorr', expr='-' + P + 'Flowoffset')
    setp(off, 'colorg', expr='-' + P + 'Flowoffset')
    setp(off, 'colorb', 0)
    setp(off, 'alpha', 0)
    pal_c = add(og, 'flow_palette_centered', 5, -1, flow_in, off)
    pal_flow = chmix(og, 'flow_palette', 6, -1, pal_c,
                     red1=P + 'Flowgain', green2=P + 'Flowgain')

    # 2b. Fallback nativo: flow "normal" ~ -dI/dt * grad(I)
    gray = mk(og, 'monochromeTOP', 'gray', 3, 1, [video])
    res(gray, W + '//4', H + '//4')
    gblur = mk(og, 'blurTOP', 'gray_blur', 4, 1, [gray])
    setp(gblur, 'size', 3)
    f32(gblur)
    prev = mk(og, 'feedbackTOP', 'gray_prev', 5, 2, [gblur])
    setp(prev, 'top', gblur.path)
    f32(prev)
    negprev = chmix(og, 'gray_prev_neg', 6, 2, prev, red1=-1)
    dIdt = add(og, 'dIdt', 7, 1, gblur, negprev)
    grad = mk(og, 'slopeTOP', 'grad', 5, 0, [gblur])
    f32(grad)
    it_rg = chmix(og, 'dIdt_rg', 8, 1, dIdt, red1=1, green1=1)
    num = mul(og, 'grad_x_dIdt', 9, 0, grad, it_rg)
    nflow = chmix(og, 'flow_native_raw', 10, 0, num,
                  red1='-' + P + 'Nativegain', green2='-' + P + 'Nativegain')
    nflow_b = mk(og, 'blurTOP', 'flow_native', 11, 0, [nflow])
    setp(nflow_b, 'size', 6)
    f32(nflow_b)

    flowsw = mk(og, 'switchTOP', 'flow_switch', 12, -1, [pal_flow, nflow_b])
    setp(flowsw, 'index', expr=P + 'Flowmode.menuIndex')
    f32(flowsw)

    # ================================================================ 3. ESTADÍSTICAS POR CELDA
    # stats = (flow.x, flow.y, |flow|^2) promediado dentro de cada celda -> textura Cols x Rows
    fl = chmix(og, 'flow_rg', 13, -1, flowsw, red1=1, green2=1)
    sq = mul(og, 'flow_sq', 14, 0, fl, fl)
    energy = chmix(og, 'energy', 15, 0, sq, blue1=1, blue2=1)
    stats_full = add(og, 'stats_full', 16, -1, fl, energy)
    stats_cells = mk(og, 'resolutionTOP', 'stats_cells', 17, -1, [stats_full])
    res(stats_cells, N, M, filt='mipmap')
    S = ema(og, 'stats_ema', 18, -1, stats_cells, '1-' + P + 'Smoothstats')

    # ================================================================ 4. FRONTERAS DE COLUMNA (por fila)
    # Dh = clamp( Push*(fx_i + fx_i+1)/2 + Grow*(E_i - E_i+1), ±Limit ), última columna = 0
    Sn = shift(og, 'stats_next_x', 20, -3, S, tx='-1/' + N)
    hA = chmix(og, 'h_a', 21, -4, S, red1='0.5*' + P + 'Push', red3=P + 'Grow')
    hB = chmix(og, 'h_b', 21, -3, Sn, red1='0.5*' + P + 'Push', red3='-' + P + 'Grow')
    hraw = add(og, 'h_raw', 22, -3, hA, hB)
    hlim = clamp_top(og, 'h_clamp', 23, -3, hraw, P + 'Limit')
    white = mk(og, 'constantTOP', 'white', 20, -5)
    res(white, N, M)
    setp(white, 'colorr', 1); setp(white, 'colorg', 1); setp(white, 'colorb', 1)
    setp(white, 'alpha', 1)
    maskx = shift(og, 'mask_x', 21, -5, white, tx='-1/' + N)
    hmask = mul(og, 'h_masked', 24, -3, hlim, maskx)
    Dh = ema(og, 'Dh', 25, -3, hmask, '1-' + P + 'Smoothgrid')
    Dhl = shift(og, 'Dh_left', 27, -3, Dh, tx='1/' + N)

    # ================================================================ 5. FRONTERAS DE FILA (globales)
    R = mk(og, 'resolutionTOP', 'stats_rows', 20, 1, [S])
    res(R, '1', M, filt='mipmap')
    Rn = shift(og, 'stats_next_y', 21, 2, R, ty='-1/' + M)
    vA = chmix(og, 'v_a', 22, 1, R, red2='0.5*' + P + 'Push', red3=P + 'Grow')
    vB = chmix(og, 'v_b', 22, 2, Rn, red2='0.5*' + P + 'Push', red3='-' + P + 'Grow')
    vraw = add(og, 'v_raw', 23, 1, vA, vB)
    vlim = clamp_top(og, 'v_clamp', 24, 1, vraw, P + 'Limit')
    white_y = mk(og, 'constantTOP', 'white_y', 21, 3)
    res(white_y, '1', M)
    setp(white_y, 'colorr', 1); setp(white_y, 'colorg', 1); setp(white_y, 'colorb', 1)
    setp(white_y, 'alpha', 1)
    masky = shift(og, 'mask_y', 22, 3, white_y, ty='-1/' + M)
    vmask = mul(og, 'v_masked', 25, 1, vlim, masky)
    Dv = ema(og, 'Dv', 26, 1, vmask, '1-' + P + 'Smoothgrid')
    Dvl = shift(og, 'Dv_below', 28, 2, Dv, ty='1/' + M)
    Dv_b = mk(og, 'resolutionTOP', 'Dv_cells', 29, 1, [Dv])
    res(Dv_b, N, M, filt='nearest')
    Dvl_b = mk(og, 'resolutionTOP', 'Dv_below_cells', 29, 2, [Dvl])
    res(Dvl_b, N, M, filt='nearest')

    # ================================================================ 6. ÍNDICES DE CELDA (i/N, j/M)
    cnt_x = prefix_count(og, 'x', 30, -8, white, 'x', N)
    cnt_y = prefix_count(og, 'y', 30, -6, white, 'y', M)
    ixr = chmix(og, 'idx_x_r', 38, -8, cnt_x, red1='1/' + N)
    iyg = chmix(og, 'idx_y_g', 38, -6, cnt_y, green1='1/' + M)
    src_origin = add(og, 'src_origin', 39, -7, ixr, iyg)

    # ================================================================ 7. LAYOUT (x0, y0, w, h)
    #   x0 = (i + Dhl)/N   w = (1 + Dh - Dhl)/N   y0 = (j + Dvl)/M   h = (1 + Dv - Dvl)/M
    base = chmix(og, 'layout_base', 36, -4, white, blue1='1/' + N, alpha1='1/' + M)
    L1 = chmix(og, 'layout_dh', 36, -3, Dh, blue1='1/' + N)
    L2 = chmix(og, 'layout_dhl', 36, -2, Dhl, red1='1/' + N, blue1='-1/' + N)
    L3 = chmix(og, 'layout_dv', 36, 1, Dv_b, alpha1='1/' + M)
    L4 = chmix(og, 'layout_dvl', 36, 2, Dvl_b, green1='1/' + M, alpha1='-1/' + M)
    layout = add(og, 'layout', 38, -2, ixr, iyg, base, L1, L2, L3, L4)

    # ================================================================ 8. RENDER DEL MAPA UV (instancing)
    rh = mk(og, 'rampTOP', 'ramp_h', 38, 4)
    rv = mk(og, 'rampTOP', 'ramp_v', 38, 5)
    for r_, kw in ((rh, 'horizontal'), (rv, 'vertical')):
        res(r_, '1024', '1024')
        setmenu(r_, 'type', kw)
    uvgrad = add(og, 'uv_gradient', 40, 4,
                 chmix(og, 'ramp_h_r', 39, 4, rh, red1=1, alpha4=1),
                 chmix(og, 'ramp_v_g', 39, 5, rv, green2=1))

    camc = mk(og, 'cameraCOMP', 'cam', 40, 6)
    setmenu(camc, 'projection', 'ortho')
    setp(camc, 'orthowidth', 1)
    setp(camc, 'tx', 0.5)
    setp(camc, 'ty', expr='0.5*{}/{}'.format(H, W))
    setp(camc, 'tz', 5)

    def cell_geo(name, x, y, mat, color_op=None):
        g = mk(og, 'geometryCOMP', name, x, y)
        for c in list(g.children):
            c.destroy()
        grid = g.create(td.gridSOP, 'quad')
        setp(grid, 'rows', 2); setp(grid, 'cols', 2)
        setp(grid, 'sizex', 1); setp(grid, 'sizey', 1)
        setmenu(grid, 'orient', 'xy')
        tex = g.create(td.textureSOP, 'uv')
        tex.inputConnectors[0].connect(grid)
        xf = g.create(td.transformSOP, 'to_corner')
        xf.inputConnectors[0].connect(tex)
        setp(xf, 'tx', 0.5); setp(xf, 'ty', 0.5)
        tex.nodeX, xf.nodeX = 200, 400
        xf.render = True
        xf.display = True
        setp(g, 'sy', expr='{}/{}'.format(H, W))
        setp(g, 'material', mat.path)
        setp(g, 'instancing', True)
        setp(g, 'instanceop', layout.path)
        setp(g, 'instancetx', 'r'); setp(g, 'instancety', 'g')
        setp(g, 'instancesx', 'b'); setp(g, 'instancesy', 'a')
        for unused in ('instancetz', 'instancesz', 'instancerx', 'instancery', 'instancerz'):
            if _par(g, unused) is not None:
                setp(g, unused, '')
        if color_op is not None:
            setp(g, ['instancecolorop', 'instancecop'], color_op.path)
            setp(g, 'instancer', 'r'); setp(g, 'instanceg', 'g'); setp(g, 'instanceb', 'b')
            setmenu(g, 'instancecolormode', 'replace')
        return g

    matA = mk(og, 'constantMAT', 'mat_uv_local', 41, 4)
    setp(matA, 'colorr', expr='1/' + N)
    setp(matA, 'colorg', expr='1/' + M)
    setp(matA, 'colorb', 0)
    setp(matA, 'colormap', uvgrad.path)
    matB = mk(og, 'constantMAT', 'mat_origin', 41, 6)
    matL = mk(og, 'wireframeMAT', 'mat_lines', 41, 8)
    setp(matL, ['colorr', 'wirecolorr'], 1); setp(matL, ['colorg', 'wirecolorg'], 1)
    setp(matL, ['colorb', 'wirecolorb'], 1)

    geoA = cell_geo('geo_uv_local', 42, 4, matA)
    geoB = cell_geo('geo_origin', 42, 6, matB, color_op=src_origin)
    geoL = cell_geo('geo_lines', 42, 8, matL)

    def render(name, x, y, geo, fmt, aa):
        r_ = mk(og, 'renderTOP', name, x, y)
        res(r_, W, H, fmt=fmt)
        setp(r_, 'camera', camc.path)
        setp(r_, 'geometry', geo.path)
        setp(r_, 'lights', '')
        setmenu(r_, 'antialias', *aa)
        return r_

    rA = render('render_uv_local', 43, 4, geoA, 'rgba32float', ('aa1', '1x', '1'))
    rB = render('render_origin', 43, 6, geoB, 'rgba32float', ('aa1', '1x', '1'))
    rL = render('render_lines', 43, 8, geoL, 'rgba8fixed', ('aa4', '4x', '4'))
    uvmap = add(og, 'uv_map', 44, 5, rA, rB)

    # ================================================================ 9. SALIDA
    remap = mk(og, 'remapTOP', 'remapped', 45, 3, [video, uvmap])
    lines = mk(og, 'levelTOP', 'lines_level', 44, 8, [rL])
    setp(lines, 'opacity', expr=P + 'Lines')
    comp = mk(og, 'compositeTOP', 'with_lines', 46, 4, [remap, lines])
    setmenu(comp, 'operand', 'add')
    out = mk(og, 'nullTOP', 'OUT', 47, 4, [comp])
    out.viewer = True
    return og


# ----------------------------------------------------------------------------- verificación
def verify():
    import numpy as np
    og = op(ROOT_PATH + '/' + NAME)
    n, m = int(og.par.Cols), int(og.par.Rows)
    rep, ok = [], True

    def a(name):
        return og.op(name).numpyArray(delayed=False)

    def check(cond, msg):
        nonlocal ok
        rep.append(('  OK    ' if cond else '  FALLA ') + msg)
        ok = ok and bool(cond)

    try:
        # orientación de numpyArray: la rampa vertical marca dónde está "arriba"
        rv = a('ramp_v')[..., 0][:, 0]
        up = rv[-1] > rv[0]

        def Y(arr):
            return arr if up else arr[::-1]

        ix = a('idx_x_r')[..., 0]
        check(np.allclose(ix[0], np.arange(n) / n, atol=1e-4), 'índice x = i/Cols')
        iy = Y(a('idx_y_g')[..., 1])[:, 0]
        check(np.allclose(iy, np.arange(m) / m, atol=1e-4), 'índice y = j/Rows (abajo -> arriba)')
        mx = a('mask_x')[..., 0]
        check(np.allclose(mx[:, -1], 0) and np.allclose(mx[:, :-1], 1), 'mask_x')
        my = Y(a('mask_y')[..., 0])[:, 0]
        check(np.allclose(my[-1], 0) and np.allclose(my[:-1], 1), 'mask_y')
        lim = float(og.par.Limit)
        hl = a('h_clamp')[..., 0]
        check(hl.min() >= -lim - 1e-5 and hl.max() <= lim + 1e-5, 'Limit TOP recorta a ±Limit')
        L = Y(a('layout'))
        x0, y0, w, h = L[..., 0], L[..., 1], L[..., 2], L[..., 3]
        check(np.allclose(x0[:, 0], 0, atol=1e-4), 'borde izquierdo fijo')
        check(np.allclose(x0[:, -1] + w[:, -1], 1, atol=1e-4), 'borde derecho fijo')
        check(np.allclose(x0[:, 1:], x0[:, :-1] + w[:, :-1], atol=1e-4), 'columnas contiguas')
        check(np.allclose(y0[0], 0, atol=1e-4) and np.allclose(y0[-1] + h[-1], 1, atol=1e-4),
              'bordes inferior/superior fijos')
        check(np.allclose(y0[1:], y0[:-1] + h[:-1], atol=1e-4), 'filas contiguas')
        check(w.min() > 0 and h.min() > 0, 'todas las celdas con tamaño > 0')

        sop = og.op('geo_uv_local/to_corner')
        pairs = set()
        for prim in sop.prims:
            for v in prim:
                uv = getattr(v, 'uv', None)
                if uv is None:
                    uv = getattr(v.point, 'uv', None)
                if uv is None:
                    raise RuntimeError('el quad no tiene uv (revisar Texture SOP "uv")')
                pairs.add(((round(uv[0], 3), round(uv[1], 3)),
                           (round(v.point.x, 3), round(v.point.y, 3))))
        check(all(u == p for u, p in pairs) and len(pairs) == 4, 'quad en [0,1]² con uv = posición')

        fl = a('flow_switch')
        rep.append('  INFO  flow (r,g): min {:.4f}/{:.4f}  max {:.4f}/{:.4f}  media {:.4f}/{:.4f}'.format(
            fl[..., 0].min(), fl[..., 1].min(), fl[..., 0].max(), fl[..., 1].max(),
            fl[..., 0].mean(), fl[..., 1].mean()))
        if og.par.Flowmode == 'palette':
            raw = a('flow_in')
            rep.append('  INFO  palette crudo (r,g) media {:.4f}/{:.4f}  (si ~0.5 en reposo -> Flowoffset = 0.5)'.format(
                raw[..., 0].mean(), raw[..., 1].mean()))
    except Exception as e:
        rep.append('  ERROR verificando: {}'.format(e))
        ok = False

    print('\n==== Optical Grid: verificación ====')
    print('\n'.join(rep))
    if LOG:
        print('---- avisos / parámetros que no se pudieron setear:')
        print('\n'.join('  ' + s for s in LOG))
    print('==== {} ====\n'.format('TODO OK' if ok else 'revisar lo marcado'))


og = build()
run('args[0]()', verify, delayFrames=60)
print('Optical Grid construido en', og.path, '- verificando en 1 s...')
