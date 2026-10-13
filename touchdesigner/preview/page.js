// Corre las pasadas del flyer en WebGL2 imitando la red de TouchDesigner.
window.setup = async function (cfg) {
  const D = cfg.data;
  const W = Math.round(D.RES[0] * cfg.outScale), H = Math.round(D.RES[1] * cfg.outScale);
  const SW = Math.round(D.SIM[0] * cfg.simScale), SH = Math.round(D.SIM[1] * cfg.simScale);
  const canvas = document.createElement('canvas'); canvas.width = W; canvas.height = H;
  const gl = canvas.getContext('webgl2', {premultipliedAlpha: false, preserveDrawingBuffer: true});
  if (!gl.getExtension('EXT_color_buffer_float')) throw 'no float rt';
  gl.getExtension('OES_texture_float_linear');
  const vs = `#version 300 es\nin vec2 p; void main(){ gl_Position = vec4(p,0,1); }`;
  function sh(type, src) { const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw gl.getShaderInfoLog(s); return s; }
  const progs = {};
  for (const [n, src] of Object.entries(D.passes)) {
    const p = gl.createProgram(); gl.attachShader(p, sh(gl.VERTEX_SHADER, vs)); gl.attachShader(p, sh(gl.FRAGMENT_SHADER, src));
    gl.bindAttribLocation(p, 0, 'p'); gl.linkProgram(p);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw n + gl.getProgramInfoLog(p);
    progs[n] = p;
  }
  const buf = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, buf);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,-1, 3,-1, -1,3]), gl.STATIC_DRAW);
  gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);

  function tex(w, h, float) {
    const t = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, t);
    gl.texImage2D(gl.TEXTURE_2D, 0, float ? gl.RGBA32F : gl.RGBA8, w, h, 0, gl.RGBA, float ? gl.FLOAT : gl.UNSIGNED_BYTE, null);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    const fb = gl.createFramebuffer(); gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, t, 0);
    return {t, fb, w, h};
  }
  function upload(target, src) {
    gl.bindTexture(gl.TEXTURE_2D, target.t);
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true); gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, true);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, gl.RGBA, gl.UNSIGNED_BYTE, src);
  }
  async function img(url) { const im = new Image(); im.src = url; await im.decode(); return im; }
  const foto = tex(1,1), recorte = tex(1,1), prof = tex(1,1), logoT = tex(1,1);
  upload(foto, await img(cfg.foto)); upload(recorte, await img(cfg.recorte)); upload(prof, await img(cfg.prof)); upload(logoT, await img(cfg.logo));
  const black = tex(SW, SH, true);
  let A = [tex(SW, SH, true), tex(SW, SH, true)], Dd = [tex(SW, SH, true), tex(SW, SH, true)];
  let M = [tex(SW, SH), tex(SW, SH)];
  const Bt = tex(SW, SH, true), Ct = tex(SW, SH, true), humo = tex(W, H), comp = tex(W, H), title = tex(W, H), partido = tex(W, H, true), capas = tex(W, H), fondoT = tex(W, H), diffT = tex(W, H);
  const tc = document.createElement('canvas'); tc.width = W; tc.height = H;
  const mc = document.createElement('canvas'); mc.width = SW; mc.height = SH;

  function drawLetters(ctx, w, h, frame, blurPx) {
    ctx.setTransform(1,0,0,1,0,0); ctx.clearRect(0,0,w,h); ctx.filter = blurPx ? `blur(${blurPx}px)` : 'none';
    ctx.font = `900 ${cfg.fontSize * w / D.RES[0]}px Inter`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    D.letters[frame - 1].forEach((L, i) => {
      ctx.setTransform(1,0,0,1,0,0);
      ctx.translate((0.5 + L.x) * w, h - (0.5 + L.y) * h); ctx.rotate(-L.rot * Math.PI / 180); ctx.scale(L.escala_x, L.escala_y);
      ctx.fillStyle = `rgba(255,255,255,${L.opacidad})`; ctx.fillText(D.text[i], 0, 0);
    });
  }
  function run(prog, out, inputs, P, X) {
    const p = progs[prog]; gl.useProgram(p);
    gl.bindFramebuffer(gl.FRAMEBUFFER, out.fb); gl.viewport(0, 0, out.w, out.h);
    for (let i = 0; i < 5; i++) { gl.activeTexture(gl.TEXTURE0 + i); gl.bindTexture(gl.TEXTURE_2D, (inputs[i] || black).t); }
    gl.uniform1iv(gl.getUniformLocation(p, 'sTD2DInputs'), [0,1,2,3,4]);
    gl.uniform4f(gl.getUniformLocation(p, 'uTDOutputInfo.res'), 1/out.w, 1/out.h, out.w, out.h);
    const f = window.frame - 1;
    gl.uniform4f(gl.getUniformLocation(p, 'uTime'), f / D.fps, 1 / D.fps, f, 0);
    gl.uniform4f(gl.getUniformLocation(p, 'uP'), ...(P || [0,0,0,0]));
    const lx = gl.getUniformLocation(p, 'uLogo'); if (lx && X) gl.uniform4f(lx, ...X);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
  }
  window.frame = 1;
  window.step = function () {
    const fr = window.frame, first = fr === 1;
    drawLetters(mc.getContext("2d"), SW, SH, fr, 5 * cfg.simScale); upload(M[0], mc);
    const prevA = first ? black : A[1], prevD = first ? black : Dd[1], prevM = first ? black : M[1];
    const P = cfg.P;
    run('sim_a', A[0], [prevD, prevA, M[0]], [P.Densidad, P.Empuje, P.Subida, 0]);
    run('sim_b', Bt, [A[0]]);
    run('sim_c', Ct, [Bt, prevD]);
    run('sim_d', Dd[0], [Ct]);
    A.reverse(); Dd.reverse(); M.reverse();   // [1] = este frame
    window.frame++;
  };
  window.renderOut = function () {
    const fr = window.frame - 1, P = cfg.P;
    const save = window.frame; window.frame = fr;
    run('humo', humo, [A[1], Dd[1]], [P.Brillo, 0, 0, 0]);
    drawLetters(tc.getContext('2d'), W, H, fr, 0); upload(title, tc);
    run('partido', partido, [humo, prof, recorte], [P.Corte, 0, 0, 0]);
    run('capas', capas, [foto, recorte, partido], [P.Limpieza, 0, 0, 0]);
    const Lg = D.logo[fr - 1];
    run('fondo', fondoT, [capas, logoT], [0, 0, 0, 0], [Lg.opacidad, Lg.tamano, Lg.y, 0]);
    run('diff', diffT, [fondoT, title]);
    run('term', comp, [diffT], [P.Grano, 0, 0, 0]);
    window.frame = save;
    const px = new Uint8Array(W * H * 4); gl.bindFramebuffer(gl.FRAMEBUFFER, comp.fb); gl.readPixels(0, 0, W, H, gl.RGBA, gl.UNSIGNED_BYTE, px);
    const oc = document.createElement('canvas'); oc.width = W; oc.height = H; const ctx = oc.getContext('2d');
    const id = ctx.createImageData(W, H);
    for (let y = 0; y < H; y++) id.data.set(px.subarray((H - 1 - y) * W * 4, (H - y) * W * 4), y * W * 4);
    ctx.putImageData(id, 0, 0); return oc.toDataURL('image/png');
  };
  return {W, H, SW, SH};
};
