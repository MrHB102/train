#!/usr/bin/env node
// Várias capturas numa sessão do navegador. Uso: node tools/shots.mjs <url> <config.json> [--w 900 --h 1000]
// config.json: [{ "out": "a.png", "eval": "js opcional" | "evalFile": "arquivo.js", "wait": 800 }, ...]
import { createRequire } from 'node:module';
import fs from 'node:fs';
const require = createRequire(import.meta.url);
let pw;
for (const p of ['playwright', '/opt/node22/lib/node_modules/playwright']) {
  try { pw = require(p); break; } catch {}
}
const [url, cfgPath, ...rest] = process.argv.slice(2);
const opt = (n, d) => { const i = rest.indexOf(n); return i >= 0 ? rest[i + 1] : d; };
const W = +opt('--w', 900), H = +opt('--h', 1000);
const steps = JSON.parse(fs.readFileSync(cfgPath, 'utf8'));
const browser = await pw.chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--enable-webgl', '--disable-dev-shm-usage'] });
const page = await browser.newPage({ viewport: { width: W, height: H } });
const logs = [];
page.on('console', (m) => { if (/error/i.test(m.type())) logs.push(`[${m.type()}] ${m.text()}`); });
page.on('pageerror', (e) => logs.push(`[pageerror] ${e.message}`));
await page.goto(url, { waitUntil: 'load' });
await page.waitForFunction(() => document.body.dataset.ready === '1' || document.body.dataset.error, null, { timeout: 120000 });
const err = await page.evaluate(() => document.body.dataset.error || '');
if (err) logs.push('APP ERROR: ' + err);
for (const s of steps) {
  if (s.evalFile) s.eval = fs.readFileSync(s.evalFile, 'utf8');
  if (s.eval) {
    try { const r = await page.evaluate(s.eval); if (r !== undefined) logs.push(`${s.out}: ${JSON.stringify(r)}`); } catch (e) { logs.push('eval error: ' + e.message); }
  }
  await page.waitForTimeout(s.wait ?? 700);
  await page.screenshot({ path: s.out });
}
console.log(logs.join('\n'));
await browser.close();
