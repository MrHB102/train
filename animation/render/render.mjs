// Frame renderer driver: node render.mjs --shot shot.json --out frames_dir [--from 0 --to 630 --step 1 --scale 1 --list 10,20,30]
// Serves the static renderer, opens it in headless Chromium (WebGL2 via SwiftShader) and writes PNG frames.
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const args = Object.fromEntries(process.argv.slice(2).reduce((a, x, i, arr) => { if (x.startsWith('--')) a.push([x.slice(2), arr[i + 1] && !arr[i + 1].startsWith('--') ? arr[i + 1] : true]); return a; }, []));
const shotPath = path.resolve(args.shot || '../out/shot.json'); const outDir = path.resolve(args.out || '../out/frames');
const scale = parseFloat(args.scale || '1'); const step = parseInt(args.step || '1'); const exposure = parseFloat(args.exposure || '1');
fs.mkdirSync(outDir, { recursive: true });

const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json', '.png': 'image/png' };
const server = http.createServer((req, res) => {
  const u = decodeURIComponent(req.url.split('?')[0]);
  const file = u === '/shot.json' ? shotPath : path.join(here, u === '/' ? 'index.html' : u);
  if (!file.startsWith(here) && file !== shotPath) { res.writeHead(403); return res.end(); }
  fs.readFile(file, (err, data) => { if (err) { res.writeHead(404); return res.end('nf'); } res.writeHead(200, { 'Content-Type': MIME[path.extname(file)] || 'application/octet-stream' }); res.end(data); });
}).listen(0);
await new Promise(r => server.on('listening', r));
const port = server.address().port;

const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--enable-webgl', '--disable-dev-shm-usage'] });
const page = await browser.newPage({ viewport: { width: 640, height: 480 } });
page.on('console', m => { const t = m.text(); if (!t.includes('GPU stall')) console.log('[page]', t); });
page.on('pageerror', e => console.log('[pageerror]', e.message));
await page.goto(`http://127.0.0.1:${port}/index.html`);
const info = await page.evaluate(async ([scale, exposure]) => await window.initStage('/shot.json', { scale, exposure }), [scale, exposure]);
const from = parseInt(args.from || '0'), to = Math.min(parseInt(args.to || String(info.frames)), info.frames);
const list = args.list ? String(args.list).split(',').map(Number) : null;
const todo = list || Array.from({ length: Math.ceil((to - from) / step) }, (_, i) => from + i * step);
const t0 = Date.now(); let n = 0;
for (const f of todo) {
  const url = await page.evaluate(i => window.renderFrame(i), f);
  fs.writeFileSync(path.join(outDir, `f${String(f).padStart(4, '0')}.png`), Buffer.from(url.split(',')[1], 'base64'));
  n++; if (n % 10 === 0 || n === todo.length) console.log(`rendered ${n}/${todo.length}  ${((Date.now() - t0) / n / 1000).toFixed(2)}s/frame  ${info.w}x${info.h}`);
}
await browser.close(); server.close();
