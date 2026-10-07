#!/usr/bin/env node
// Captura de tela headless (Chromium + SwiftShader) para iterar no visual sem GPU.
// Uso: node tools/screenshot.mjs <url> <saida.png> [--w 1280] [--h 900] [--eval "js"] [--wait 1500] [--log]
import { createRequire } from 'node:module';
import fs from 'node:fs';

const require = createRequire(import.meta.url);
let pw;
for (const p of ['playwright', '/opt/node22/lib/node_modules/playwright']) {
  try {
    pw = require(p);
    break;
  } catch {}
}
if (!pw) throw new Error('playwright não encontrado');

const args = process.argv.slice(2);
const url = args[0];
const out = args[1];
const opt = (n, d) => {
  const i = args.indexOf(n);
  return i >= 0 ? args[i + 1] : d;
};
const W = +opt('--w', 1280);
const H = +opt('--h', 900);
const wait = +opt('--wait', 1500);
const evalJs = opt('--eval', '');
const showLog = args.includes('--log');

const browser = await pw.chromium.launch({
  args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--enable-webgl', '--disable-dev-shm-usage'],
});
const page = await browser.newPage({ viewport: { width: W, height: H } });
const logs = [];
page.on('console', (m) => logs.push(`[${m.type()}] ${m.text()}`));
page.on('pageerror', (e) => logs.push(`[pageerror] ${e.message}\n${(e.stack || '').split('\n').slice(0, 6).join('\n')}`));
await page.goto(url, { waitUntil: 'load' });
try {
  await page.waitForFunction(() => document.body.dataset.ready === '1' || document.body.dataset.error, null, { timeout: 90000 });
} catch (e) {
  logs.push('timeout aguardando ready');
}
const err = await page.evaluate(() => document.body.dataset.error || '');
if (err) logs.push('APP ERROR: ' + err);
if (evalJs) {
  try {
    const r = await page.evaluate(evalJs);
    if (r !== undefined) logs.push('eval => ' + JSON.stringify(r));
  } catch (e) {
    logs.push('eval error: ' + e.message);
  }
}
await page.waitForTimeout(wait);
fs.mkdirSync(new URL('.', import.meta.url).pathname, { recursive: true });
await page.screenshot({ path: out });
if (showLog || err) console.log(logs.join('\n'));
else console.log(logs.filter((l) => /error|warn/i.test(l)).join('\n'));
await browser.close();
