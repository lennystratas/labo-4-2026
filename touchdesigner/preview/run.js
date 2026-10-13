// Uso: node run.js passes.json <carpeta_salida> <frames,separados,por,coma> <simScale> <outScale> '<json params>' <carpeta_imagenes>
let chromium;
try { ({ chromium } = require('playwright')); } catch (e) { ({ chromium } = require('/opt/node-tools/node_modules/playwright')); }
const fs = require('fs'), path = require('path');
const [,, dataPath, outDir, framesArg, simScale, outScale, paramsJson, imgDir] = process.argv;
const shots = framesArg.split(',').map(Number), last = Math.max(...shots);
(async () => {
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage();
  page.on('console', m => console.log('page:', m.text()));
  await page.setContent('<html><body></body></html>');
  await page.addScriptTag({ path: path.join(__dirname, 'page.js') });
  const F = imgDir || path.join(__dirname, '..', 'flyer');
  const durl = (f, t) => `data:${t};base64,` + fs.readFileSync(path.join(F, f)).toString('base64');
  const P = Object.assign({ Subida: 1, Densidad: 1, Empuje: 1, Brillo: 1, Corte: 0.38, Limpieza: 1, Grano: 0.04 }, JSON.parse(paramsJson || '{}'));
  const info = await page.evaluate(async cfg => await window.setup(cfg), {
    data: JSON.parse(fs.readFileSync(dataPath)), simScale: +simScale, outScale: +outScale, fontSize: 125, P,
    foto: durl('foto.jpg', 'image/jpeg'), recorte: durl('recorte.png', 'image/png'), prof: durl('profundidad.png', 'image/png'), logo: durl('logo.png', 'image/png') });
  console.log('setup', JSON.stringify(info));
  fs.mkdirSync(outDir, { recursive: true });
  const t0 = Date.now();
  for (let f = 1; f <= last; f++) {
    await page.evaluate(() => window.step());
    if (shots.includes(f)) {
      const url = await page.evaluate(() => window.renderOut());
      fs.writeFileSync(path.join(outDir, `f${String(f).padStart(4, '0')}.png`), Buffer.from(url.split(',')[1], 'base64'));
      console.log('frame', f, ((Date.now() - t0) / 1000).toFixed(1) + 's');
    }
  }
  await browser.close();
})().catch(e => { console.error('ERR', e); process.exit(1); });
