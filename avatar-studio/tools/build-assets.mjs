#!/usr/bin/env node
// Conversor de assets: MakeHuman (CC0) -> pacote binário para o navegador.
//
// Gera o corpo feminino SEM CABEÇA E SEM BRAÇOS (torso + pernas, estilo manequim):
//  1. subdivide a malha base com Catmull-Clark (1 nível) -> pele lisa; cada vértice novo é um *stencil*
//     (combinação linear dos vértices base), então todo morph target herda a suavização;
//  2. corta a malha subdividida por planos no pescoço e nos ombros (ADR 0003): triângulos recortados,
//     vértices novos nascem em arestas e também viram stencils (acompanham morphs, poses e Jiggle);
//  3. pesos de skinning (top-4) remapeados para o esqueleto reduzido + juntas virtuais de Jiggle;
//  4. morph targets esparsos quantizados (somente fêmea adulta) + volumes e formas procedurais.
//
// Uso: node tools/build-assets.mjs [--mh <makehuman/makehuman/data>] [--out public/data]
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { fileURLToPath } from 'node:url';
import { parseObj, parseTarget, parseSkeleton, parseWeights } from './lib/mh.mjs';
import { catmullClark, lerpRows } from './lib/subdivide.mjs';
import { clipTriangles, compactClip } from '../src/geometry/clip.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const arg = (name, def) => {
  const i = args.indexOf(name);
  return i >= 0 ? args[i + 1] : def;
};
const MH = arg('--mh', process.env.MH_DATA || '/home/user/makehumancommunity/makehuman/makehuman/data');
const OUT = path.resolve(arg('--out', path.join(__dirname, '..', 'public', 'data')));
fs.mkdirSync(OUT, { recursive: true });

const SCALE = 0.1; // decímetro (MakeHuman) -> metro

// ---------------------------------------------------------------- parâmetros do corte (dm)
const CUT = {
  neck: 0.62, // distância ao longo do eixo do pescoço a partir de neck01.head
  arm: 0.95, // distância ao longo do eixo do braço a partir de upperarm01.head
  snap: 0.025, // 2,5 mm: vértices tão perto do plano ficam exatamente nele (sem triângulos-lasca)
};

// ---------------------------------------------------------------- vetor util
const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const add = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
const mul = (a, s) => [a[0] * s, a[1] * s, a[2] * s];
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const len = (a) => Math.hypot(a[0], a[1], a[2]);
const norm = (a) => mul(a, 1 / (len(a) || 1));
const smoothstep = (e0, e1, x) => {
  const t = Math.min(1, Math.max(0, (x - e0) / (e1 - e0)));
  return t * t * (3 - 2 * t);
};

// ---------------------------------------------------------------- leitura
console.log('> lendo base.obj, esqueleto e pesos...');
const obj = parseObj(path.join(MH, '3dobjs', 'base.obj'));
const basePos = obj.pos; // 19158*3, dm
const NV = basePos.length / 3;
const bodyFaces = obj.groups.get('body');
const bodyQuads = bodyFaces.map((f) => f.v);
const skel = parseSkeleton(path.join(MH, 'rigs', 'default.mhskel'));
const mhw = parseWeights(path.join(MH, 'rigs', 'default_weights.mhw'));

// ---------------------------------------------------------------- estado "mulher padrão"
function applyTargetInto(P, name, w) {
  const f = path.join(MH, 'targets', name + '.target');
  if (!fs.existsSync(f)) return false;
  const t = parseTarget(f);
  for (let i = 0; i < t.idx.length; i++) {
    const v = t.idx[i];
    P[v * 3] += t.d[i * 3] * w;
    P[v * 3 + 1] += t.d[i * 3 + 1] * w;
    P[v * 3 + 2] += t.d[i * 3 + 2] * w;
  }
  return true;
}
const Pdef = Float64Array.from(basePos);
for (const race of ['african', 'asian', 'caucasian']) applyTargetInto(Pdef, `macrodetails/${race}-female-young`, 1 / 3);
const P3 = (P, i) => [P[i * 3], P[i * 3 + 1], P[i * 3 + 2]];
const jointPos = (jname, P = Pdef) => {
  const idx = skel.joints[jname];
  const s = [0, 0, 0];
  for (const i of idx) {
    s[0] += P[i * 3];
    s[1] += P[i * 3 + 1];
    s[2] += P[i * 3 + 2];
  }
  return mul(s, 1 / idx.length);
};
const boneHead = (b) => jointPos(skel.bones[b].head);

// ---------------------------------------------------------------- esqueleto reduzido
const dropRe = /^(finger|metacarpal|lowerarm|wrist|eye|oculi|orbicularis|levator|oris|risorius|temporalis|tongue|special|jaw|head$)/;
const keepBones = Object.keys(skel.bones).filter((b) => !dropRe.test(b));
const order = [];
const seen = new Set();
const visit = (b) => {
  if (seen.has(b)) return;
  const p = skel.bones[b].parent;
  if (p && keepBones.includes(p)) visit(p);
  seen.add(b);
  order.push(b);
};
keepBones.forEach(visit);
const boneIndex = new Map(order.map((b, i) => [b, i]));
const retainedOf = (b) => {
  let c = b;
  while (c && !boneIndex.has(c)) c = skel.bones[c].parent;
  return c || 'root';
};
console.log(`  ossos retidos: ${order.length}`);

// ---------------------------------------------------------------- pesos por vértice base
const wacc = Array.from({ length: NV }, () => new Map());
for (const [bone, list] of Object.entries(mhw)) {
  const bi = boneIndex.get(retainedOf(bone));
  for (const [v, w] of list) wacc[v].set(bi, (wacc[v].get(bi) || 0) + w);
}
const armBones = { L: new Set(), R: new Set() };
for (const b of Object.keys(skel.bones)) {
  if (/^(upperarm01|upperarm02|lowerarm|wrist|finger|metacarpal)/.test(b)) armBones[b.endsWith('.L') ? 'L' : 'R'].add(b);
}
const armW = { L: new Float32Array(NV), R: new Float32Array(NV) };
for (const [bone, list] of Object.entries(mhw)) {
  for (const side of ['L', 'R']) if (armBones[side].has(bone)) for (const [v, w] of list) armW[side][v] += w;
}

// normais aproximadas (malha base, mulher padrão)
const nrm = new Float64Array(NV * 3);
{
  const tri = [];
  for (const [a, b, c, d] of bodyQuads) tri.push([a, b, c], [a, c, d]);
  for (const t of tri) {
    const a = P3(Pdef, t[0]);
    const e1 = sub(P3(Pdef, t[1]), a);
    const e2 = sub(P3(Pdef, t[2]), a);
    const n = [e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]];
    for (const v of t) for (let k = 0; k < 3; k++) nrm[v * 3 + k] += n[k];
  }
  for (let v = 0; v < NV; v++) {
    const l = Math.hypot(nrm[v * 3], nrm[v * 3 + 1], nrm[v * 3 + 2]) || 1;
    for (let k = 0; k < 3; k++) nrm[v * 3 + k] /= l;
  }
}
const nrm3 = (v) => [nrm[v * 3], nrm[v * 3 + 1], nrm[v * 3 + 2]];

// ---------------------------------------------------------------- juntas virtuais (jiggle)
// Elipsóides no espaço da mulher padrão (dm). Peso = amp * (1 - smoothstep(0,1,q)).
const VIRTUAL = [
  { name: 'glute.L', parent: 'pelvis.L', c: [0.9, -0.45, -0.95], r: [1.0, 1.15, 0.85], amp: 0.92, side: +1, nzMax: 0.35 },
  { name: 'glute.R', parent: 'pelvis.R', c: [-0.9, -0.45, -0.95], r: [1.0, 1.15, 0.85], amp: 0.92, side: -1, nzMax: 0.35 },
  { name: 'thigh.L', parent: 'upperleg02.L', c: [1.55, -2.35, 0.35], r: [0.95, 1.55, 1.15], amp: 0.8, side: +1 },
  { name: 'thigh.R', parent: 'upperleg02.R', c: [-1.55, -2.35, 0.35], r: [0.95, 1.55, 1.15], amp: 0.8, side: -1 },
  { name: 'belly', parent: 'spine05', c: [0, 1.15, 1.45], r: [1.35, 1.0, 0.75], amp: 0.85 },
];
for (const vb of VIRTUAL) {
  boneIndex.set(vb.name, order.length);
  order.push(vb.name);
}
// influências por vértice base [[bone, w], ...] com as juntas virtuais já aplicadas
const infl = new Array(NV);
for (let v = 0; v < NV; v++) {
  const m = new Map(wacc[v]);
  let s = 0;
  for (const w of m.values()) s += w;
  if (s <= 0) m.set(boneIndex.get('root'), 1);
  else for (const [b, w] of m) m.set(b, w / s);
  const p = P3(Pdef, v);
  for (const vb of VIRTUAL) {
    const q = Math.hypot((p[0] - vb.c[0]) / vb.r[0], (p[1] - vb.c[1]) / vb.r[1], (p[2] - vb.c[2]) / vb.r[2]);
    let w = vb.amp * (1 - smoothstep(0, 1, q));
    if (vb.side && p[0] * vb.side < 0.15) w *= smoothstep(-0.2, 0.3, p[0] * vb.side);
    if (vb.nzMax !== undefined) w *= smoothstep(vb.nzMax + 0.4, vb.nzMax - 0.3, nrm[v * 3 + 2]);
    if (vb.name === 'belly') w *= smoothstep(-0.2, 0.5, nrm[v * 3 + 2]);
    if (vb.name.startsWith('thigh')) w *= smoothstep(-0.2, 0.5, nrm[v * 3] * vb.side * 0.7 - Math.abs(nrm[v * 3 + 1]) * 0.3 + 0.35);
    if (w < 0.01) continue;
    for (const [b, bw] of m) m.set(b, bw * (1 - w));
    m.set(boneIndex.get(vb.name), w);
  }
  infl[v] = m;
}

// ---------------------------------------------------------------- subdivisão Catmull-Clark
console.log('> subdividindo (Catmull-Clark, 1 nível)...');
const sub1 = catmullClark(bodyQuads, NV);
const rows = sub1.rows; // Map(base -> peso) por vértice subdividido
const NS = rows.length;
const evalRows = (P) => {
  const out = new Float64Array(NS * 3);
  for (let i = 0; i < NS; i++) {
    let x = 0, y = 0, z = 0;
    for (const [k, w] of rows[i]) {
      x += P[k * 3] * w;
      y += P[k * 3 + 1] * w;
      z += P[k * 3 + 2] * w;
    }
    out[i * 3] = x; out[i * 3 + 1] = y; out[i * 3 + 2] = z;
  }
  return out;
};
const evalScalar = (arr) => {
  const out = new Float32Array(NS);
  for (let i = 0; i < NS; i++) {
    let s = 0;
    for (const [k, w] of rows[i]) s += arr[k] * w;
    out[i] = s;
  }
  return out;
};
const PS = evalRows(Pdef);
const armWS = { L: evalScalar(armW.L), R: evalScalar(armW.R) };
console.log(`  ${sub1.quads.length} quads, ${NS} vértices subdivididos`);

// ---------------------------------------------------------------- campos de corte
const neckA = norm(sub(boneHead('neck03'), boneHead('neck01')));
const neckP0 = add(boneHead('neck01'), mul(neckA, CUT.neck));
const armCut = {};
for (const side of ['L', 'R']) {
  const h = boneHead(`upperarm01.${side}`);
  const a = norm(sub(boneHead(`upperarm02.${side}`), h));
  armCut[side] = { a, p0: add(h, mul(a, CUT.arm)) };
}
const F = new Float64Array(NS);
for (let v = 0; v < NS; v++) {
  const p = P3(PS, v);
  let f = dot(sub(p, neckP0), neckA);
  for (const side of ['L', 'R']) {
    const c = armCut[side];
    const fa = armWS[side][v] > 0.5 ? dot(sub(p, c.p0), c.a) : -1;
    if (fa > f) f = fa;
  }
  F[v] = f;
}

// ---------------------------------------------------------------- triangulação (diagonal mais curta) e recorte
const triFlat = [];
for (const [a, b, c, d] of sub1.quads) {
  const d02 = len(sub(P3(PS, a), P3(PS, c)));
  const d13 = len(sub(P3(PS, b), P3(PS, d)));
  if (d02 <= d13) triFlat.push(a, b, c, a, c, d);
  else triFlat.push(a, b, d, b, c, d);
}
const cut = compactClip(clipTriangles(triFlat, F, CUT.snap));
const N = cut.vertices.length;
const indices = Uint16Array.from(cut.tris);
console.log(`  malha final: ${N} vértices, ${indices.length / 3} triângulos`);

// stencil de cada vértice final (vértice subdividido ou ponto numa aresta recortada)
const finalRows = cut.vertices.map((v) => (v.t === 0 ? rows[v.a] : lerpRows(rows[v.a], rows[v.b], v.t)));
const PSF = new Float64Array(N * 3); // posições finais na mulher padrão (dm)
finalRows.forEach((row, i) => {
  let x = 0, y = 0, z = 0;
  for (const [k, w] of row) {
    x += Pdef[k * 3] * w;
    y += Pdef[k * 3 + 1] * w;
    z += Pdef[k * 3 + 2] * w;
  }
  PSF[i * 3] = x; PSF[i * 3 + 1] = y; PSF[i * 3 + 2] = z;
});

// ---------------------------------------------------------------- base compacta
const RULERS = {
  bust: [8439, 8455, 8462, 8446, 8478, 8494, 8557, 8510, 8526, 8542, 10720, 10601, 10603, 10602, 10612, 10611, 10610, 10613, 10604, 10605, 10606, 3942, 3941, 3940, 3950, 3947, 3948, 3949, 3938, 3939, 3937, 4065, 1870, 1854, 1838, 1885, 1822, 1806, 1774, 1790, 1783, 1767, 1799, 8471],
  underbust: [10750, 10744, 10724, 10725, 10748, 10722, 10640, 10642, 10641, 10651, 10650, 10649, 10652, 10643, 10644, 10645, 10646, 10647, 10648, 3988, 3987, 3986, 3985, 3984, 3983, 3982, 3992, 3989, 3990, 3991, 3980, 3981, 3979, 4067, 4098, 4073, 4072, 4094, 4100, 4082, 4088],
  waist: [4121, 10760, 10757, 10777, 10776, 10779, 10780, 10778, 10781, 10771, 10773, 10772, 10775, 10774, 10814, 10834, 10816, 10817, 10818, 10819, 10820, 10821, 4181, 4180, 4179, 4178, 4177, 4176, 4175, 4196, 4173, 4131, 4132, 4129, 4130, 4128, 4138, 4135, 4137, 4136, 4133, 4134, 4108, 4113, 4118, 4121],
  hips: [4341, 10968, 10969, 10971, 10970, 10967, 10928, 10927, 10925, 10926, 10923, 10924, 10868, 10875, 10861, 10862, 4228, 4227, 4226, 4242, 4234, 4294, 4293, 4296, 4295, 4297, 4298, 4342, 4345, 4346, 4344, 4343, 4361, 4341],
  thigh: [11071, 11080, 11081, 11086, 11076, 11077, 11074, 11075, 11072, 11073, 11069, 11070, 11087, 11085, 11084, 12994, 11083, 11082, 11079, 11071],
  knee: [11223, 11230, 11232, 11233, 11238, 11228, 11229, 11226, 11227, 11224, 11225, 11221, 11222, 11239, 11237, 11236, 13002, 11235, 11234, 11223],
  calf: [11339, 11336, 11353, 11351, 11350, 13008, 11349, 11348, 11345, 11337, 11344, 11346, 11347, 11352, 11342, 11343, 11340, 11341, 11338, 11339],
  ankle: [11460, 11464, 11458, 11459, 11419, 11418, 12958, 12965, 12960, 12963, 12961, 12962, 12964, 12927, 13028, 12957, 11463, 11461, 11457, 11460],
};
const CROWN = skel.joints['head____tail'];
const baseNeeded = new Set();
for (const row of finalRows) for (const k of row.keys()) baseNeeded.add(k);
for (const b of order) {
  const d = skel.bones[b];
  if (!d) continue; // juntas virtuais
  for (const j of [d.head, d.tail]) for (const v of skel.joints[j]) baseNeeded.add(v);
}
for (const list of Object.values(RULERS)) for (const v of list) baseNeeded.add(v);
for (const v of CROWN) baseNeeded.add(v);
const baseList = [...baseNeeded].sort((a, b) => a - b);
const baseMap = new Map(baseList.map((v, i) => [v, i]));
const NB = baseList.length;

// stencils finais (CSR) com índices da base compacta e pesos quantizados em 16 bits
const stencilStart = new Uint32Array(N + 1);
const sIdx = [];
const sW = [];
finalRows.forEach((row, i) => {
  stencilStart[i] = sIdx.length;
  const entries = [...row.entries()].filter(([, w]) => w > 1e-6).sort((a, b) => b[1] - a[1]);
  const total = entries.reduce((s, e) => s + e[1], 0);
  const q = entries.map(([, w]) => Math.round((w / total) * 65535));
  q[0] += 65535 - q.reduce((a, b) => a + b, 0); // soma exata = 1
  entries.forEach(([k], j) => {
    sIdx.push(baseMap.get(k));
    sW.push(q[j]);
  });
});
stencilStart[N] = sIdx.length;
console.log(`  base compacta: ${NB} vértices; stencils: ${sIdx.length} entradas (média ${(sIdx.length / N).toFixed(1)})`);

// ---------------------------------------------------------------- pesos de skinning finais
const skinIndex = new Uint8Array(N * 4);
const skinWeight = new Uint8Array(N * 4);
const quantizeW = (list) => {
  const out = new Array(4).fill(0);
  let tot = 0;
  list.forEach(([, w], i) => {
    out[i] = Math.round(w * 255);
    tot += out[i];
  });
  out[0] += 255 - tot;
  return out;
};
finalRows.forEach((row, i) => {
  const m = new Map();
  for (const [k, w] of row) for (const [b, bw] of infl[k]) m.set(b, (m.get(b) || 0) + w * bw);
  const top = [...m.entries()].sort((a, b) => b[1] - a[1]).slice(0, 4);
  const s = top.reduce((a, b) => a + b[1], 0) || 1;
  const list = top.map(([b, w]) => [b, w / s]);
  const q = quantizeW(list);
  list.forEach(([b], j) => {
    skinIndex[i * 4 + j] = b;
    skinWeight[i * 4 + j] = q[j];
  });
});

// ---------------------------------------------------------------- laços de borda (Caps) e eixos de saída
const edgeCount = new Map();
const dirEdge = new Map();
for (let t = 0; t < indices.length; t += 3) {
  for (let e = 0; e < 3; e++) {
    const a = indices[t + e];
    const b = indices[t + ((e + 1) % 3)];
    const key = a < b ? a * 65536 + b : b * 65536 + a;
    edgeCount.set(key, (edgeCount.get(key) || 0) + 1);
    dirEdge.set(a * 65536 + b, [a, b]);
  }
}
const nextOf = new Map();
for (const [key, c] of edgeCount) {
  if (c !== 1) continue;
  const a = Math.floor(key / 65536);
  const b = key % 65536;
  const d = dirEdge.has(a * 65536 + b) ? [a, b] : [b, a];
  nextOf.set(d[0], d[1]);
}
const loops = [];
const doneL = new Set();
for (const s of nextOf.keys()) {
  if (doneL.has(s)) continue;
  const loop = [];
  let c = s;
  while (c !== undefined && !doneL.has(c)) {
    doneL.add(c);
    loop.push(c);
    c = nextOf.get(c);
  }
  loops.push(loop);
}
// eixo de saída (referência) de cada Cut: normal do plano de corte mais próximo do centro do laço
const loopAxes = loops.map((loop) => {
  const c = [0, 0, 0];
  for (const i of loop) for (let k = 0; k < 3; k++) c[k] += PSF[i * 3 + k] / loop.length;
  const cand = [
    { d: Math.abs(dot(sub(c, neckP0), neckA)), a: neckA },
    ...['L', 'R'].map((s) => ({ d: Math.abs(dot(sub(c, armCut[s].p0), armCut[s].a)), a: armCut[s].a })),
  ].sort((x, y) => x.d - y.d);
  return cand[0].a;
});
console.log(`  laços de borda (Cuts): ${loops.map((l) => l.length).join(', ')}`);

// ---------------------------------------------------------------- zona de suavização do cruzamento
// Peso 0..255 por vértice: a região entre as pernas é suavizada no runtime (a cada morph) para que o
// tecido justo faça uma transição limpa. O busto NÃO é suavizado: o tecido marca o contorno ("tenda").
const smoothZone = new Uint8Array(N);
{
  let cy = Infinity;
  const kneeY = boneHead('lowerleg01.L')[1];
  for (let i = 0; i < N; i++) {
    const p = P3(PSF, i);
    if (Math.abs(p[0]) < 0.06 && p[1] < cy && p[1] > kneeY) cy = p[1];
  }
  for (let i = 0; i < N; i++) {
    const p = P3(PSF, i);
    const ax = Math.abs(p[0]);
    const wc = (1 - smoothstep(0.2, 0.5, ax)) * smoothstep(cy - 0.4, cy, p[1]) * (1 - smoothstep(cy + 0.9, cy + 1.5, p[1]));
    smoothZone[i] = Math.round(255 * wc);
  }
  console.log(`  zona de suavização (cruzamento): ${smoothZone.filter((x) => x > 0).length} vértices`);
}

// ---------------------------------------------------------------- esqueleto exportado
const bonesOut = order.map((name) => {
  const vb = VIRTUAL.find((x) => x.name === name);
  if (vb) return { n: name, p: boneIndex.get(vb.parent), v: 1 };
  const b = skel.bones[name];
  const p = b.parent && boneIndex.has(retainedOf(b.parent)) ? boneIndex.get(retainedOf(b.parent)) : -1;
  return {
    n: name,
    p,
    h: skel.joints[b.head].map((v) => baseMap.get(v)),
    t: skel.joints[b.tail].map((v) => baseMap.get(v)),
  };
});

// ---------------------------------------------------------------- morph targets
console.log('> convertendo morph targets...');
const targetNames = [];
const addIf = (name) => {
  if (fs.existsSync(path.join(MH, 'targets', name + '.target'))) targetNames.push(name);
};
const AGES = ['young', 'old'];
const MUSC = ['minmuscle', 'averagemuscle', 'maxmuscle'];
const WGT = ['minweight', 'averageweight', 'maxweight'];
for (const a of AGES) {
  for (const m of MUSC) {
    for (const w of WGT) {
      addIf(`macrodetails/universal-female-${a}-${m}-${w}`);
      for (const h of ['minheight', 'maxheight']) addIf(`macrodetails/height/female-${a}-${m}-${w}-${h}`);
      for (const p of ['idealproportions', 'uncommonproportions']) addIf(`macrodetails/proportions/female-${a}-${m}-${w}-${p}`);
      for (const c of ['mincup', 'averagecup', 'maxcup']) {
        for (const f of ['minfirmness', 'averagefirmness', 'maxfirmness']) addIf(`breast/female-${a}-${m}-${w}-${c}-${f}`);
      }
    }
  }
  for (const race of ['african', 'asian', 'caucasian']) addIf(`macrodetails/${race}-female-${a}`);
}
const listDir = (d) => fs.readdirSync(path.join(MH, 'targets', d)).filter((f) => f.endsWith('.target')).map((f) => f.slice(0, -7));
const take = (dir, pred) => listDir(dir).filter(pred).forEach((n) => targetNames.push(`${dir}/${n}`));
take('breast', (n) => n.startsWith('breast-'));
take('hip', () => true);
take('buttocks', () => true);
take('stomach', () => true);
take('pelvis', (n) => n.startsWith('pelvis-tone'));
take('torso', () => true);
take('neck', () => true);
take('armslegs', (n) => /^(l|r)-(upperleg|lowerleg|leg-valgus|foot)/.test(n) || /^(upperlegs|lowerlegs)-height/.test(n));
take('measure', (n) => /^measure-(neck|bust|underbust|waist|napetowaist|waisttohip|hips|upperleg|thigh|lowerleg|calf|knee|ankle|shoulder|frontchest)/.test(n));
take('bodyshapes', (n) => /^bodyshapes-elvs-fem-(apple|diamond|full-hourglass|neat-hourglass|invert-triangle|lean-column|rectangle|triangle)$/.test(n));
take('asym', (n) => n.startsWith('asymm-breast') || n.startsWith('asymm-trunk'));

const tIdx = [];
const tDelta = [];
const manifest = [];
let totalEntries = 0;
function pushTarget(name, ids, ds, maxAbs) {
  if (ids.length === 0) {
    manifest.push([name, totalEntries, 0, 0]);
    return;
  }
  const scale = maxAbs / 32767;
  for (const k of ids) tIdx.push(k);
  for (const d of ds) tDelta.push(Math.max(-32767, Math.min(32767, Math.round(d / scale))));
  manifest.push([name, totalEntries, ids.length, scale]);
  totalEntries += ids.length;
}
for (const name of targetNames) {
  const t = parseTarget(path.join(MH, 'targets', name + '.target'));
  const ids = [];
  const ds = [];
  let maxAbs = 0;
  for (let i = 0; i < t.idx.length; i++) {
    const k = baseMap.get(t.idx[i]);
    if (k === undefined) continue;
    const dx = t.d[i * 3] * SCALE;
    const dy = t.d[i * 3 + 1] * SCALE;
    const dz = t.d[i * 3 + 2] * SCALE;
    if (dx === 0 && dy === 0 && dz === 0) continue;
    ids.push(k);
    ds.push(dx, dy, dz);
    maxAbs = Math.max(maxAbs, Math.abs(dx), Math.abs(dy), Math.abs(dz));
  }
  pushTarget(name, ids, ds, maxAbs);
}

// ---------------------------------------------------------------- morphs procedurais
// Volumes (busto, glúteos, coxas) e formas dos glúteos (dobra infraglútea, sulco central, caído/firme).
// Definidos sobre a malha base (decímetros, mulher padrão); a subdivisão os suaviza. Cada alvo tem
// versão incr (+) e decr (-, o oposto).
const bodyVertexSet = new Set();
for (const q of bodyQuads) for (const v of q) bodyVertexSet.add(v);
const nipples = ['breast.L____tail', 'breast.R____tail'].map((j) => jointPos(j));
const nippleNormals = ['breast.L____tail', 'breast.R____tail'].map((j) => nrm3(skel.joints[j][0]));

const gluteWeight = (p, n, rad = [1.15, 1.45, 0.95]) => {
  let best = { w: 0, s: 1, c: null };
  for (const s of [1, -1]) {
    const c = [0.9 * s, -0.55, -0.95];
    const q = Math.hypot((p[0] - c[0]) / rad[0], (p[1] - c[1]) / rad[1], (p[2] - c[2]) / rad[2]);
    let w = 1 - smoothstep(0, 1, q);
    w *= smoothstep(0.4, -0.3, n[2]) * (s * p[0] > -0.1 ? 1 : 0);
    if (w > best.w) best = { w, s, c };
  }
  return best;
};
const foldY = (ax) => -1.2 + 0.2 * smoothstep(0.3, 1.4, ax); // linha da dobra infraglútea (dm): sobe levemente para o lado
const foldGroove = (p, n) => {
  const ax = Math.abs(p[0]);
  const dy = p[1] - foldY(ax);
  const win = smoothstep(0.12, 0.45, ax) * (1 - smoothstep(1.25, 1.65, ax));
  const back = smoothstep(0.35, -0.35, n[2]);
  return { groove: Math.exp(-((dy / 0.2) ** 2)) * win * back, roll: Math.exp(-(((dy - 0.42) / 0.3) ** 2)) * win * back };
};

const procedural = {
  'bust-volume': (v, p, n) => {
    let best = null;
    for (let s = 0; s < 2; s++) {
      const c = sub(nipples[s], mul(nippleNormals[s], 0.4));
      const r = sub(p, c);
      const w = 1 - smoothstep(0.25, 1.35, len(r));
      if (w <= 0 || dot(n, nippleNormals[s]) < -0.1) continue;
      const dir = norm(add(mul(n, 0.45), mul(norm(r), 0.55)));
      const amp = 0.36 * w * smoothstep(-0.1, 0.45, dot(n, nippleNormals[s]));
      if (!best || amp > best.amp) best = { amp, dir };
    }
    return best && best.amp > 1e-4 ? mul(best.dir, best.amp) : null;
  },
  'glutes-volume': (v, p, n) => {
    const g = gluteWeight(p, n, [1.05, 1.2, 0.9]);
    if (g.w <= 0) return null;
    const dir = norm([n[0] * 0.5, n[1] * 0.2 + 0.2, n[2]]);
    return mul(dir, 0.32 * g.w);
  },
  'thighs-volume': (v, p, n) => {
    let best = null;
    for (const s of [1, -1]) {
      const rr = [p[0] - 1.45 * s, 0, p[2] - 0.4];
      const q = Math.hypot((p[0] - 1.45 * s) / 1.0, (p[1] + 2.2) / 1.65, (p[2] - 0.4) / 1.1);
      let w = 1 - smoothstep(0, 1, q);
      if (s * p[0] < 0.55) w *= smoothstep(0.35, 0.8, s * p[0]);
      if (w <= 0) continue;
      const amp = 0.3 * w;
      if (!best || amp > best.amp) best = { amp, dir: norm(add(mul(norm(rr), 0.7), mul(n, 0.3))) };
    }
    return best && best.amp > 1e-4 ? mul(best.dir, best.amp) : null;
  },
  // parte alta das coxas (formato pera, como nos desenhos de referência): cresce mais perto do quadril e
  // afina até o joelho; empurra a superfície radialmente a partir do eixo da coxa
  'thighs-upper-volume': (v, p, n) => {
    let best = null;
    for (const s of [1, -1]) {
      const k = Math.min(1, Math.max(0, (-p[1] - 0.05) / 3.675)); // 0 no quadril, 1 no joelho
      const ax = (0.943 + 0.394 * k) * s;
      const az = 0.175 + 0.304 * k;
      const rr = [p[0] - ax, 0, p[2] - az];
      const q = Math.hypot((p[0] - ax) / 1.15, (p[1] + 1.55) / 1.3, (p[2] - az) / 1.2);
      let w = 1 - smoothstep(0, 1, q);
      if (s * p[0] < 0.3) w *= smoothstep(0.1, 0.45, s * p[0]);
      if (w <= 0) continue;
      const amp = 0.34 * w;
      if (!best || amp > best.amp) best = { amp, dir: norm(add(mul(norm(rr), 0.8), mul(n, 0.2))) };
    }
    return best && best.amp > 1e-4 ? mul(best.dir, best.amp) : null;
  },
  // glúteos "relaxados" (macios): a massa desce pouco, a parte de baixo fica mais cheia e projetada e o
  // polo superior só suaviza. Nunca achata nem pende como num corpo envelhecido (isso é o Trait Age).
  'glutes-relax': (v, p, n) => {
    const g = gluteWeight(p, n);
    if (g.w <= 0) return null;
    const yr = (p[1] - g.c[1]) / 0.7;
    const upper = smoothstep(-0.2, 0.7, yr);
    const lower = smoothstep(0.1, -0.8, yr);
    const d = [0.02 * g.s * g.w, -0.13 * g.w, -0.05 * g.w * lower];
    return add(d, mul(n, 0.05 * g.w * lower - 0.02 * g.w * upper));
  },
  // glúteos "empinados" (firmes): sobem e arredondam o polo superior
  'glutes-lift': (v, p, n) => {
    const g = gluteWeight(p, n);
    if (g.w <= 0) return null;
    const yr = (p[1] - g.c[1]) / 0.7;
    const upper = smoothstep(-0.2, 0.7, yr);
    const d = [-0.02 * g.s * g.w, 0.2 * g.w, -0.03 * g.w * upper];
    return add(d, mul(n, 0.05 * g.w * upper));
  },
  // dobra infraglútea: sulco sob o glúteo + leve "rolo" acima dela
  'glutes-fold': (v, p, n) => {
    const f = foldGroove(p, n);
    if (f.groove < 1e-3 && f.roll < 1e-3) return null;
    return mul(n, -0.09 * f.groove + 0.04 * f.roll);
  },
  // sulco central (entre os glúteos)
  'glutes-cleft': (v, p, n) => {
    const g = Math.exp(-((p[0] / 0.2) ** 2));
    const win = smoothstep(-1.35, -1.0, p[1]) * (1 - smoothstep(0.1, 0.45, p[1]));
    const back = smoothstep(0.35, -0.35, n[2]);
    const w = g * win * back;
    return w < 1e-3 ? null : mul(n, -0.1 * w);
  },
};
function emitProcedural(name, fn, sign) {
  const ids = [];
  const ds = [];
  let maxAbs = 0;
  for (const v of baseList) {
    if (!bodyVertexSet.has(v)) continue;
    const d = fn(v, P3(Pdef, v), nrm3(v));
    if (!d) continue;
    ids.push(baseMap.get(v));
    for (const x of d) {
      ds.push(x * SCALE * sign);
      maxAbs = Math.max(maxAbs, Math.abs(x * SCALE));
    }
  }
  pushTarget(name, ids, ds, maxAbs);
  targetNames.push(name);
  console.log(`  ${name}: ${ids.length} vértices`);
}
for (const key of ['bust-volume', 'glutes-volume', 'thighs-volume', 'thighs-upper-volume', 'glutes-fold', 'glutes-cleft']) {
  emitProcedural(`custom/${key}-incr`, procedural[key], +1);
  emitProcedural(`custom/${key}-decr`, procedural[key], -1);
}
emitProcedural('custom/glutes-lift-incr', procedural['glutes-lift'], +1);
emitProcedural('custom/glutes-lift-decr', procedural['glutes-relax'], +1);

// ---------------------------------------------------------------- escrita
const pad4 = (n) => (n + 3) & ~3;
function packSections(sections) {
  let off = 0;
  const meta = {};
  for (const [name, arr] of sections) {
    meta[name] = { o: off, n: arr.length, t: arr.constructor.name };
    off += pad4(arr.byteLength);
  }
  const buf = Buffer.alloc(off);
  for (const [name, arr] of sections) Buffer.from(arr.buffer, arr.byteOffset, arr.byteLength).copy(buf, meta[name].o);
  return { meta, buf };
}
const basePosCompact = new Float32Array(NB * 3);
baseList.forEach((v, k) => {
  for (let c = 0; c < 3; c++) basePosCompact[k * 3 + c] = basePos[v * 3 + c] * SCALE;
});
const body = packSections([
  ['basePos', basePosCompact],
  ['stencilStart', stencilStart],
  ['stencilIdx', Uint16Array.from(sIdx)],
  ['stencilW16', Uint16Array.from(sW)],
  ['skinIndex', skinIndex],
  ['skinWeight', skinWeight],
  ['indices', indices],
  ['smoothZone', smoothZone],
]);
const tgt = packSections([
  ['idx', Uint16Array.from(tIdx)],
  ['delta', Int16Array.from(tDelta)],
]);

const bodyJson = {
  version: 2,
  units: 'm',
  subdivision: 1,
  baseCount: NB,
  vertCount: N,
  triCount: indices.length / 3,
  sections: body.meta,
  bones: bonesOut,
  loops,
  loopAxes: loopAxes.map((a) => a.map((x) => +x.toFixed(5))),
  cut: CUT,
  rulers: Object.fromEntries(Object.entries(RULERS).map(([k, l]) => [k, l.map((v) => baseMap.get(v))])),
  crown: CROWN.map((v) => baseMap.get(v)),
};
const targetsJson = { sections: tgt.meta, targets: manifest };

const gz = (buf) => zlib.gzipSync(buf, { level: 9 });
fs.writeFileSync(path.join(OUT, 'body.json'), JSON.stringify(bodyJson));
fs.writeFileSync(path.join(OUT, 'body.bin.gz'), gz(body.buf));
fs.writeFileSync(path.join(OUT, 'targets.json'), JSON.stringify(targetsJson));
fs.writeFileSync(path.join(OUT, 'targets.bin.gz'), gz(tgt.buf));
console.log(`> ok: body.bin ${(body.buf.length / 1024).toFixed(0)} KB (gz ${(gz(body.buf).length / 1024).toFixed(0)} KB), targets.bin ${(tgt.buf.length / 1024).toFixed(0)} KB (gz ${(gz(tgt.buf).length / 1024).toFixed(0)} KB), ${targetNames.length} targets`);
