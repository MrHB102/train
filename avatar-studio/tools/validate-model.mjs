#!/usr/bin/env node
// Validação do modelo (princípios da skill 3d-modeling): unidades/orientação, topologia, normais,
// pesos de skinning, simetria e orçamento de polígonos. Falha (exit 1) se algo estiver fora do padrão.
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { fileURLToPath } from 'node:url';
import { parsePackage } from '../src/avatar/package.js';
import { MorphEngine } from '../src/avatar/morph.js';
import { neutralValues } from '../src/domain/traits.js';

const dir = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'public', 'data');
const rd = (f) => fs.readFileSync(path.join(dir, f));
const ab = (b) => b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength);
const pkg = parsePackage(JSON.parse(rd('body.json')), JSON.parse(rd('targets.json')), ab(zlib.gunzipSync(rd('body.bin.gz'))), ab(zlib.gunzipSync(rd('targets.bin.gz'))));

const results = [];
const check = (name, ok, detail = '') => {
  results.push({ name, ok, detail });
  console.log(`${ok ? 'OK  ' : 'FALHA'}  ${name}${detail ? ' — ' + detail : ''}`);
};

// ---- estado neutro
const morph = new MorphEngine(pkg);
const P = morph.update(neutralValues());
const N = pkg.meta.vertCount;
const pos = new Float32Array(N * 3);
for (let k = 0; k < N; k++) {
  let x = 0, y = 0, z = 0;
  for (let q = pkg.stencilStart[k]; q < pkg.stencilStart[k + 1]; q++) {
    const j = pkg.stencilIdx[q] * 3, w = pkg.stencilW[q];
    x += P[j] * w; y += P[j + 1] * w; z += P[j + 2] * w;
  }
  pos[k * 3] = x; pos[k * 3 + 1] = y; pos[k * 3 + 2] = z;
}
const I = pkg.indices;
const T = I.length / 3;

// ---- 1. unidades e orientação (aplicar escala/rotação antes do export)
let minY = Infinity, maxY = -Infinity, minX = Infinity, maxX = -Infinity;
for (let k = 0; k < N; k++) {
  minY = Math.min(minY, pos[k * 3 + 1]); maxY = Math.max(maxY, pos[k * 3 + 1]);
  minX = Math.min(minX, pos[k * 3]); maxX = Math.max(maxX, pos[k * 3]);
}
check('unidades em metros (altura do corpo 1.2–1.7 m)', maxY - minY > 1.2 && maxY - minY < 1.7, `${(maxY - minY).toFixed(3)} m`);
check('centrado em X (simétrico)', Math.abs((minX + maxX) / 2) < 0.01, `centro x = ${((minX + maxX) / 2).toFixed(4)}`);
const zAt = (y0, y1, pick) => {
  let r = pick === 'max' ? -Infinity : Infinity;
  for (let k = 0; k < N; k++) {
    const y = pos[k * 3 + 1] - minY;
    if (y >= y0 && y < y1 && Math.abs(pos[k * 3]) < 0.2) r = pick === 'max' ? Math.max(r, pos[k * 3 + 2]) : Math.min(r, pos[k * 3 + 2]);
  }
  return r;
};
check('frente = +Z (busto à frente, glúteos atrás)', zAt(1.05, 1.2, 'max') > 0.1 && zAt(0.75, 0.9, 'min') < -0.05, `busto z=${zAt(1.05, 1.2, 'max').toFixed(3)} glúteos z=${zAt(0.75, 0.9, 'min').toFixed(3)}`);

// ---- 2. topologia
check('orçamento de triângulos (≤ 60 000, malha subdividida)', T <= 60000, `${T} triângulos, ${N} vértices`);
let degenerate = 0, sliver = 0, minAngle = 180;
const edgeUse = new Map();
const ekey = (a, b) => (a < b ? a * 65536 + b : b * 65536 + a);
for (let t = 0; t < T; t++) {
  const ia = I[t * 3], ib = I[t * 3 + 1], ic = I[t * 3 + 2];
  const v = [ia, ib, ic].map((i) => [pos[i * 3], pos[i * 3 + 1], pos[i * 3 + 2]]);
  const e = [[v[1], v[0]], [v[2], v[1]], [v[0], v[2]]].map(([p, q]) => [p[0] - q[0], p[1] - q[1], p[2] - q[2]]);
  const len = e.map((x) => Math.hypot(x[0], x[1], x[2]));
  const cr = [e[0][1] * e[1][2] - e[0][2] * e[1][1], e[0][2] * e[1][0] - e[0][0] * e[1][2], e[0][0] * e[1][1] - e[0][1] * e[1][0]];
  const area = 0.5 * Math.hypot(cr[0], cr[1], cr[2]);
  if (area < 1e-9) degenerate++;
  for (let c = 0; c < 3; c++) {
    const a = len[c], b = len[(c + 1) % 3], cc = len[(c + 2) % 3];
    if (a * b > 0) {
      const ang = (Math.acos(Math.max(-1, Math.min(1, (a * a + b * b - cc * cc) / (2 * a * b)))) * 180) / Math.PI;
      minAngle = Math.min(minAngle, ang);
      if (ang < 1) sliver++;
    }
  }
  for (const [a, b] of [[ia, ib], [ib, ic], [ic, ia]]) edgeUse.set(ekey(a, b), (edgeUse.get(ekey(a, b)) || 0) + 1);
}
check('sem triângulos degenerados', degenerate === 0, `${degenerate}`);
check('sem triângulos-lasca (ângulo < 1°)', sliver === 0, `${sliver} cantos, menor ângulo ${minAngle.toFixed(2)}°`);
let nonManifold = 0, boundary = 0;
for (const c of edgeUse.values()) {
  if (c > 2) nonManifold++;
  if (c === 1) boundary++;
}
check('sem arestas non-manifold', nonManifold === 0, `${nonManifold}`);
check('3 laços de borda (pescoço + 2 ombros) = Cuts', pkg.meta.loops.length === 3, `${pkg.meta.loops.length} laços, ${boundary} arestas de borda`);
const referenced = new Uint8Array(N);
for (let i = 0; i < I.length; i++) referenced[I[i]] = 1;
check('sem vértices órfãos', referenced.every((x) => x), '');

// ---- 3. orientação dos triângulos / normais (battle scar: normais invertidas)
const dirUse = new Map();
let sameDir = 0;
for (let t = 0; t < T; t++) {
  for (const [a, b] of [[I[t * 3], I[t * 3 + 1]], [I[t * 3 + 1], I[t * 3 + 2]], [I[t * 3 + 2], I[t * 3]]]) {
    const k = a * 65536 + b;
    const c = (dirUse.get(k) || 0) + 1;
    dirUse.set(k, c);
    if (c > 1) sameDir++;
  }
}
check('winding consistente (nenhuma aresta usada duas vezes no mesmo sentido)', sameDir === 0, `${sameDir}`);
// volume com sinal do sólido fechado = malha + tampas em leque; positivo => normais para fora
let vol = 0;
const tet = (a, b, c) => (a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0]) + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6;
const pv = (i) => [pos[i * 3], pos[i * 3 + 1], pos[i * 3 + 2]];
for (let t = 0; t < T; t++) vol += tet(pv(I[t * 3]), pv(I[t * 3 + 1]), pv(I[t * 3 + 2]));
for (const loop of pkg.meta.loops) {
  const c = [0, 0, 0];
  for (const v of loop) for (let k = 0; k < 3; k++) c[k] += pos[v * 3 + k] / loop.length;
  for (let i = 0; i < loop.length; i++) vol += tet(pv(loop[(i + 1) % loop.length]), pv(loop[i]), c);
}
check('normais para fora (volume com sinal > 0)', vol > 0, `${(vol * 1000).toFixed(1)} L`);

// ---- 4. pesos
let sumBad = 0, maxInfl = 0, badBone = 0;
const boneCount = pkg.meta.bones.length;
for (let k = 0; k < N; k++) {
  let s = 0, inf = 0;
  for (let j = 0; j < 4; j++) {
    s += pkg.skinWeight[k * 4 + j];
    if (pkg.skinWeight[k * 4 + j]) {
      inf++;
      if (pkg.skinIndex[k * 4 + j] >= boneCount) badBone++;
    }
  }
  if (s !== 255) sumBad++;
  maxInfl = Math.max(maxInfl, inf);
}
check('pesos somam 1 em todos os vértices', sumBad === 0, `${sumBad} fora`);
check('no máximo 4 influências, índices de osso válidos', maxInfl <= 4 && badBone === 0, `${boneCount} ossos`);

// ---- 4b. stencils somam 1
let stencilBad = 0;
for (let k = 0; k < N; k++) {
  let t = 0;
  for (let q = pkg.stencilStart[k]; q < pkg.stencilStart[k + 1]; q++) t += pkg.stencilW[q];
  if (Math.abs(t - 1) > 1e-3) stencilBad++;
}
check('stencils de posição somam 1 (partição da unidade)', stencilBad === 0, `${stencilBad} fora`);

// ---- 5. simetria L/R
const cell = new Map();
const q = (v) => Math.round(v * 2000);
for (let k = 0; k < N; k++) cell.set(`${q(pos[k * 3])}|${q(pos[k * 3 + 1])}|${q(pos[k * 3 + 2])}`, k);
let matched = 0;
for (let k = 0; k < N; k++) if (cell.has(`${q(-pos[k * 3])}|${q(pos[k * 3 + 1])}|${q(pos[k * 3 + 2])}`)) matched++;
check('simetria esquerda/direita (≥ 97% dos vértices com par espelhado a 0.5 mm)', matched / N >= 0.97, `${((100 * matched) / N).toFixed(1)}%`);

const bad = results.filter((r) => !r.ok);
console.log(`\n${results.length - bad.length}/${results.length} verificações ok`);
process.exit(bad.length ? 1 : 0);
