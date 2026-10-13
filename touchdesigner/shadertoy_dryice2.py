# =====================================================================
#  Shadertoy -> TouchDesigner : "Dry ice 2" (xjorma)
#  https://www.shadertoy.com/view/WlVyRV
#
#  Uso:
#   1. En TouchDesigner creá un Text DAT y pegá este archivo entero.
#   2. Copiá desde Shadertoy el código de cada pestaña (Common, Buffer A,
#      Buffer B, ..., Image) en las variables de abajo. Las pestañas
#      que el shader no tenga, dejalas como None.
#   3. En CHANNELS poné qué tiene cada iChannel de cada pasada (se ve
#      abajo del editor de Shadertoy, en cada pestaña).
#   4. Click derecho en el Text DAT -> "Run Script".
#   Para reiniciar la simulación: op('/project1/dryice/reset').run()
# =====================================================================

COMMON = r'''
'''

BUFFERS = {
    'A': r'''
''',
    'B': None,
    'C': None,
    'D': None,
}

IMAGE = r'''
'''

# Qué hay en iChannel0..3 de cada pasada:
#   'A'..'D' -> ese buffer  |  None -> nada  |  '/ruta/a/un/TOP' -> cualquier TOP
CHANNELS = {
    'A':     ['A', None, None, None],
    'B':     [None, None, None, None],
    'C':     [None, None, None, None],
    'D':     [None, None, None, None],
    'Image': ['A', None, None, None],
}

RES = (1280, 720)
NAME = 'dryice'

# ---------------------------------------------------------------------

HEADER = '''
uniform vec4 uTime;   // x = iTime, y = iTimeDelta, z = iFrame
uniform vec4 uMouse;  // iMouse
#define iTime       uTime.x
#define iTimeDelta  uTime.y
#define iFrame      int(uTime.z)
#define iMouse      uMouse
#define iResolution vec3(uTDOutputInfo.res.zw, 1.0)
{chan_defines}
vec3 iChannelResolution[4];
layout(location = 0) out vec4 _stOut;
'''

FOOTER = '''
void main() {{
{chan_res}
    vec4 col = vec4(0.0);
    mainImage(col, gl_FragCoord.xy);
    _stOut = TDOutputSwizzle(col);
}}
'''

ORDER = ['A', 'B', 'C', 'D']


def build_glsl(code, n_inputs):
    defines = '\n'.join('#define iChannel%d sTD2DInputs[%d]' % (i, i)
                        for i in range(n_inputs))
    chan_res = '\n'.join(
        '    iChannelResolution[%d] = vec3(textureSize(sTD2DInputs[%d], 0), 1.0);'
        % (i, i) for i in range(n_inputs))
    return (HEADER.format(chan_defines=defines) + (COMMON or '') + '\n'
            + code + FOOTER.format(chan_res=chan_res))


def make_glsl_top(comp, name, code, n_inputs, x, y, is_buffer):
    dat = comp.create(textDAT, name + '_code')
    dat.text = build_glsl(code, n_inputs)
    dat.nodeX, dat.nodeY = x, y + 150
    top = comp.create(glslTOP, name)
    top.nodeX, top.nodeY = x, y
    top.par.pixeldat = dat.name
    top.par.outputresolution = 'custom'
    top.par.resolutionw, top.par.resolutionh = RES
    if is_buffer:
        top.par.format = 'rgba32float'  # los buffers de Shadertoy son float
    top.par.vec0name = 'uTime'
    top.par.vec0valuex.expr = "absTime.seconds - parent().fetch('t0', 0)"
    top.par.vec0valuey.expr = "absTime.stepSeconds"
    top.par.vec0valuez.expr = "absTime.frame - parent().fetch('f0', 0)"
    top.par.vec1name = 'uMouse'
    return top


def main():
    parent_comp = op('/project1')
    old = parent_comp.op(NAME)
    if old:
        old.destroy()
    comp = parent_comp.create(baseCOMP, NAME)

    buffers = [b for b in ORDER if BUFFERS.get(b)]
    used = lambda p: [c for c in CHANNELS.get(p, []) if c is not None]

    # Pasadas que necesitan el frame anterior (se leen a sí mismas o a
    # un buffer que se calcula después) -> Feedback TOP.
    needs_fb = set()
    for p in buffers:
        for c in used(p):
            if c in ORDER and ORDER.index(c) >= ORDER.index(p):
                needs_fb.add(c)

    black = comp.create(constantTOP, 'black')
    black.par.outputresolution = 'custom'
    black.par.resolutionw, black.par.resolutionh = RES
    black.par.format = 'rgba32float'
    black.par.alpha = 0
    black.nodeX, black.nodeY = -400, -300

    tops, fbs = {}, {}
    for i, p in enumerate(buffers):
        n = len(CHANNELS[p])
        while n and CHANNELS[p][n - 1] is None:
            n -= 1
        tops[p] = make_glsl_top(comp, 'buf' + p, BUFFERS[p], n,
                                i * 300, 0, True)
        if p in needs_fb:
            fb = comp.create(feedbackTOP, 'fb' + p)
            fb.nodeX, fb.nodeY = i * 300, -200
            black.outputConnectors[0].connect(fb)
            fb.par.top = 'buf' + p
            fbs[p] = fb

    n = len(CHANNELS['Image'])
    while n and CHANNELS['Image'][n - 1] is None:
        n -= 1
    image = make_glsl_top(comp, 'image', IMAGE, n, len(buffers) * 300, 0, False)
    tops['Image'] = image

    def source(pass_name, c):
        if c is None:
            return black
        if c in ORDER:
            if pass_name != 'Image' and ORDER.index(c) >= ORDER.index(pass_name):
                return fbs[c]
            return tops[c]
        return op(c)

    for p in buffers + ['Image']:
        chans = CHANNELS[p]
        last = max([i for i, c in enumerate(chans) if c is not None], default=-1)
        for i in range(last + 1):
            source(p, chans[i]).outputConnectors[0].connect(tops[p].inputConnectors[i])

    out = comp.create(nullTOP, 'out')
    out.nodeX, out.nodeY = image.nodeX + 300, 0
    image.outputConnectors[0].connect(out)
    out.viewer = True

    reset = comp.create(textDAT, 'reset')
    reset.nodeX, reset.nodeY = -400, 200
    reset.text = (
        "parent().store('t0', absTime.seconds)\n"
        "parent().store('f0', absTime.frame)\n"
        "for fb in parent().findChildren(type=feedbackTOP):\n"
        "    fb.par.resetpulse.pulse()\n")
    reset.run()
    print('Red de Shadertoy creada en', comp.path)


main()
