# =====================================================================
#  OSSYRAVE — flyer animado en TouchDesigner (12 s, 60 fps)
#
#  Humo: "Dry ice 2" de David Gallardo (xjorma), adaptado.
#        https://www.shadertoy.com/view/WlVyRV   (CC BY-NC-SA 3.0)
#
#  Uso:
#   1. Poné foto.jpg, recorte.png y profundidad.png al lado del .toe
#      (o cambiá las rutas en los parámetros del COMP).
#   2. Pegá ESTE ARCHIVO COMPLETO en un Text DAT -> click derecho ->
#      Run Script. Se crea /project1/ossyrave y el timeline queda en
#      12 s a 60 fps.
#   3. Todo se ajusta desde los parámetros del COMP "ossyrave"
#      (página "Flyer"). El movimiento de las letras está en
#      ossyrave/titulo/animacion.
#   4. "Exportar 12 s" graba ossyrave.mov empezando del frame 1.
#
#  Determinismo: la simulación arranca de cero en el frame 1 y avanza
#  un paso por frame del timeline. Para un resultado idéntico, reproducí
#  siempre desde el frame 1 sin saltear frames (Exportar ya lo hace).
# =====================================================================

LINEAS = ('OSSY', 'RAVE')       # título en dos líneas
TITULO = ''.join(LINEAS)
FPS = 60
DURACION = 12                 # segundos
RES = (1116, 2000)            # resolución del flyer (la de las imágenes)
SIM = (558, 1000)             # resolución de la simulación de humo
NAME = 'ossyrave'

# =====================================================================
#  GLSL
# =====================================================================

# ---------------------------------------------------------------------
# Common: compartido por todas las pasadas
# ---------------------------------------------------------------------
COMMON = r'''
const float dissipation   = 0.95;
const float fogHeigth     = 0.24;
const int   nbSlice       = 24;
const float fogSlice      = fogHeigth / float(nbSlice);
const float shadowDensity = 25.;
const float fogDensity    = 20.;
const float lightHeight   = 1.;
const float tau           = radians(360.);

float hash12(vec2 p)
{
    vec3 p3  = fract(vec3(p.xyx) * .1031);
    p3 += dot(p3, p3.yzx + 33.33);
    return fract((p3.x + p3.y) * p3.z);
}

vec4 hash41(float p)
{
    vec4 p4 = fract(vec4(p) * vec4(.1031, .1030, .0973, .1099));
    p4 += dot(p4, p4.wzxy+33.33);
    return fract((p4.xxyz+p4.yzzw)*p4.zywx);
}

float noise(vec3 p)
{
    vec3 ip=floor(p);
    p-=ip;
    vec3 s=vec3(7,157,113);
    vec4 h=vec4(0.,s.yz,s.y+s.z)+dot(ip,s);
    p=p*p*(3.-2.*p);
    h=mix(fract(sin(h)*43758.5),fract(sin(h+s.x)*43758.5),p.x);
    h.xy=mix(h.xz,h.yw,p.y);
    return mix(h.x,h.y,p.z);
}

// Recorrido de la luz (era la bola blanca del shader original)
vec2 lightPath(int frame)
{
    vec4 offset = hash41(0.) * tau;
    float f = float(frame);
    return vec2(cos(offset.x + f * 0.015) + cos(offset.y + f * 0.020),
                cos(offset.z + f * 0.017) + cos(offset.w + f * 0.022)) * vec2(1., 0.5) * 0.9;
}

float dist2(vec3 v)
{
    return dot(v, v);
}
'''

# ---------------------------------------------------------------------
# sim_a: advección + inyección de humo + empuje del texto
#   iChannel0 presión (frame anterior)   iChannel1 sim_a (frame anterior)
#   iChannel2 máscara del texto
#   Salida: xy velocidad, z densidad, w máscara (para el próximo frame)
# ---------------------------------------------------------------------
SIM_A = r'''
#define DENSIDAD uP.x
#define EMPUJE   uP.y
#define SUBIDA   uP.z

vec2 fbm(vec3 p, int octaveNum)
{
    vec2 acc = vec2(0);
    float amp = 0.5;
    vec3 shift = vec3(100);
    for (int i = 0; i < octaveNum; i++)
    {
        acc += vec2(noise(p), noise(p + vec3(0,0,10))) * amp;
        p = p * 2.0 + shift;
        amp *= 0.5;
    }
    return acc;
}

vec3 sampleMinusGradient(vec2 coord)
{
    vec3  veld   = texture(iChannel1, coord / iResolution.xy).xyz;
    float left   = texture(iChannel0, (coord + vec2(-1, 0)) / iResolution.xy).x;
    float right  = texture(iChannel0, (coord + vec2( 1, 0)) / iResolution.xy).x;
    float bottom = texture(iChannel0, (coord + vec2( 0,-1)) / iResolution.xy).x;
    float top    = texture(iChannel0, (coord + vec2( 0, 1)) / iResolution.xy).x;
    vec2  grad   = vec2(right - left, top - bottom) * 0.5;
    return vec3(veld.xy - grad, veld.z);
}

vec3 vignette(vec3 color, vec2 q, float v)
{
    color *= mix(1., pow(16.0 * q.x * q.y * (1.0 - q.x) * (1.0 - q.y), v), 0.02);
    return color;
}

void mainImage( out vec4 fragColor, in vec2 fragCoord )
{
    // Advección (Euler)
    vec2  velocity = sampleMinusGradient(fragCoord).xy;
    vec3  veld = sampleMinusGradient(fragCoord - dissipation * velocity).xyz;
    float density = veld.z;
    velocity = veld.xy;

    vec2 q  = fragCoord / iResolution.xy;
    vec2 uv = (2. * fragCoord - iResolution.xy) / iResolution.y;

    // Colchón de humo fijo sobre el piso: está desde el frame 1 y tapa
    // el corte del recorte a la altura de los pies.
    float colchon = (1. - smoothstep(0.0, 0.17, q.y))
                  * (0.55 + 0.45 * noise(vec3(uv * vec2(5., 9.), iTime * 0.4)));
    if (iFrame == 0)
    {
        density = colchon;
        velocity = vec2(0.);
    }
    density = max(density, colchon);

    // El humo nace sobre el piso y flota hacia arriba
    float piso = 1. - smoothstep(0.02, 0.30, q.y);
    velocity.y += 0.04 * SUBIDA * density;
    velocity *= 0.995;

    // Perturbación fina
    vec2 detailNoise = fbm(vec3(uv * 40., iTime * 0.5 + 30.), 7) - 0.5;
    velocity += detailNoise * 0.2;
    density  += length(detailNoise) * 0.004 * piso * DENSIDAD;

    // Inyección: solo donde el ruido supera un umbral -> deja zonas vacías
    vec2 injectionNoise = fbm(vec3(uv * 1.5, iTime * 0.1 + 30.), 7) - 0.5;
    velocity += injectionNoise * 0.1;
    density  += smoothstep(0.10, 0.26, length(injectionNoise)) * 0.04 * piso * DENSIDAD;

    // Texto: las letras son obstáculos sólidos que arrastran el humo.
    // La velocidad de cada borde sale de cuánto cambió la máscara
    // entre este frame y el anterior (flujo óptico).
    vec2  px = 1. / iResolution.xy;
    float m  = texture(iChannel2, q).a;
    float mp = texture(iChannel1, q).a;   // máscara del frame anterior
    vec2  g  = vec2(texture(iChannel2, q + vec2(px.x, 0.)).a - texture(iChannel2, q - vec2(px.x, 0.)).a,
                    texture(iChannel2, q + vec2(0., px.y)).a - texture(iChannel2, q - vec2(0., px.y)).a) * 0.5;
    vec2  vText = -(m - mp) * g / (dot(g, g) + 1e-3);
    float l = length(vText);
    if (l > 10.) vText *= 10. / l;
    velocity = mix(velocity, vText * EMPUJE, m);
    density *= 1. - m;

    density = min(1., density);
    density *= 0.996;      // se disipa lento: llega hasta arriba
    veld = vignette(vec3(velocity, density), q, 1.);
    fragColor = vec4(veld, m);
}
'''

# ---------------------------------------------------------------------
# sim_b: divergencia
# ---------------------------------------------------------------------
SIM_B = r'''
void mainImage(out vec4 fragColor, in vec2 fragCoord)
{
    ivec2 icoord = ivec2(fragCoord);
    float vel_x_left   = texelFetch(iChannel0, icoord + ivec2(-1,  0), 0).x;
    float vel_x_right  = texelFetch(iChannel0, icoord + ivec2( 1,  0), 0).x;
    float vel_y_bottom = texelFetch(iChannel0, icoord + ivec2( 0, -1), 0).y;
    float vel_y_top    = texelFetch(iChannel0, icoord + ivec2( 0,  1), 0).y;
    float divergence   = (vel_x_right - vel_x_left + vel_y_top - vel_y_bottom) * 0.5;
    fragColor = vec4(divergence, vec3(1));
}
'''


# Las sumas getDiv()/getPre() de sim_c y sim_d son tablas que el autor
# generó con un programa en C++; acá se generan igual (mismos coeficientes).
def _tables(levels=10):
    def step(c):
        n = {}
        for (x, y), v in c.items():
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n[(x + dx, y + dy)] = n.get((x + dx, y + dy), 0) + v
        return n
    walks, div = {(0, 0): 1}, {}
    for k in range(levels):
        for p, v in walks.items():
            div[p] = div.get(p, 0) + v * 4 ** (levels - 1 - k)
        walks = step(walks)
    return div, walks


def _sum_func(name, fetch, tab):
    body = ''.join('    p += %d.*%s(%d, %d);\n' % (v, fetch, x, y)
                   for (x, y), v in sorted(tab.items()) if v)
    return ('float %s( void )\n{\n    float p = 0.;\n%s'
            '    return  p / 1048576.;\n}\n' % (name, body))


_DIV, _PRE = _tables()

# ---------------------------------------------------------------------
# sim_c: presión, 1ª iteración   (iChannel0 sim_b, iChannel1 sim_d anterior)
# ---------------------------------------------------------------------
SIM_C = r'''
float div(int x,int y)
{
    return texelFetch(iChannel0, ivec2(gl_FragCoord.xy) + ivec2(x, y), 0).x;
}
float pre(int x,int y)
{
    return texelFetch(iChannel1, ivec2(gl_FragCoord.xy) + ivec2(x, y), 0).x;
}
''' + _sum_func('getDiv', 'div', _DIV) + _sum_func('getPre', 'pre', _PRE) + r'''
void mainImage( out vec4 fragColor, in vec2 C )
{
    float div = getDiv();
    float p = getPre() - div;
    fragColor = vec4(p, div, vec3(1));
}
'''

# ---------------------------------------------------------------------
# sim_d: presión, 2ª iteración   (iChannel0 sim_c)
# ---------------------------------------------------------------------
SIM_D = r'''
float div(int x,int y)
{
    return texelFetch(iChannel0, ivec2(gl_FragCoord.xy) + ivec2(x, y), 0).y;
}
float pre(int x,int y)
{
    return texelFetch(iChannel0, ivec2(gl_FragCoord.xy) + ivec2(x, y), 0).x;
}
''' + _sum_func('getPre', 'pre', _PRE) + r'''
void mainImage( out vec4 fragColor, in vec2 C )
{
    float p = getPre() - div(0,0);
    fragColor = vec4(p, vec3(1));
}
'''

# ---------------------------------------------------------------------
# humo: render volumétrico del humo, alineado con la pantalla.
#   Sale RGBA premultiplicado: alfa = opacidad del humo.
#   iChannel0 sim_a
# ---------------------------------------------------------------------
HUMO = r'''
#define BRILLO uP.x
const float viewTilt = 0.35;   // inclinación de la mirada (0 = desde arriba)
const float ambiente = 0.25;   // luz mínima del humo en sombra

float sampleFog(in vec3 pos)
{
    vec2 uv = pos.xz;
    uv.x *= iResolution.y / iResolution.x;
    uv = uv * 0.5 + 0.5;
    if(max(uv.x, uv.y) > 1. || min(uv.x, uv.y) < 0.)
        return 0.;
    return texture(iChannel0, uv).z;
}

vec3 lightPos()
{
    float aspect = iResolution.x / iResolution.y;
    vec2 p = lightPath(iFrame);
    return vec3(p.x * aspect / 1.8, fogHeigth + lightHeight, p.y * 0.6 - 0.35);
}

// Devuelve (luz recibida por el humo, opacidad del humo)
vec2 renderFog(in vec3 ro, in vec3 rd, float fudge)
{
    vec3 light = lightPos();
    vec3 fogStep = (fogHeigth / float(nbSlice)) * rd / abs(rd.y);
    vec3 curPos = ro + fudge * fogStep;
    float stepLen = length(fogStep);
    float transmittance = 1.;
    float lightEnergy = 0.;
    for(int i = 0; i < nbSlice; i++)
    {
        float curHeigth = sampleFog(curPos) * fogHeigth;
        float curSample = min(max(0., curHeigth - curPos.y), fogSlice) * stepLen / fogSlice;
        if(curSample > 0.001)
        {
            vec3 lightDir = normalize(light - curPos);
            vec3 shadowStep = (fogHeigth / float(nbSlice)) * lightDir / lightDir.y;
            float lightDist2 = dist2(light - curPos);
            vec3 shadowPos = curPos + shadowStep * fudge;
            float shadowDist = 0.;
            for (int j = 0; j < nbSlice; j++)
            {
                shadowPos += shadowStep;
                if(shadowPos.y > fogHeigth)
                    break;
                float curHeight = sampleFog(shadowPos) * fogHeigth;
                shadowDist += min(max(0., curHeight - shadowPos.y), fogSlice) * length(shadowStep) / fogSlice;
            }
            float shadowFactor = exp(-shadowDist * shadowDensity) / lightDist2;
            float curDensity = curSample * fogDensity;
            lightEnergy += shadowFactor * curDensity * transmittance;
            transmittance *= 1. - curDensity;
        }
        curPos += fogStep;
    }
    return vec2(lightEnergy, 1. - transmittance);
}

void mainImage( out vec4 fragColor, in vec2 fragCoord )
{
    vec2 q = fragCoord / iResolution.xy;
    float aspect = iResolution.x / iResolution.y;
    vec3 ro = vec3((q.x * 2. - 1.) * aspect, fogHeigth, q.y * 2. - 1.);
    vec3 rd = normalize(vec3(0., -1., viewTilt));
    vec2 fog = renderFog(ro, rd, hash12(fragCoord + iTime));
    float a = clamp(fog.y, 0., 1.);
    float l = sqrt(1. - exp(-fog.x * 3. * BRILLO));   // exposición suave
    l = ambiente + (1. - ambiente) * l;
    fragColor = vec4(vec3(l * a), a);
}
'''

# ---------------------------------------------------------------------
# Composición en tres pasos (cada GLSL TOP con 3 entradas como máximo)
#
# humo_partido: decide qué parte del humo queda detrás de la chica
#   iChannel0 humo (premult)   iChannel1 profundidad   iChannel2 recorte
#   Salida: x luz del humo, y opacidad, z fracción que va detrás
# ---------------------------------------------------------------------
HUMO_PARTIDO = r'''
#define CORTE uP.x   // altura hasta donde el humo pasa por delante de ella

void mainImage( out vec4 fragColor, in vec2 fragCoord )
{
    vec2 uv = fragCoord / iResolution.xy;
    vec4 humo = texture(iChannel0, uv);
    float prof = texture(iChannel1, uv).r;                  // blanco = cerca
    float chica = texture(iChannel2, uv).a * smoothstep(0.055, 0.14, uv.y);

    // El humo bajo está cerca de cámara y el alto lejos, con algo de ruido
    // para que se entrelace con ella.
    float profHumo = mix(0.2, 0.95, smoothstep(CORTE, 0., uv.y))
                   + (noise(vec3(uv * vec2(4., 7.), iTime * 0.15)) - 0.5) * 0.25;
    float delante = smoothstep(-0.05, 0.05, profHumo - prof);
    float atras = (1. - delante) * chica;
    fragColor = vec4(humo.r, humo.a, atras, 1.);
}
'''

# ---------------------------------------------------------------------
# capas: foto limpia -> humo de atrás -> chica -> humo de adelante
#   iChannel0 foto original   iChannel1 recorte (premult)   iChannel2 humo_partido
# ---------------------------------------------------------------------
CAPAS = r'''
#define LIMPIEZA uP.x   // cuánto se borra el humo pintado en la foto
const vec3 tonoHumo = vec3(1.0, 0.95, 0.86);   // sepia de la foto

void mainImage( out vec4 fragColor, in vec2 fragCoord )
{
    vec2 uv = fragCoord / iResolution.xy;

    // Fondo: la foto original sin el humo pintado de la parte baja
    vec3 foto = texture(iChannel0, uv).rgb;
    float lum = dot(foto, vec3(0.299, 0.587, 0.114));
    float zonaBaja = 1. - smoothstep(0.45, 0.66, uv.y);
    foto *= 1. - smoothstep(0.12, 0.45, lum) * zonaBaja * LIMPIEZA;

    // La chica, que se funde hacia los pies
    vec4 chica = texture(iChannel1, uv) * smoothstep(0.055, 0.14, uv.y);

    // Humo partido en dos capas
    vec4 h = texture(iChannel2, uv);
    vec4 humo = vec4(vec3(h.x) * tonoHumo, h.y);
    vec4 humoAtras   = humo * h.z;
    vec4 humoDelante = humo * (1. - h.z);

    vec3 col = foto;
    col = col * (1. - humoAtras.a)   + humoAtras.rgb;
    col = col * (1. - chica.a)       + chica.rgb;
    col = col * (1. - humoDelante.a) + humoDelante.rgb;
    fragColor = vec4(col, 1.);
}
'''

# ---------------------------------------------------------------------
# terminacion: título encima, viñeta y grano
#   iChannel0 capas   iChannel1 título (premult)
# ---------------------------------------------------------------------
TERMINACION = r'''
#define GRANO  uP.x
#define GLITCH uP.y    // separación RGB del título (la da animacion.glitch)

void mainImage( out vec4 fragColor, in vec2 fragCoord )
{
    vec2 uv = fragCoord / iResolution.xy;
    vec3 col = texture(iChannel0, uv).rgb;

    // Título con separación de canales (rojo a un lado, azul al otro)
    vec2 d = vec2((1.5 + 16. * GLITCH) / iResolution.x, 0.);
    vec4 tR = texture(iChannel1, uv + d);
    vec4 tG = texture(iChannel1, uv);
    vec4 tB = texture(iChannel1, uv - d);
    float ta = max(tG.a, max(tR.a, tB.a));
    col = col * (1. - ta) + vec3(tR.r, tG.g, tB.b);

    vec2 c = uv - 0.5;
    col *= 1. - 0.6 * dot(c, c);
    col += (hash12(fragCoord + float(iFrame) * 17.31) - 0.5) * GRANO;   // determinista
    fragColor = vec4(clamp(col, 0., 1.), 1.);
}
'''

# =====================================================================
#  Animación del título (va a ossyrave/titulo/animacion)
# =====================================================================

ANIMACION = '''# Animación del título.
# Todo depende solo del frame -> cada reproducción es idéntica.
# Las letras empujan el humo solas: cualquier movimiento que hagas acá
# (o con keyframes en los Transform TOP mov1..mov8) se transmite al humo.
#
# Unidades:  x, y  -> fracción de la pantalla (0 = centro, 0.5 = borde)
#            escala_x, escala_y -> 1 = tamaño normal    rot -> grados
#            opacidad -> 0..1

import math

FPS = %(fps)d
LINEAS = %(lineas)r
ESTIRAR = 1.35              # letras extendidas: ancho / alto
ANCHO = 0.205               # distancia entre letras (fracción del ancho)
Y_LINEAS = (0.37, 0.265)    # altura de cada línea
ENTRADA = (1.0, 1.6)        # segundo en que empieza a entrar cada línea
LADO = (-1, 1)              # OSSY entra por la izquierda, RAVE por la derecha
DESFASE = 0.10              # segundos entre letras
VIAJE = 2.0                 # segundos que tarda cada letra en entrar
DESTELLO = 0.3              # segundos de parpadeo al llegar


def _suave(x):
    x = min(max(x, 0.), 1.)
    return x * x * (3. - 2. * x)


def _ubicar(i):
    for linea, texto in enumerate(LINEAS):
        if i < len(texto):
            return linea, i
        i -= len(texto)


def _estado(i, t):
    linea, col = _ubicar(i)
    n = len(LINEAS[linea])
    lado = LADO[linea]
    # entra primero la letra que tiene más camino por delante
    orden = (n - 1 - col) if lado < 0 else col
    inicio = ENTRADA[linea] + orden * DESFASE
    u = (t - inicio) / VIAJE
    k = _suave(u)
    x_final = (col - (n - 1) / 2.) * ANCHO
    x_inicio = lado * 0.75                 # justo afuera de la pantalla
    x = x_inicio + (x_final - x_inicio) * k
    # velocidad relativa (0..1) para estirar la letra y el glitch
    vel = 0.
    if 0. < u < 1.:
        vel = min(abs(x_final - x_inicio) * 6. * u * (1. - u) / VIAJE / 0.9, 1.)
    return linea, x, u, vel


def letra(i, frame):
    t = (frame - 1) / FPS
    linea, x, u, vel = _estado(i, t)
    llegada = (u - 1.) * VIAJE                # segundos desde que llegó
    opacidad = 1. if u > 0. else 0.
    if 0. <= llegada < DESTELLO:              # estroboscópico al llegar
        opacidad = 1. if (frame // 3) %% 2 == 0 else 0.25
    return {'x': x,
            'y': Y_LINEAS[linea],
            'escala_x': ESTIRAR * (1. + 0.5 * vel),   # se estira con la velocidad
            'escala_y': 1. - 0.15 * vel,
            'rot': 0.,
            'opacidad': opacidad}


def glitch(frame):
    # 0..1: separación RGB del título. Sube cuando las letras se mueven
    # y en dos golpes cortos más adelante.
    t = (frame - 1) / FPS
    g = 0.
    for i in range(sum(len(l) for l in LINEAS)):
        g = max(g, _estado(i, t)[3])
    for golpe in (6.5, 9.2):
        if 0. <= t - golpe < 0.25:
            g = max(g, 0.8 if (frame // 2) %% 2 == 0 else 0.2)
    return g
''' % {'fps': FPS, 'lineas': LINEAS}

# =====================================================================
#  Construcción de la red (solo corre dentro de TouchDesigner)
# =====================================================================

HEADER = r'''
uniform vec4 uTime;   // x = iTime, y = iTimeDelta, z = iFrame
uniform vec4 uP;      // parámetros de la pasada
#define iTime       uTime.x
#define iTimeDelta  uTime.y
#define iFrame      int(uTime.z)
#define iResolution vec3(uTDOutputInfo.res.zw, 1.0)
layout(location = 0) out vec4 _stOut;

// En WebGL un texelFetch fuera de la textura devuelve 0; en desktop GL
// no está definido, así que lo forzamos.
vec4 _stFetch(sampler2D s, ivec2 c, int l)
{
    if (any(lessThan(c, ivec2(0))) || any(greaterThanEqual(c, textureSize(s, l))))
        return vec4(0.0);
    return texelFetch(s, c, l);
}
#define texelFetch _stFetch
'''

FOOTER = r'''
void main()
{
    vec4 col = vec4(0.0);
    mainImage(col, gl_FragCoord.xy);
    _stOut = TDOutputSwizzle(col);
}
'''

TIME_X = '(me.time.frame - me.time.start) / me.time.rate'
TIME_Y = '1 / me.time.rate'
TIME_Z = 'me.time.frame - me.time.start'
RESET = 'me.time.frame <= me.time.start'


def glsl_source(code, n_channels):
    defines = ''.join('#define iChannel%d sTD2DInputs[%d]\n' % (i, i)
                      for i in range(n_channels))
    return HEADER + defines + COMMON + code + FOOTER


def glsl_pass(comp, name, code, n_channels, res, x, y, fmt=None, params=()):
    dat = comp.create(textDAT, name + '_glsl')
    dat.text = glsl_source(code, n_channels)
    dat.nodeX, dat.nodeY = x, y + 160
    dat.viewer = False
    top = comp.create(glslTOP, name)
    top.nodeX, top.nodeY = x, y
    top.par.pixeldat = dat.name
    top.par.outputresolution = 'custom'
    top.par.resolutionw, top.par.resolutionh = res
    if fmt:
        top.par.format = fmt
    top.par.vec0name = 'uTime'
    top.par.vec0valuex.expr = TIME_X
    top.par.vec0valuey.expr = TIME_Y
    top.par.vec0valuez.expr = TIME_Z
    top.par.vec1name = 'uP'
    for comp_name, expr in zip('xyzw', params):
        getattr(top.par, 'vec1value' + comp_name).expr = expr
    return top


def feedback(comp, name, target, src, x, y):
    fb = comp.create(feedbackTOP, name)
    fb.nodeX, fb.nodeY = x, y
    src.outputConnectors[0].connect(fb)
    fb.par.top = target
    fb.par.reset.expr = RESET     # el frame 1 arranca siempre de cero
    return fb


_EXPECTED = []   # (nodo, índice, fuente) para verificar al final


def wire(src, dst, i):
    # TouchDesigner a veces no crea el próximo conector libre hasta más
    # tarde; en ese caso conectamos a la siguiente entrada libre (siempre
    # cableamos en orden, así que el índice coincide).
    try:
        src.outputConnectors[0].connect(dst.inputConnectors[i])
    except IndexError:
        src.outputConnectors[0].connect(dst)
    _EXPECTED.append((dst, i, src))


def check_wiring():
    ok = True
    for dst, i, src in _EXPECTED:
        ins = dst.inputs
        if i >= len(ins) or ins[i] is None or ins[i].path != src.path:
            ok = False
            print('ATENCION: %s entrada %d deberia ser %s, es %s'
                  % (dst.path, i, src.name, ins[i].name if i < len(ins) and ins[i] else None))
    return ok


def add_custom_pars(comp):
    comp.par.parentshortcut = 'Flyer'
    page = comp.appendCustomPage('Flyer')

    def fpar(name, label, val, lo, hi):
        p = page.appendFloat(name, label=label)[0]
        p.default = val
        p.val = val
        p.normMin, p.normMax = lo, hi

    for name, label, file in (('Foto', 'Foto original', 'foto.jpg'),
                              ('Recorte', 'Recorte (alfa)', 'recorte.png'),
                              ('Profundidad', 'Profundidad', 'profundidad.png')):
        p = page.appendFile(name, label=label)[0]
        p.val = file          # relativa a la carpeta del .toe
    fpar('Densidad', 'Densidad del humo', 1.0, 0, 3)
    fpar('Brillo', 'Brillo del humo', 1.0, 0, 3)
    fpar('Empuje', 'Empuje del texto', 1.0, 0, 3)
    fpar('Subida', 'Subida del humo', 1.0, 0, 3)
    fpar('Corte', 'Humo delante hasta', 0.38, 0, 1)
    fpar('Limpieza', 'Borrar humo pintado', 1.0, 0, 1)
    fpar('Grano', 'Grano', 0.04, 0, 0.2)
    p = page.appendStr('Fuente', label='Fuente')[0]
    p.val = 'Arial Black'
    fpar('Tamano', 'Tamaño de letra', 220, 40, 500)
    page.appendPulse('Exportar', label='Exportar 12 s')


def build_titulo(flyer):
    comp = flyer.create(baseCOMP, 'titulo')
    comp.nodeX, comp.nodeY = 0, -300
    anim = comp.create(textDAT, 'animacion')
    anim.text = ANIMACION
    anim.nodeX, anim.nodeY = -300, 200

    letras = comp.create(compositeTOP, 'letras')
    letras.par.operand = 'over'
    letras.nodeX, letras.nodeY = 600, 0
    for i, ch in enumerate(TITULO):
        get = "mod.animacion.letra(%d, me.time.frame)['%%s']" % i
        txt = comp.create(textTOP, 'letra%d' % (i + 1))
        txt.nodeX, txt.nodeY = 0, -i * 120
        txt.par.outputresolution = 'custom'
        txt.par.resolutionw, txt.par.resolutionh = RES
        txt.par.text = ch
        txt.par.font.expr = 'parent.Flyer.par.Fuente'
        txt.par.fontsizex.expr = 'parent.Flyer.par.Tamano'
        txt.par.fontcolorr, txt.par.fontcolorg, txt.par.fontcolorb = 0.97, 0.96, 0.93
        txt.par.fontalpha.expr = get % 'opacidad'
        txt.par.bgalpha = 0
        mov = comp.create(transformTOP, 'mov%d' % (i + 1))
        mov.nodeX, mov.nodeY = 200, -i * 120
        mov.par.tx.expr = get % 'x'
        mov.par.ty.expr = get % 'y'
        mov.par.rotate.expr = get % 'rot'
        mov.par.sx.expr = get % 'escala_x'
        mov.par.sy.expr = get % 'escala_y'
        txt.outputConnectors[0].connect(mov)
        mov.outputConnectors[0].connect(letras.inputConnectors[i])
    out = comp.create(outTOP, 'out1')
    out.nodeX, out.nodeY = 800, 0
    letras.outputConnectors[0].connect(out)
    return comp


def build_humo(flyer):
    comp = flyer.create(baseCOMP, 'humo')
    comp.nodeX, comp.nodeY = 200, -300
    # Toma el título por ruta (sin cables entre COMPs)
    texto = comp.create(selectTOP, 'texto')
    texto.par.top = '../titulo/out1'
    texto.nodeX, texto.nodeY = -600, 0

    # Máscara del texto a la resolución de la simulación (suavizada para
    # que los bordes empujen con un gradiente parejo)
    mascara = comp.create(blurTOP, 'mascara')
    mascara.nodeX, mascara.nodeY = -400, 0
    mascara.par.size = 12
    mascara.par.outputresolution = 'custom'
    mascara.par.resolutionw, mascara.par.resolutionh = SIM
    texto.outputConnectors[0].connect(mascara)

    negro = comp.create(constantTOP, 'negro')
    negro.nodeX, negro.nodeY = -600, -300
    negro.par.outputresolution = 'custom'
    negro.par.resolutionw, negro.par.resolutionh = SIM
    negro.par.format = 'rgba32float'
    negro.par.alpha = 0

    sim_params = ('parent.Flyer.par.Densidad', 'parent.Flyer.par.Empuje',
                  'parent.Flyer.par.Subida')
    a = glsl_pass(comp, 'sim_a', SIM_A, 3, SIM, 0, 0, 'rgba32float', sim_params)
    b = glsl_pass(comp, 'sim_b', SIM_B, 1, SIM, 200, 0, 'rgba32float')
    c = glsl_pass(comp, 'sim_c', SIM_C, 2, SIM, 400, 0, 'rgba32float')
    d = glsl_pass(comp, 'sim_d', SIM_D, 1, SIM, 600, 0, 'rgba32float')
    render = glsl_pass(comp, 'render', HUMO, 1, RES, 850, 0, None,
                       ('parent.Flyer.par.Brillo',))

    fb_a = feedback(comp, 'sim_a_anterior', 'sim_a', negro, -200, -300)
    fb_d = feedback(comp, 'sim_d_anterior', 'sim_d', negro, -200, -450)

    wire(fb_d, a, 0)
    wire(fb_a, a, 1)
    wire(mascara, a, 2)
    wire(a, b, 0)
    wire(b, c, 0)
    wire(fb_d, c, 1)
    wire(c, d, 0)
    wire(a, render, 0)
    wire(d, render, 1)   # no se usa: solo hace que sim_d se calcule cada frame

    out = comp.create(outTOP, 'out1')
    out.nodeX, out.nodeY = 1050, 0
    render.outputConnectors[0].connect(out)
    return comp


EXPORT_PAREXEC = '''# Botón "Exportar 12 s": vuelve al frame 1 y graba sin saltear frames
# (realTime apagado: TD calcula cada frame aunque tarde más que 1/60 s).
def onPulse(par):
    if par.name != 'Exportar':
        return
    flyer = par.owner
    project.realTime = False
    root.time.frame = root.time.start
    flyer.store('exportando', True)
    flyer.op('grabar').par.record = True
    root.time.play = True
'''

EXPORT_EXEC = '''# Corta la grabación después del último frame del timeline.
def onFrameEnd(frame):
    flyer = parent()
    if flyer.fetch('exportando', False) and root.time.frame >= root.time.end:
        flyer.op('grabar').par.record = False
        flyer.store('exportando', False)
        project.realTime = True
'''


def set_timeline():
    t = root.time
    end = FPS * DURACION
    for attr, val in (('rate', FPS), ('start', 1), ('end', end),
                      ('rangeStart', 1), ('rangeEnd', end)):
        try:
            setattr(t, attr, val)
        except Exception:
            getattr(t.par, attr.lower()).val = val
    t.frame = 1


def build():
    project_comp = op('/project1')
    if project_comp.op(NAME):
        project_comp.op(NAME).destroy()
    flyer = project_comp.create(baseCOMP, NAME)
    add_custom_pars(flyer)
    set_timeline()

    # Entradas
    for i, (name, par) in enumerate((('foto', 'Foto'), ('recorte', 'Recorte'),
                                     ('profundidad', 'Profundidad'))):
        m = flyer.create(moviefileinTOP, name)
        m.par.file.expr = 'parent.Flyer.par.%s' % par
        m.nodeX, m.nodeY = 0, 300 - i * 150

    build_titulo(flyer)
    build_humo(flyer)

    # Salidas de los COMPs tomadas por ruta con Select TOPs
    sel_humo = flyer.create(selectTOP, 'humo_out')
    sel_humo.par.top = 'humo/out1'
    sel_humo.nodeX, sel_humo.nodeY = 300, -150
    sel_titulo = flyer.create(selectTOP, 'titulo_out')
    sel_titulo.par.top = 'titulo/out1'
    sel_titulo.nodeX, sel_titulo.nodeY = 300, -300

    partido = glsl_pass(flyer, 'humo_partido', HUMO_PARTIDO, 3, RES, 500, -150,
                        'rgba16float', ('parent.Flyer.par.Corte',))
    wire(sel_humo, partido, 0)
    wire(flyer.op('profundidad'), partido, 1)
    wire(flyer.op('recorte'), partido, 2)

    capas = glsl_pass(flyer, 'capas', CAPAS, 3, RES, 700, 0, None,
                      ('parent.Flyer.par.Limpieza',))
    wire(flyer.op('foto'), capas, 0)
    wire(flyer.op('recorte'), capas, 1)
    wire(partido, capas, 2)

    term = glsl_pass(flyer, 'terminacion', TERMINACION, 2, RES, 900, 0, None,
                     ('parent.Flyer.par.Grano',
                      "op('titulo/animacion').module.glitch(me.time.frame)"))
    wire(capas, term, 0)
    wire(sel_titulo, term, 1)

    final = flyer.create(nullTOP, 'final')
    final.nodeX, final.nodeY = 1100, 0
    term.outputConnectors[0].connect(final)
    final.viewer = True

    grabar = flyer.create(moviefileoutTOP, 'grabar')
    grabar.nodeX, grabar.nodeY = 1300, 0
    grabar.par.file = 'ossyrave.mov'
    final.outputConnectors[0].connect(grabar)

    pe = flyer.create(parameterexecuteDAT, 'exportar')
    pe.text = EXPORT_PAREXEC
    pe.par.op = flyer.path
    pe.par.pars = 'Exportar'
    pe.par.onpulse = True
    pe.nodeX, pe.nodeY = 900, -250
    ex = flyer.create(executeDAT, 'control_grabacion')
    ex.text = EXPORT_EXEC
    ex.par.frameend = True
    ex.nodeX, ex.nodeY = 1100, -250

    if check_wiring():
        print('Flyer creado en', flyer.path)


try:
    op
except NameError:
    pass          # fuera de TouchDesigner (solo se leen los shaders)
else:
    build()
