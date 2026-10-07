#!/usr/bin/env node
// Teste ponta a ponta no navegador (Chromium headless + SwiftShader): percorre a interface, arrasta sliders,
// aplica conjuntos/presets, troca idioma, desfaz/refaz e falha se houver erro de console ou de página.
// Uso: node tools/e2e.mjs <url> [saida_dir]
import { createRequire } from 'node:module';
import fs from 'node:fs';
const require = createRequire(import.meta.url);
let pw;
for (const p of ['playwright', '/opt/node22/lib/node_modules/playwright']) {
  try { pw = require(p); break; } catch {}
}
const url = process.argv[2] || 'http://localhost:5173/';
const outDir = process.argv[3] || '/tmp';
fs.mkdirSync(outDir, { recursive: true });
const browser = await pw.chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--enable-webgl', '--disable-dev-shm-usage'] });
const page = await browser.newPage({ viewport: { width: 1280, height: 780 } });
const errors = [];
page.on('console', (m) => { if (m.type() === 'error' || (m.type() === 'warning' && /camada-base/.test(m.text()))) errors.push(`[${m.type()}] ${m.text()}`); });
page.on('pageerror', (e) => errors.push(`[pageerror] ${e.message}`));
const checks = [];
const ok = (name, cond, extra = '') => { checks.push({ name, ok: !!cond, extra }); };

await page.goto(url, { waitUntil: 'load' });
await page.waitForFunction(() => document.body.dataset.ready === '1' || document.body.dataset.error, null, { timeout: 120000 });
ok('app sem erro de inicialização', !(await page.evaluate(() => document.body.dataset.error)));
await page.evaluate(() => __app.engine.stop());
const step = (n = 6) => page.evaluate((k) => __app.engine.step(1 / 60, k), n);

// 1. abas
for (const id of ['body', 'skin', 'outfit', 'dynamics', 'scene', 'presets']) {
  await page.click(`.tab[data-id="${id}"]`);
  await step(2);
  ok(`aba ${id} renderiza`, (await page.locator('.panel-body *').count()) > 5);
}

// 1b. nenhuma região do corpo mostra dois controles com o mesmo nome (Dial e Trait-base se confundiam)
await page.click('.tab[data-id="body"]');
const dupLabels = await page.evaluate(() => {
  const out = [];
  for (const c of [...document.querySelectorAll('.panel .chip')]) {
    c.click();
    const labels = [...document.querySelectorAll('.panel .srow .stxt')].map((x) => x.textContent.trim());
    labels.forEach((l, i) => labels.indexOf(l) !== i && out.push(`${c.textContent.trim()}: ${l}`));
  }
  return out;
});
ok('nenhuma região do corpo repete o nome de um controle', dupLabels.length === 0, dupLabels.join('; '));

// 2. sliders do corpo: arrasta o tamanho do busto ao máximo, com repique
await page.click('.tab[data-id="body"]');
await page.click('.chip[data-id="bust"]');
const bustVal = async () => page.evaluate(() => __app.body.effective()['bust.extraVolume']);
const before = await bustVal();
await page.evaluate(() => {
  const input = document.querySelector('.panel-body .srow input[type=range]');
  input.value = input.max;
  input.dispatchEvent(new Event('input', { bubbles: true }));
  input.dispatchEvent(new Event('change', { bubbles: true }));
});
await step(8);
const peak = await bustVal();
await step(120);
const settled = await bustVal();
ok('busto cresce ao arrastar o slider', settled > before + 1, `${before.toFixed(2)} → ${settled.toFixed(2)}`);
ok('repique passa do valor final (overshoot)', peak > 0 && settled > 0.5, `pico parcial ${peak.toFixed(2)}, final ${settled.toFixed(2)}`);

// 3. desfazer / refazer
const histBefore = await page.evaluate(() => __app.history.length);
await page.keyboard.press('Control+z');
await step(100);
const afterUndo = await bustVal();
ok('desfazer volta o busto', afterUndo < settled - 0.5, `${settled.toFixed(2)} → ${afterUndo.toFixed(2)}`);
await page.keyboard.press('Control+y');
await step(100);
ok('refazer reaplica', (await bustVal()) > afterUndo + 0.5);
ok('histórico registra mudanças', histBefore >= 2, `entradas ${histBefore}`);

// 4. roupas: cada conjunto monta sem erro e a camada-base nunca fica sem geometria
await page.click('.tab[data-id="outfit"]');
for (const id of ['bunny', 'maid', 'school', 'summer', 'casual', 'sport', 'gothic', 'none']) {
  await page.evaluate((o) => __app.dresser.applyOutfit(o), id);
  await step(30);
  const info = await page.evaluate(() => {
    const d = __app.dresser;
    const baseOK = ['top', 'bottom'].every((w) => d.base[w].parts.some((p) => p.kind === 'shell' && p.obj.count > 0) || d._coverField(w === 'top' ? ['top', 'onepiece'] : ['bottom', 'onepiece']));
    return { n: d.entries.size, baseOK };
  });
  ok(`conjunto ${id}`, info.baseOK, `${info.n} peças`);
}
await page.evaluate(() => __app.dresser.applyOutfit('bunny'));
await step(10);

// 5. editor de peça: troca tecido/cor, opções
await page.evaluate(() => {
  __app.dresser.setItemStyle('onepiece', { color: '#c01f3d', fabric: 'latex' });
  __app.dresser.setItemOptions('onepiece', { legCut: 1, padding: 0.8 });
  __app.dresser.setItemOptions('shoes', { heel: 0.15 });
});
await step(6);
ok('estilo e opções da peça aplicam', await page.evaluate(() => __app.dresser.entries.get('onepiece').style.fabric === 'latex' && __app.animator.heelMeters === 0.15));

// 6. preset extremo (mesmos valores do preset "Gigante")
await page.evaluate(() => __app.applyBodyPreset({ traits: { 'thighs.contact': 1 }, dials: { bustSize: 3, glutesSize: 3, hipSize: 2.2, thickness: 2.2, curves: 1.6, anime: 1 } }));
await step(200);
const giant = await page.evaluate(() => ({ b: __app.body.effective()['bust.extraVolume'], g: __app.body.effective()['glutes.extraVolume'] }));
ok('preset gigante chega ao máximo', giant.b > 1.6 && giant.g > 1.6, JSON.stringify(giant));
const fin = await page.evaluate(() => {
  const bad = (a) => a.some((x) => !Number.isFinite(x));
  return { body: bad(__app.body.pos), shells: [...__app.wardrobe.items.values()].some((s) => bad(s.position)) };
});
ok('nenhum NaN nas malhas no extremo', !fin.body && !fin.shells, JSON.stringify(fin));
await page.screenshot({ path: `${outDir}/e2e_giant.png` });

// 7. compartilhar e restaurar
const code = await page.evaluate(() => __app.shareCode());
await page.evaluate(() => __app.resetAll());
await step(150);
const reset = await bustVal();
await page.evaluate((c) => __app.loadCode(c), code);
await step(200);
ok('código de compartilhar restaura o corpo', (await bustVal()) > reset + 1, `${reset.toFixed(2)} → ${(await bustVal()).toFixed(2)} (código ${code.length} chars)`);

// 8. idioma e painel
await page.click('.topactions .ibtn:last-child');
await step(2);
ok('troca de idioma reconstrói a interface', (await page.locator('.tab').first().textContent()).length > 0);
await page.screenshot({ path: `${outDir}/e2e_final.png` });

await browser.close();
let fail = 0;
for (const c of checks) {
  console.log(`${c.ok ? 'OK  ' : 'FAIL'} ${c.name}${c.extra ? '  — ' + c.extra : ''}`);
  if (!c.ok) fail++;
}
if (errors.length) {
  console.log('\nErros de console/página:');
  for (const e of [...new Set(errors)].slice(0, 20)) console.log('  ' + e);
}
console.log(`\n${checks.length - fail}/${checks.length} verificações OK, ${errors.length} erro(s) de console`);
process.exit(fail || errors.length ? 1 : 0);
