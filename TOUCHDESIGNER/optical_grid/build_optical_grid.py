"""
OPTICAL GRID — constructor de red para TouchDesigner (solo nodos nativos, sin GLSL)
Pegar en un Text DAT y click derecho > Run Script.

Crea /project1/opticalGrid (lo reemplaza si existe).
  - Parámetros: Constant CHOP 'params' dentro de opticalGrid.
  - HUECO para el optical flow: conectá  to_flow -> [opticalFlow de la Palette] -> flow_in
    (los dos son Null TOPs dentro de opticalGrid; hay lugar libre entre ellos).
~1 s después imprime un reporte de verificación en el Textport.
"""

import td

ROOT_PATH = '/project1'
NAME = 'opticalGrid'
LOG = []

# ----------------------------------------------------------------------------- parámetros
PARAMS = [
    ('cols', 12),          # columnas de la grilla (2..48)
    ('rows', 8),           # filas de la grilla (2..48)
    ('resw', 1280),        # resolución de salida
    ('resh', 720),
    ('source', 0),         # 0 = cámara (Video Device In), 1 = archivo (Movie File In)
    ('flowoffset', 0),     # restar a la salida del optical flow (0.5 si en reposo da ~0.5)
    ('flowgain', 1),       # ganancia del optical flow
    ('push', 1.5),         # fronteras se mueven en la dirección del flow
    ('grow', 4),           # celda con más movimiento se agranda
    ('limit', 0.45),       # desplazamiento máximo de cada frontera, en celdas (< 0.5)
    ('smoothstats', 0.6),  # suavizado temporal del flow (0..0.99)
    ('smoothgrid', 0.85),  # suavizado temporal de la grilla (0..0.99)
    ('lines', 1),          # opacidad de las líneas
]


def C(name):
    """Expresión que lee un canal del Constant CHOP 'params'."""
    return "op('params')['{}'].eval()".format(name)


N = 'int({})'.format(C('cols'))
M = 'int({})'.format(C('rows'))
W = 'int({})'.format(C('resw'))
H = 'int({})'.format(C('resh'))


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


def shift(parent_op, name, x, y, src, tx='0', ty='0', extend='zero'):
    """Corre la textura (tx, ty en fracción de la imagen)."""
    o = mk(parent_op, 'transformTOP', name, x, y, [src])
    setp(o, 'tx', expr=tx)
    setp(o, 'ty', expr=ty)
    setmenu(o, 'extend', extend)
    setmenu(o, 'inputfiltertype', 'nearest')
    f32(o)
    return o


def clamp_top(parent_op, name, x, y, src, lo_expr, hi_expr):
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
    setp(o, ['min', 'minimum', 'minval'], expr=lo_expr)
    setp(o, ['max', 'maximum', 'maxval'], expr=hi_expr)
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
    """Índice entero de cada pixel (0,1,2,...) a lo largo de `axis`, por suma prefija
    (duplicación): unos corridos 1 px + copias corridas 1, 2, 4, ... px."""
    key = 'tx' if axis == 'x' else 'ty'
    acc = shift(parent_op, 'idx_{}_s0'.format(tag), x, y, ones, **{key: '1/' + count_expr})
    for k in range(6):                     # 2^6 = 64 > máximo de 48 celdas
        sh = shift(parent_op, 'idx_{}_sh{}'.format(tag, k), x + 1 + k, y + 1, acc,
                   **{key: '{}/{}'.format(2 ** k, count_expr)})
        acc = add(parent_op, 'idx_{}_sum{}'.format(tag, k), x + 1 + k, y, acc, sh)
    return acc


def make_params(og):
    c = mk(og, 'constantCHOP', 'params', 0, -4)
    try:
        c.seq.const.numBlocks = len(PARAMS)          # TD 2022+ (secuencia 'const')
    except Exception:
        pass
    for i, (name, val) in enumerate(PARAMS):
        pn = _par(c, ['const{}name'.format(i), 'name{}'.format(i)])
        pv = _par(c, ['const{}value'.format(i), 'value{}'.format(i)])
        if pn is None or pv is None:
            LOG.append('params: no pude crear el canal {}'.format(name))
            continue
        pn.val = name
        pv.val = val
    return c


# ----------------------------------------------------------------------------- build
def build():
    root = op(ROOT_PATH)
    old = root.op(NAME)
    if old:
        old.destroy()
    og = root.create(td.baseCOMP, NAME)

    make_params(og)

    # ================================================================ 1. FUENTE
    cam = mk(og, 'videodeviceinTOP', 'cam_in', 0, 0)
    mov = mk(og, 'moviefileinTOP', 'movie_in', 0, 1)
    srcsw = mk(og, 'switchTOP', 'src_switch', 1, 0, [cam, mov])
    setp(srcsw, 'index', expr='int({})'.format(C('source')))
    video = mk(og, 'resolutionTOP', 'video', 2, 0, [srcsw])
    res(video, W, H, fmt='rgba8fixed')

    # ================================================================ 2. HUECO: OPTICAL FLOW (Palette)
    #   to_flow  ->  [ opticalFlow de la Palette ]  ->  flow_in
    #   Salida esperada: R = movimiento izq->der, G = abajo->arriba.
    to_flow = mk(og, 'nullTOP', 'to_flow', 3, -2, [video])
    flow_in = mk(og, 'nullTOP', 'flow_in', 7, -2)
    off = mk(og, 'constantTOP', 'flow_offset', 7, -3)
    res(off, '8', '8')
    setp(off, 'colorr', expr='-' + C('flowoffset'))
    setp(off, 'colorg', expr='-' + C('flowoffset'))
    setp(off, 'colorb', 0)
    setp(off, 'alpha', 0)
    flow_c = add(og, 'flow_centered', 8, -2, flow_in, off)
    fl = chmix(og, 'flow_rg', 9, -2, flow_c, red1=C('flowgain'), green2=C('flowgain'))

    # ================================================================ 3. ESTADÍSTICAS POR CELDA
    # stats = (flow.x, flow.y, |flow|^2) promediado dentro de cada celda -> textura Cols x Rows
    sq = mul(og, 'flow_sq', 10, -1, fl, fl)
    energy = chmix(og, 'energy', 11, -1, sq, blue1=1, blue2=1)
    stats_full = add(og, 'stats_full', 12, -2, fl, energy)
    stats_cells = mk(og, 'resolutionTOP', 'stats_cells', 13, -2, [stats_full])
    res(stats_cells, N, M, filt='mipmap')
    S = ema(og, 'stats_ema', 14, -2, stats_cells, '1-' + C('smoothstats'))

    # ================================================================ 4. FRONTERAS DE COLUMNA (por fila)
    # Dh = clamp( push*(fx_i + fx_i+1)/2 + grow*(E_i - E_i+1), ±limit ), última columna = 0
    Sn = shift(og, 'stats_next_x', 17, -4, S, tx='-1/' + N)
    hA = chmix(og, 'h_a', 18, -5, S, red1='0.5*' + C('push'), red3=C('grow'))
    hB = chmix(og, 'h_b', 18, -4, Sn, red1='0.5*' + C('push'), red3='-' + C('grow'))
    hraw = add(og, 'h_raw', 19, -4, hA, hB)
    hlim = clamp_top(og, 'h_clamp', 20, -4, hraw, '-' + C('limit'), C('limit'))
    white = mk(og, 'constantTOP', 'white', 17, -6)
    res(white, N, M)
    setp(white, 'colorr', 1); setp(white, 'colorg', 1); setp(white, 'colorb', 1)
    setp(white, 'alpha', 1)
    maskx = shift(og, 'mask_x', 18, -6, white, tx='-1/' + N)
    hmask = mul(og, 'h_masked', 21, -4, hlim, maskx)
    Dh = ema(og, 'Dh', 22, -4, hmask, '1-' + C('smoothgrid'))
    Dhl = shift(og, 'Dh_left', 24, -4, Dh, tx='1/' + N)

    # ================================================================ 5. FRONTERAS DE FILA (globales)
    R = mk(og, 'resolutionTOP', 'stats_rows', 17, 0, [S])
    res(R, '1', M, filt='mipmap')
    Rn = shift(og, 'stats_next_y', 18, 1, R, ty='-1/' + M)
    vA = chmix(og, 'v_a', 19, 0, R, red2='0.5*' + C('push'), red3=C('grow'))
    vB = chmix(og, 'v_b', 19, 1, Rn, red2='0.5*' + C('push'), red3='-' + C('grow'))
    vraw = add(og, 'v_raw', 20, 0, vA, vB)
    vlim = clamp_top(og, 'v_clamp', 21, 0, vraw, '-' + C('limit'), C('limit'))
    white_y = mk(og, 'constantTOP', 'white_y', 18, 2)
    res(white_y, '1', M)
    setp(white_y, 'colorr', 1); setp(white_y, 'colorg', 1); setp(white_y, 'colorb', 1)
    setp(white_y, 'alpha', 1)
    masky = shift(og, 'mask_y', 19, 2, white_y, ty='-1/' + M)
    vmask = mul(og, 'v_masked', 22, 0, vlim, masky)
    Dv = ema(og, 'Dv', 23, 0, vmask, '1-' + C('smoothgrid'))
    Dvl = shift(og, 'Dv_below', 25, 1, Dv, ty='1/' + M)
    Dv_b = mk(og, 'resolutionTOP', 'Dv_cells', 26, 0, [Dv])
    res(Dv_b, N, M, filt='nearest')
    Dvl_b = mk(og, 'resolutionTOP', 'Dv_below_cells', 26, 1, [Dvl])
    res(Dvl_b, N, M, filt='nearest')

    # ================================================================ 6. ÍNDICES DE CELDA (i/N, j/M)
    cnt_x = prefix_count(og, 'x', 17, -10, white, 'x', N)
    cnt_y = prefix_count(og, 'y', 17, -8, white, 'y', M)
    ixr = chmix(og, 'idx_x_r', 25, -10, cnt_x, red1='1/' + N)
    iyg = chmix(og, 'idx_y_g', 25, -8, cnt_y, green1='1/' + M)
    src_origin = add(og, 'src_origin', 26, -9, ixr, iyg)

    # ================================================================ 7. LAYOUT (x0, y0, w, h)
    #   x0 = (i + Dhl)/N   w = (1 + Dh - Dhl)/N   y0 = (j + Dvl)/M   h = (1 + Dv - Dvl)/M
    base = chmix(og, 'layout_base', 27, -6, white, blue1='1/' + N, alpha1='1/' + M)
    L1 = chmix(og, 'layout_dh', 27, -5, Dh, blue1='1/' + N)
    L2 = chmix(og, 'layout_dhl', 27, -4, Dhl, red1='1/' + N, blue1='-1/' + N)
    L3 = chmix(og, 'layout_dv', 27, 0, Dv_b, alpha1='1/' + M)
    L4 = chmix(og, 'layout_dvl', 27, 1, Dvl_b, green1='1/' + M, alpha1='-1/' + M)
    layout = add(og, 'layout', 29, -3, ixr, iyg, base, L1, L2, L3, L4)

    # ================================================================ 8. RENDER DEL MAPA UV (instancing)
    # Cada pixel de `layout` es una instancia de un quad unitario -> rectángulo de la celda.
    # A: gradiente local (u,v)*(1/N,1/M)   B: color plano = origen fuente.  A + B = UV fuente.
    rh = mk(og, 'rampTOP', 'ramp_h', 29, 3)
    rv = mk(og, 'rampTOP', 'ramp_v', 29, 4)
    for r_, kw in ((rh, 'horizontal'), (rv, 'vertical')):
        res(r_, '1024', '1024')
        setmenu(r_, 'type', kw)
    uvgrad = add(og, 'uv_gradient', 31, 3,
                 chmix(og, 'ramp_h_r', 30, 3, rh, red1=1, alpha4=1),
                 chmix(og, 'ramp_v_g', 30, 4, rv, green2=1))

    camc = mk(og, 'cameraCOMP', 'cam', 31, 6)
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

    matA = mk(og, 'constantMAT', 'mat_uv_local', 32, 3)
    setp(matA, 'colorr', expr='1/' + N)
    setp(matA, 'colorg', expr='1/' + M)
    setp(matA, 'colorb', 0)
    setp(matA, 'colormap', uvgrad.path)
    matB = mk(og, 'constantMAT', 'mat_origin', 32, 5)

    geoA = cell_geo('geo_uv_local', 33, 3, matA)
    geoB = cell_geo('geo_origin', 33, 5, matB, color_op=src_origin)

    def render(name, x, y, geo):
        r_ = mk(og, 'renderTOP', name, x, y)
        res(r_, W, H)
        setp(r_, 'camera', camc.path)
        setp(r_, 'geometry', geo.path)
        setp(r_, 'lights', '')
        setmenu(r_, 'antialias', 'aa1', '1x', '1')
        return r_

    rA = render('render_uv_local', 34, 3, geoA)
    rB = render('render_origin', 34, 5, geoB)
    uvmap = add(og, 'uv_map', 35, 4, rA, rB)

    # ================================================================ 9. LÍNEAS (solo bordes de celda)
    # Un pixel es borde si su celda (color de render_origin) difiere de la del pixel vecino.
    def edge(tag, x, y, **sh):
        s = shift(og, 'edge_{}_shift'.format(tag), x, y, rB, extend='hold', **sh)
        neg = chmix(og, 'edge_{}_neg'.format(tag), x + 1, y, s, red1=-1, green2=-1)
        d = add(og, 'edge_{}_diff'.format(tag), x + 2, y, rB, neg)
        return mul(og, 'edge_{}_sq'.format(tag), x + 3, y, d, d)

    ex = edge('x', 35, 7, tx='1/' + W)
    ey = edge('y', 35, 8, ty='1/' + H)
    e = add(og, 'edges', 39, 7, ex, ey)
    G = 1e6
    emono = chmix(og, 'edges_mono', 40, 7, e, red1=G, red2=G, green1=G, green2=G,
                  blue1=G, blue2=G, alpha1=G, alpha2=G)
    lines = clamp_top(og, 'lines', 41, 7, emono, '0', C('lines'))

    # ================================================================ 10. SALIDA
    remap = mk(og, 'remapTOP', 'remapped', 37, 4, [video, uvmap])
    comp = mk(og, 'compositeTOP', 'with_lines', 42, 5, [remap, lines])
    setmenu(comp, 'operand', 'add')
    out = mk(og, 'nullTOP', 'OUT', 43, 5, [comp])
    out.viewer = True
    return og


# ----------------------------------------------------------------------------- verificación
def verify():
    import numpy as np
    og = op(ROOT_PATH + '/' + NAME)
    prm = og.op('params')
    n, m = int(prm['cols'].eval()), int(prm['rows'].eval())
    rep, ok = [], True

    def a(name):
        return og.op(name).numpyArray(delayed=False)

    def check(cond, msg):
        nonlocal ok
        rep.append(('  OK    ' if cond else '  FALLA ') + msg)
        ok = ok and bool(cond)

    try:
        rv = a('ramp_v')[..., 0][:, 0]
        up = rv[-1] > rv[0]

        def Y(arr):
            return arr if up else arr[::-1]

        ix = a('idx_x_r')[..., 0]
        check(np.allclose(ix[0], np.arange(n) / n, atol=1e-4), 'índice x = i/cols')
        iy = Y(a('idx_y_g')[..., 1])[:, 0]
        check(np.allclose(iy, np.arange(m) / m, atol=1e-4), 'índice y = j/rows')
        L = Y(a('layout'))
        x0, y0, w, h = L[..., 0], L[..., 1], L[..., 2], L[..., 3]
        check(np.allclose(x0[:, 0], 0, atol=1e-4) and np.allclose(x0[:, -1] + w[:, -1], 1, atol=1e-4),
              'bordes izquierdo/derecho fijos')
        check(np.allclose(y0[0], 0, atol=1e-4) and np.allclose(y0[-1] + h[-1], 1, atol=1e-4),
              'bordes inferior/superior fijos')
        check(np.allclose(x0[:, 1:], x0[:, :-1] + w[:, :-1], atol=1e-4), 'columnas contiguas')
        check(np.allclose(y0[1:], y0[:-1] + h[:-1], atol=1e-4), 'filas contiguas')
        check(w.min() > 0 and h.min() > 0, 'todas las celdas con tamaño > 0')
    except Exception as e:
        rep.append('  ERROR verificando: {}'.format(e))
        ok = False
    try:
        fl = a('flow_in')
        rep.append('  INFO  flow_in (r,g) media {:.4f}/{:.4f}  min {:.4f}/{:.4f}  max {:.4f}/{:.4f}'.format(
            fl[..., 0].mean(), fl[..., 1].mean(), fl[..., 0].min(), fl[..., 1].min(),
            fl[..., 0].max(), fl[..., 1].max()))
    except Exception:
        rep.append('  INFO  flow_in todavía sin conectar (to_flow -> opticalFlow -> flow_in)')

    print('\n==== Optical Grid: verificación ====')
    print('\n'.join(rep))
    if LOG:
        print('---- parámetros que no se pudieron setear:')
        print('\n'.join('  ' + s for s in LOG))
    print('==== {} ====\n'.format('TODO OK' if ok else 'revisar lo marcado'))


og = build()
run('args[0]()', verify, delayFrames=60)
print('Optical Grid construido en', og.path,
      '- conectá to_flow -> opticalFlow (Palette) -> flow_in. Verificando en 1 s...')
