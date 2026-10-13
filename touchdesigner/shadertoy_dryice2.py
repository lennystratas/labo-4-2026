# =====================================================================
#  "Dry ice 2" de David Gallardo (xjorma) en TouchDesigner
#  https://www.shadertoy.com/view/WlVyRV   (CC BY-NC-SA 3.0)
#
#  Uso: crear un Text DAT, pegar ESTE ARCHIVO COMPLETO (desde la
#  primera línea) y hacer click derecho -> Run Script.
#  Crea /project1/dryice; la imagen final sale en el Null TOP "out".
#  Reiniciar la simulación: op('/project1/dryice/reset').run()
#
#  Red: bufA (advección) -> bufB (divergencia) -> bufC (presión 1)
#       -> bufD (presión 2) ;  bufA lee bufA y bufD del frame anterior
#       (Feedback TOPs) ; image lee bufA y hace el render 3D.
# =====================================================================

RES = (1280, 720)
NAME = 'dryice'

# ------------------------------- Common ------------------------------
COMMON = r'''
const float dissipation 	= 0.95;

const float ballRadius		= 0.06;
const float fogHeigth		= ballRadius * 4.;
const int	nbSlice			= 24;
const float fogSlice		= fogHeigth / float(nbSlice);
const int	nbSphere 		= 3;
const float shadowDensity 	= 25.;
const float fogDensity 		= 20.;
const float lightHeight     = 1.;

const float tau =  radians(360.);

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

vec2 rotate(float angle, float radius)
{
    return vec2(cos(angle),-sin(angle)) * radius;
}

bool floorIntersect(in vec3 ro, in vec3 rd, in float floorHeight, out float t)
{
    ro.y -= floorHeight;
    if(rd.y < -0.01)
    {
        t = ro.y / - rd.y;
        return true;
    }
    return false;
}

vec2 sphIntersect( in vec3 ro, in vec3 rd, in vec3 ce, float ra )
{
    vec3 oc = ro - ce;
    float b = dot( oc, rd );
    float c = dot( oc, oc ) - ra*ra;
    float h = b*b - c;
    if( h<0.0 ) return vec2(-1.0);
    h = sqrt( h );
    return vec2( -b-h, -b+h );
}

vec2 boxIntersection( in vec3 ro, in vec3 rd, in vec3 rad, in vec3 center,out vec3 oN )
{
    ro -= center;
    vec3 m = 1.0/rd;
    vec3 n = m*ro;
    vec3 k = abs(m)*rad;
    vec3 t1 = -n - k;
    vec3 t2 = -n + k;
    float tN = max( max( t1.x, t1.y ), t1.z );
    float tF = min( min( t2.x, t2.y ), t2.z );
    if( tN>tF || tF<0.0) return vec2(-1.0);
    oN = -sign(rd)*step(t1.yzx,t1.xyz)*step(t1.zxy,t1.xyz);
    return vec2( tN, tF );
}

vec2 spherePosition(int id, int frame)
{
    vec4 offset = hash41(float(id)) * tau;
    float fframe = float(frame);
    return vec2(cos(offset.x + fframe * 0.015) + cos(offset.y + fframe * 0.020), cos(offset.z + fframe * 0.017) + cos(offset.w + fframe * 0.022)) * vec2(1., 0.5) * 0.9;
}

float dist2(vec3 v)
{
    return dot(v, v);
}
'''

# ------------------------- Buffer A: advección ------------------------
BUF_A = r'''
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

vec2 fbm(vec3 p, int octaveNum)
{
	vec2 acc = vec2(0);
	float freq = 1.0;
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
    vec3	veld	= texture(iChannel1, coord / iResolution.xy).xyz;
    float	left	= texture(iChannel0,(coord + vec2(-1, 0)) / iResolution.xy).x;
    float	right	= texture(iChannel0,(coord + vec2( 1, 0)) / iResolution.xy).x;
    float	bottom	= texture(iChannel0,(coord + vec2( 0,-1)) / iResolution.xy).x;
    float	top 	= texture(iChannel0,(coord + vec2( 0, 1)) / iResolution.xy).x;
    vec2	grad 	= vec2(right - left,top - bottom) * 0.5;
    return	vec3(veld.xy - grad, veld.z);
}

vec3 vignette(vec3 color, vec2 q, float v)
{
    color *= mix(1., pow(16.0 * q.x * q.y * (1.0 - q.x) * (1.0 - q.y), v), 0.02);
    return color;
}

void mainImage( out vec4 fragColor, in vec2 fragCoord )
{
    vec2	velocity = sampleMinusGradient(fragCoord).xy;
    vec3	veld = sampleMinusGradient(fragCoord - dissipation * velocity).xyz;
    float	density = veld.z;
    velocity = veld.xy;

    vec2	uv = (2. * fragCoord - iResolution.xy) / iResolution.y;
    vec2 detailNoise = fbm(vec3(uv*40., iTime * 0.5 + 30.), 7) - 0.5;
    velocity += detailNoise * 0.2;
    density += length(detailNoise) * 0.01;

    vec2 injectionNoise = fbm(vec3(uv *1.5, iTime * 0.1 + 30.), 7) - 0.5;
    velocity += injectionNoise * 0.1;
    density += max((length(injectionNoise) * 0.04), 0.);

    float influenceRadius = ballRadius * 2.;
    for(int i = 0 ; i < nbSphere ; i++)
    {
        vec2 p = spherePosition(i, iFrame);
        float dist = distance(uv, p);
        if(dist < influenceRadius)
        {
            vec2 op = spherePosition(i, iFrame + 1);
            vec2 ballVelocity = p - op;
            density -= ((influenceRadius - dist) / influenceRadius) * 0.15;
            density = max(0., density);
         	velocity -= ballVelocity * 5.;
        }
    }
    density = min(1., density);
    density *= 0.99;
    veld = vec3(vec3(velocity, density));
    veld = vignette(veld, fragCoord / iResolution.xy, 1.);
    fragColor = vec4(veld, 1);
}
'''

# ------------------------ Buffer B: divergencia -----------------------
BUF_B = r'''
void mainImage(out vec4 fragColor, in vec2 fragCoord)
{
    ivec2 icoord = ivec2(fragCoord);
    float vel_x_left	= texelFetch(iChannel0, icoord + ivec2(-1,  0) , 0).x;
    float vel_x_right	= texelFetch(iChannel0, icoord + ivec2( 1,  0) , 0).x;
    float vel_y_bottom	= texelFetch(iChannel0, icoord + ivec2( 0, -1) , 0).y;
    float vel_y_top		= texelFetch(iChannel0, icoord + ivec2( 0,  1) , 0).y;
    float divergence	= (vel_x_right - vel_x_left + vel_y_top - vel_y_bottom) * 0.5;
    fragColor = vec4(divergence,vec3(1));
}
'''


# Las sumas getDiv()/getPre() de los buffers C y D son tablas enormes que el
# autor generó con un programa en C++ (comentado en el original). Acá se
# generan igual en Python: dan exactamente los mismos coeficientes.
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

# ---------------------- Buffer C: presión (1ª iter.) ------------------
BUF_C = r'''
float div(int x,int y)
{
    return texelFetch(iChannel0, ivec2(gl_FragCoord.xy) + ivec2(x,  y) , 0).x;
}
float pre(int x,int y)
{
    return texelFetch(iChannel1, ivec2(gl_FragCoord.xy) + ivec2(x,  y) , 0).x;
}
''' + _sum_func('getDiv', 'div', _DIV) + _sum_func('getPre', 'pre', _PRE) + r'''
void mainImage( out vec4 fragColor, in vec2 C )
{
    float div = getDiv();
    float p = getPre() - div;
    fragColor = vec4(p, div, vec3(1));
}
'''

# ---------------------- Buffer D: presión (2ª iter.) ------------------
BUF_D = r'''
float div(int x,int y)
{
    return texelFetch(iChannel0, ivec2(gl_FragCoord.xy) + ivec2(x,  y) , 0).y;
}
float pre(int x,int y)
{
    return texelFetch(iChannel0, ivec2(gl_FragCoord.xy) + ivec2(x,  y) , 0).x;
}
''' + _sum_func('getPre', 'pre', _PRE) + r'''
void mainImage( out vec4 fragColor, in vec2 C )
{
    float p = getPre() - div(0,0);
    fragColor = vec4(p,vec3(1));
}
'''

# ----------------------------- Image ---------------------------------
IMAGE = r'''
float sceneIntersection(in vec3 ro,in vec3 rd, out vec3 inter, out vec3 normal, out vec3 color, in float dist, out vec3 lightPos)
{
    float mint = dist;
    inter = vec3(0);
    normal = vec3(0);
    color = vec3(0);
    for(int i = 0 ; i < nbSphere ; i++)
    {
        vec2 p2d = spherePosition(i, iFrame);
		vec3 pos = vec3(p2d.x, ballRadius, p2d.y);
        vec3 ballColor = vec3(1, 0, 0);
        if( i == 0)
        {
            ballColor = vec3(1);
            lightPos = pos + vec3(0, lightHeight, 0);
        }
        float t = sphIntersect( ro, rd, pos, ballRadius).x;
        if(t > 0. && t < mint)
        {
            mint = t;
            inter = (ro + mint * rd);
            normal = normalize(inter - pos);
            color = ballColor;
        }
    }
    {
        float aspecRatio = iResolution.x / iResolution.y;
        vec3 boxNormal;
    	float t = boxIntersection(ro, rd, vec3(aspecRatio,0.1,1), vec3(0,-0.1,0),boxNormal).x;
        if(t > 0. && t < mint)
        {
            mint = t;
            inter = (ro + mint * rd);
			normal = boxNormal;
            ivec2 tileId = ivec2(vec2(inter.x, inter.z) * 3. + 100.);
            color = ((tileId.x & 1) ^ (tileId.y & 1)) == 0 ? vec3(0.3) : vec3(0.15);
        }
    }
	return mint;
}

float sampleFog(in vec3 pos)
{
    vec2 uv = pos.xz;
    uv.x *= iResolution.y / iResolution.x;
    uv = uv * 0.5 + 0.5;
    if(max(uv.x, uv.y) > 1. || min(uv.x, uv.y) < 0.)
    {
        return 0.;
    }
    return texture(iChannel0, uv).z;
}

vec3 Render(in vec3 ro,in vec3 rd,in float dist, float fudge)
{
    vec3  inter;
    vec3  normal;
    vec3  baseColor;
    vec3  lightPos;
    float mint = sceneIntersection(ro, rd, inter, normal, baseColor, dist, lightPos);
    vec3 color = vec3(0);

    if(mint<dist)
    {
        vec3 lightDir = normalize(lightPos - inter);
        float lightDist2 = dist2(lightPos - inter);
        vec3 shadowStep = (fogHeigth / float(nbSlice)) * lightDir / lightDir.y;
        float shadowDist = 0.;
        for(int i = 0 ; i < nbSlice ; i++)
        {
            vec3 shadowPos = inter + shadowStep * float(i);
            float v = sampleFog(shadowPos) * fogHeigth;
            shadowDist += min(max(0., v - shadowPos.y), fogSlice) * length(shadowStep) / fogSlice;
        }
        float shadowFactor = exp(-shadowDist * shadowDensity * 0.25);
        color = baseColor * (max(0., dot(normal, lightDir) * shadowFactor) + 0.2) / lightDist2;
    }

	float t;
    if(floorIntersect(ro, rd, fogHeigth, t))
    {
        vec3 curPos = ro + rd * t;
        vec3 fogStep = (fogHeigth / float(nbSlice)) * rd / abs(rd.y);
        curPos += fudge * fogStep;
        float stepLen = length(fogStep);
        float curDensity = 0.;
        float transmittance = 1.;
        float lightEnergy = 0.;
        for(int i = 0; i < nbSlice; i++)
        {
            if( dot(curPos - ro, rd) > mint)
                break;
            float curHeigth = sampleFog(curPos) * fogHeigth;
            float curSample = min(max(0., curHeigth - curPos.y), fogSlice) * stepLen / fogSlice;
            if(curSample > 0.001)
            {
                vec3 lightDir = normalize(lightPos - curPos);
                vec3 shadowStep = (fogHeigth / float(nbSlice)) * lightDir / lightDir.y;
                float lightDist2 = dist2(lightPos - curPos);
                vec3 shadowPos = curPos + shadowStep * fudge;
                float shadowDist = 0.;
                for (int j = 0; j < nbSlice; j++)
                {
                    shadowPos += shadowStep;
                    if(shadowPos.y > fogHeigth)
                    {
                        break;
                    }
                    float curHeight = sampleFog(shadowPos) * fogHeigth;
             		shadowDist += min(max(0., curHeight - shadowPos.y), fogSlice) * length(shadowStep) / fogSlice;
                }
            	float shadowFactor = exp(-shadowDist * shadowDensity) / lightDist2;
                curDensity = curSample * fogDensity;
                float absorbedlight =  shadowFactor * (1. * curDensity);
                lightEnergy += absorbedlight * transmittance;
                transmittance *= 1. - curDensity;
            }
            curPos+= fogStep;
        }
        color = mix(color, vec3(lightEnergy), 1. - transmittance);
    }
    return color;
}

vec3 vignette(vec3 color, vec2 q, float v)
{
    color *= 0.3 + 0.8 * pow(16.0 * q.x * q.y * (1.0 - q.x) * (1.0 - q.y), v);
    return color;
}

mat3 setCamera( in vec3 ro, in vec3 ta )
{
	vec3 cw = normalize(ta-ro);
	vec3 up = vec3(0, 1, 0);
	vec3 cu = normalize( cross(cw,up) );
	vec3 cv = normalize( cross(cu,cw) );
    return mat3( cu, cv, cw );
}

void mainImage( out vec4 fragColor, in vec2 fragCoord )
{
    vec2 p = (-iResolution.xy + 2.0*fragCoord)/iResolution.y;
    float theta	= radians(360.)*(iMouse.x/iResolution.x-0.5) - radians(90.);
    float phi	= -radians(30.);
    vec3 ro = 2. * vec3( sin(phi)*cos(theta),cos(phi),sin(phi)*sin(theta));
    vec3 ta = vec3( 0 );
    mat3 ca = setCamera( ro, ta );
    vec3 rd =  ca*normalize(vec3(p,1.5));
    vec3 tot = Render(ro ,rd, 6., hash12(fragCoord + iTime));
	tot = vignette(tot, fragCoord / iResolution.xy, 0.6);
	fragColor = vec4( sqrt(tot), 1.0 );
}
'''

# Pasadas en orden de cálculo: (nombre, código, iChannel0..n)
# Un canal que apunta a la misma pasada o a una posterior lee el frame
# anterior (Feedback TOP), igual que en Shadertoy.
PASSES = [
    ('bufA',  BUF_A, ['bufD', 'bufA']),  # iCh0 = presión, iCh1 = velocidad/densidad
    ('bufB',  BUF_B, ['bufA']),
    ('bufC',  BUF_C, ['bufB', 'bufD']),
    ('bufD',  BUF_D, ['bufC']),
    ('image', IMAGE, ['bufA']),
]

# ---------------------------------------------------------------------
# Adaptador Shadertoy -> GLSL TOP de TouchDesigner
# ---------------------------------------------------------------------

HEADER = r'''
uniform vec4 uTime;   // x = iTime, y = iTimeDelta, z = iFrame
uniform vec4 uMouse;  // iMouse
#define iTime       uTime.x
#define iTimeDelta  uTime.y
#define iFrame      int(uTime.z)
#define iMouse      uMouse
#define iResolution vec3(uTDOutputInfo.res.zw, 1.0)
layout(location = 0) out vec4 _stOut;

// En WebGL un texelFetch fuera de la textura devuelve 0; en desktop GL
// no está definido, así que lo forzamos para que el fluido no explote.
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


def make_pass(comp, name, code, n_channels, x, is_buffer):
    defines = ''.join('#define iChannel%d sTD2DInputs[%d]\n' % (i, i)
                      for i in range(n_channels))
    dat = comp.create(textDAT, name + '_glsl')
    dat.text = HEADER + defines + COMMON + code + FOOTER
    dat.nodeX, dat.nodeY = x, 200

    top = comp.create(glslTOP, name)
    top.nodeX, top.nodeY = x, 0
    top.par.pixeldat = dat.name
    top.par.outputresolution = 'custom'
    top.par.resolutionw, top.par.resolutionh = RES
    if is_buffer:
        top.par.format = 'rgba32float'  # el fluido necesita floats con signo
    top.par.vec0name = 'uTime'
    top.par.vec0valuex.expr = "absTime.seconds - parent().fetch('t0', 0)"
    top.par.vec0valuey.expr = "absTime.stepSeconds"
    top.par.vec0valuez.expr = "absTime.frame - parent().fetch('f0', 0)"
    top.par.vec1name = 'uMouse'
    return top


def build():
    project = op('/project1')
    if project.op(NAME):
        project.op(NAME).destroy()
    comp = project.create(baseCOMP, NAME)

    order = [p[0] for p in PASSES]
    black = comp.create(constantTOP, 'black')
    black.par.outputresolution = 'custom'
    black.par.resolutionw, black.par.resolutionh = RES
    black.par.format = 'rgba32float'
    black.par.alpha = 0
    black.nodeX, black.nodeY = -300, -250

    tops, fbs = {}, {}
    for i, (name, code, chans) in enumerate(PASSES):
        tops[name] = make_pass(comp, name, code, len(chans), i * 250,
                               name != 'image')

    pulled = set()  # buffers que alguien lee en el mismo frame
    for name, code, chans in PASSES:
        for i, src in enumerate(chans):
            if order.index(src) >= order.index(name):   # frame anterior
                if src not in fbs:
                    fb = comp.create(feedbackTOP, 'fb_' + src)
                    fb.nodeX, fb.nodeY = order.index(src) * 250, -250
                    black.outputConnectors[0].connect(fb)
                    fb.par.top = src
                    fbs[src] = fb
                node = fbs[src]
            else:
                node = tops[src]
                pulled.add(src)
            node.outputConnectors[0].connect(tops[name].inputConnectors[i])

    # Los buffers que solo se leen vía feedback (bufD) los conectamos como
    # entradas extra (no usadas) de image para que se calculen cada frame.
    image = tops['image']
    for name in order[:-1]:
        if name not in pulled:
            tops[name].outputConnectors[0].connect(
                image.inputConnectors[len(image.inputs)])

    out = comp.create(nullTOP, 'out')
    out.nodeX, out.nodeY = image.nodeX + 250, 0
    image.outputConnectors[0].connect(out)
    out.viewer = True

    reset = comp.create(textDAT, 'reset')
    reset.nodeX, reset.nodeY = -300, 200
    reset.text = (
        "parent().store('t0', absTime.seconds)\n"
        "parent().store('f0', absTime.frame)\n"
        "for fb in parent().findChildren(type=feedbackTOP):\n"
        "    fb.par.resetpulse.pulse()\n")
    reset.run()
    print('Dry ice 2 creado en', comp.path)


build()
