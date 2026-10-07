#!/usr/bin/env node
// Empacota o build (dist/) como artefato: um fragmento HTML (título, CSS inline, marcação e <script type=module>)
// mais os arquivos de apoio (bundle JS e dados do corpo). Uso: node tools/pack-artifact.mjs [saida_dir]
import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const dist = path.join(root, 'dist');
const out = process.argv[2] || path.join(root, 'artifact');
fs.mkdirSync(out, { recursive: true });

const css = fs.readFileSync(path.join(dist, 'assets', 'index.css'), 'utf8');
const html = `<title>Avatar Studio</title>
<style>
${css}
.loading { position: fixed; inset: 0; z-index: 60; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 16px; background: radial-gradient(circle at 50% 40%, #121b33, #05070c); color: #8f9cc0; }
.loading b { letter-spacing: 0.22em; color: #e8eeff; font-weight: 600; }
</style>
<div id="app"></div>
<div id="loading" class="loading"><b>AVATAR STUDIO</b><div class="bar"><i></i></div><div>carregando o corpo…</div></div>
<script>window.__AVATAR_B64 = 1;</script>
<script type="module" src="assets/app.js"></script>
`;
fs.writeFileSync(path.join(out, 'index.html'), html);
// binários em base64 (.txt): o visualizador de artefatos só serve texto/imagens/mídia
fs.mkdirSync(path.join(out, 'data'), { recursive: true });
for (const f of ['body.bin.gz', 'targets.bin.gz']) {
  fs.writeFileSync(path.join(out, 'data', f + '.b64.txt'), fs.readFileSync(path.join(dist, 'data', f)).toString('base64'));
}
fs.mkdirSync(path.join(out, 'assets'), { recursive: true });
fs.copyFileSync(path.join(dist, 'assets', 'app.js'), path.join(out, 'assets', 'app.js'));
fs.copyFileSync(path.join(dist, 'data', 'body.json'), path.join(out, 'data', 'body.json'));
fs.copyFileSync(path.join(dist, 'data', 'targets.json'), path.join(out, 'data', 'targets.json'));
const files = {
  'assets/app.js': path.join(out, 'assets', 'app.js'),
  'data/body.json': path.join(out, 'data', 'body.json'),
  'data/targets.json': path.join(out, 'data', 'targets.json'),
  'data/body.bin.gz.b64.txt': path.join(out, 'data', 'body.bin.gz.b64.txt'),
  'data/targets.bin.gz.b64.txt': path.join(out, 'data', 'targets.bin.gz.b64.txt'),
};
fs.writeFileSync(path.join(out, 'files.json'), JSON.stringify(files, null, 2));
let total = Buffer.byteLength(html);
for (const f of Object.values(files)) total += fs.statSync(f).size;
console.log(`artefato: ${out}/index.html + ${Object.keys(files).length} arquivos, ${(total / 1024 / 1024).toFixed(2)} MB`);
