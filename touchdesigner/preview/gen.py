# Extrae shaders + animación del script de TD y genera passes.json para WebGL2
# Uso: python3 gen.py ../ossyrave_flyer.py passes.json
import json, sys
src = open(sys.argv[1]).read()
ns = {}
exec(src, ns)          # fuera de TD no construye nada
TDSHIM = '''#version 300 es
precision highp float; precision highp int; precision highp sampler2D;
uniform sampler2D sTD2DInputs[5];
struct TDInfo { vec4 res; };
uniform TDInfo uTDOutputInfo;
vec4 TDOutputSwizzle(vec4 c){ return c; }
'''
passes = {}
for name, code, n in [('sim_a', ns['SIM_A'], 3), ('sim_b', ns['SIM_B'], 1), ('sim_c', ns['SIM_C'], 2),
                      ('sim_d', ns['SIM_D'], 1), ('humo', ns['HUMO'], 1), ('partido', ns['HUMO_PARTIDO'], 3), ('capas', ns['CAPAS'], 3), ('fondo', ns['FONDO'], 2), ('term', ns['TERMINACION'], 1)]:
    passes[name] = TDSHIM + ns['glsl_source'](code, n)
# Composite TOP 'difference' (solo para la vista previa)
passes['diff'] = TDSHIM + ns['glsl_source']('void mainImage(out vec4 o, in vec2 c){ vec2 uv=c/iResolution.xy; vec4 a=texture(iChannel0,uv), b=texture(iChannel1,uv); o=vec4(abs(a.rgb-b.rgb),1.); }', 2)
anim = {}
exec(ns['ANIMACION'], anim)
frames = int(ns['FPS'] * ns['DURACION'])
letters = [[anim['letra'](i, f) for i in range(len(ns['TITULO']))] for f in range(1, frames + 1)]
logo = [anim['logo'](f) for f in range(1, frames + 1)]
json.dump({'passes': passes, 'letters': letters, 'logo': logo, 'text': ns['TITULO'], 'RES': ns['RES'], 'SIM': ns['SIM'],
           'fps': ns['FPS']}, open(sys.argv[2], 'w'))
print('ok', frames, 'frames')
