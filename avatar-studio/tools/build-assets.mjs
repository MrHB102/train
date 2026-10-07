#!/usr/bin/env node
// Conversor de assets: MakeHuman (CC0) -> pacote binário para o navegador.
//
// Gera o corpo feminino SEM CABEÇA E SEM BRAÇOS (torso + pernas, estilo manequim):
//  - malha cortada por planos no pescoço e nos ombros (triângulos recortados com vértices novos
//    ligados por (A,B,t) aos vértices base, assim o corte acompanha todos os morphs);
//  - pesos de skinning (top-4) remapeados para o esqueleto reduzido + ossos virtuais de jiggle;
//  - morph targets esparsos quantizados (somente fêmea adulta; sem rosto/mãos).
//
// Uso: node tools/build-assets.mjs [--mh <makehuman/makehuman/data>] [--out public/data]
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { fileURLToPath } from 'node:url';
import { parseObj, parseTarget, parseSkeleton, parseWeights } from './lib/mh.mjs';
import { clipTriangles } from '../src/geometry/clip.js';

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
const boneTail = (b) => jointPos(skel.bones[b].tail);

// ---------------------------------------------------------------- esqueleto reduzido
const dropRe = /^(finger|metacarpal|lowerarm|wrist|eye|oculi|orbicularis|levator|oris|risorius|temporalis|tongue|special|jaw|head$)/;
const keepBones = Object.keys(skel.bones).filter((b) => !dropRe.test(b));
// ordem topológica (pais antes)
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
// mapeia um osso qualquer para o ancestral retido mais próximo
const retainedOf = (b) => {
  let c = b;
  while (c && !boneIndex.has(c)) c = skel.bones[c].parent;
  return c || 'root';
};
// o resto do braço aponta para upperarm02; cabeça/rosto para neck03 (via ancestral retido)
console.log(`  ossos retidos: ${order.length}`);

// ---------------------------------------------------------------- pesos por vértice base
const wacc = Array.from({ length: NV }, () => new Map());
for (const [bone, list] of Object.entries(mhw)) {
  const rb = retainedOf(bone);
  const bi = boneIndex.get(rb);
  for (const [v, w] of list) {
    const m = wacc[v];
    m.set(bi, (m.get(bi) || 0) + w);
  }
}
// campo "peso de braço" (ossos do braço a partir de upperarm01) para o corte dos ombros
const armBonesL = new Set();
const armBonesR = new Set();
for (const b of Object.keys(skel.bones)) {
  if (/^(upperarm01|upperarm02|lowerarm|wrist|finger|metacarpal)/.test(b)) (b.endsWith('.L') ? armBonesL : armBonesR).add(b);
}
const armW = { L: new Float32Array(NV), R: new Float32Array(NV) };
for (const [bone, list] of Object.entries(mhw)) {
  for (const side of ['L', 'R']) {
    if ((side === 'L' ? armBonesL : armBonesR).has(bone)) for (const [v, w] of list) armW[side][v] += w;
  }
}

// ---------------------------------------------------------------- campos escalares de corte
const neckA = norm(sub(boneHead('neck03'), boneHead('neck01')));
const neckP0 = add(boneHead('neck01'), mul(neckA, CUT.neck));
const armCut = {};
for (const side of ['L', 'R']) {
  const h = boneHead(`upperarm01.${side}`);
  const a = norm(sub(boneHead(`upperarm02.${side}`), h));
  armCut[side] = { a, p0: add(h, mul(a, CUT.arm)) };
}
const F = new Float64Array(NV);
for (let v = 0; v < NV; v++) {
  const p = P3(Pdef, v);
  let f = dot(sub(p, neckP0), neckA);
  for (const side of ['L', 'R']) {
    const c = armCut[side];
    const fa = armW[side][v] > 0.5 ? dot(sub(p, c.p0), c.a) : -1;
    if (fa > f) f = fa;
  }
  F[v] = f;
}

// ---------------------------------------------------------------- triangulação (diagonal mais curta)
const tris = [];
for (const f of bodyFaces) {
  const [a, b, c, d] = f.v;
  if (f.v.length === 3) {
    tris.push([a, b, c]);
    continue;
  }
  const d02 = len(sub(P3(Pdef, a), P3(Pdef, c)));
  const d13 = len(sub(P3(Pdef, b), P3(Pdef, d)));
  if (d02 <= d13) tris.push([a, b, c], [a, c, d]);
  else tris.push([a, b, d], [b, c, d]);
}

// ---------------------------------------------------------------- recorte (módulo compartilhado com o runtime)
const SNAP = 0.04; // dm (4 mm): vértices tão próximos do plano ficam exatamente nele
const clipRes = clipTriangles(tris.flat(), F, SNAP);
const clipDesc = clipRes.clipVerts; // [A,B,t] em índice base original
const clipped = [];
for (let t = 0; t < clipRes.tris.length; t += 3) clipped.push([clipRes.tris[t], clipRes.tris[t + 1], clipRes.tris[t + 2]]);

// ---------------------------------------------------------------- compactação
// Vértices da malha final (índices originais >= NV são recortados)
const used = new Set();
for (const t of clipped) for (const v of t) used.add(v);
const finalList = [...used].sort((a, b) => a - b);
const finalIndex = new Map(finalList.map((v, i) => [v, i]));
const N = finalList.length;

// base vertices necessários: os dos vértices finais originais + extremos dos recortados + juntas
const baseNeeded = new Set();
for (const v of finalList) {
  if (v < NV) baseNeeded.add(v);
  else {
    const [A, B] = clipDesc[v - NV];
    baseNeeded.add(A);
    baseNeeded.add(B);
  }
}
for (const b of order) {
  for (const j of skel.bones[b].head && [skel.bones[b].head, skel.bones[b].tail]) for (const v of skel.joints[j]) baseNeeded.add(v);
}
// réguas de medidas (MakeHuman, plugin de medidas) e topo da cabeça (para a altura total)
const RULERS = {
  bust: [8439, 8455, 8462, 8446, 8478, 8494, 8557, 8510, 8526, 8542, 10720, 10601, 10603, 10602, 10612, 10611, 10610, 10613, 10604, 10605, 10606, 3942, 3941, 3940, 3950, 3947, 3948, 3949, 3938, 3939, 3937, 4065, 1870, 1854, 1838, 1885, 1822, 1806, 1774, 1790, 1783, 1767, 1799, 8471],
  underbust: [10750, 10744, 10724, 10725, 10748, 10722, 10640, 10642, 10641, 10651, 10650, 10649, 10652, 10643, 10644, 10645, 10646, 10647, 10648, 3988, 3987, 3986, 3985, 3984, 3983, 3982, 3992, 3989, 3990, 3991, 3980, 3981, 3979, 4067, 4098, 4073, 4072, 4094, 4100, 4082, 4088],
  waist: [4121, 10760, 10757, 10777, 10776, 10779, 10780, 10778, 10781, 10771, 10773, 10772, 10775, 10774, 10814, 10834, 10816, 10817, 10818, 10819, 10820, 10821, 4181, 4180, 4179, 4178, 4177, 4176, 4175, 4196, 4173, 4131, 4132, 4129, 4130, 4128, 4138, 4135, 4137, 4136, 4133, 4134, 4108, 4113, 4118, 4121],
  hips: [4341, 10968, 10969, 10971, 10970, 10967, 10928, 10927, 10925, 10926, 10923, 10924, 10868, 10875, 10861, 10862, 4228, 4227, 4226, 4242, 4234, 4294, 4293, 4296, 4295, 4297, 4298, 4342, 4345, 4346, 4344, 4343, 4361, 4341],
  thigh: [11071, 11080, 11081, 11086, 11076, 11077, 11074, 11075, 11072, 11073, 11069, 11070, 11087, 11085, 11084, 12994, 11083, 11082, 11079, 11071],
  knee: [11223, 11230, 11232, 11233, 11238, 11228, 11229, 11226, 11227, 11224, 11225, 11221, 11222, 11239, 11237, 11236, 13002, 11235, 11234, 11223],
  calf: [11339, 11336, 11353, 11351, 11350, 13008, 11349, 11348, 11345, 11337, 11344, 11346, 11347, 11352, 11342, 11343, 11340, 11341, 11338, 11339],
  ankle: [11460, 11464, 11458, 11459, 11419, 11418, 12958, 12965, 12960, 12963, 12961, 12962, 12964, 12927, 13028, 12957, 11463, 11461, 11457, 11460],
  // alturas verticais (pares de vértices) usadas para o comprimento do torso
  napeToWaist: [1491, 4181],
};
const CROWN = skel.joints['head____tail'];
for (const list of Object.values(RULERS)) for (const v of list) baseNeeded.add(v);
for (const v of CROWN) baseNeeded.add(v);
const baseList = [...baseNeeded].sort((a, b) => a - b);
const baseMap = new Map(baseList.map((v, i) => [v, i]));
const NB = baseList.length;
console.log(`  malha: ${N} vértices (${finalList.filter((v) => v >= NV).length} recortados), ${clipped.length} triângulos, base compacta ${NB}`);

// ---------------------------------------------------------------- ossos virtuais (jiggle)
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

// normais aproximadas na mulher padrão para limitar ossos virtuais à face externa
const nrm = new Float64Array(NV * 3);
for (const t of tris) {
  const a = P3(Pdef, t[0]);
  const b = P3(Pdef, t[1]);
  const c = P3(Pdef, t[2]);
  const e1 = sub(b, a);
  const e2 = sub(c, a);
  const n = [e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]];
  for (const v of t) {
    nrm[v * 3] += n[0];
    nrm[v * 3 + 1] += n[1];
    nrm[v * 3 + 2] += n[2];
  }
}
for (let v = 0; v < NV; v++) {
  const l = Math.hypot(nrm[v * 3], nrm[v * 3 + 1], nrm[v * 3 + 2]) || 1;
  nrm[v * 3] /= l;
  nrm[v * 3 + 1] /= l;
  nrm[v * 3 + 2] /= l;
}

// pesos finais (base compacta): top-4 + normalizados
const infl = new Array(NB); // [[bone,weight],...]
for (let k = 0; k < NB; k++) {
  const v = baseList[k];
  const m = new Map(wacc[v]);
  // normaliza
  let s = 0;
  for (const w of m.values()) s += w;
  if (s <= 0) m.set(boneIndex.get('root'), 1);
  else for (const [b, w] of m) m.set(b, w / s);
  const p = P3(Pdef, v);
  for (const vb of VIRTUAL) {
    const q = Math.hypot((p[0] - vb.c[0]) / vb.r[0], (p[1] - vb.c[1]) / vb.r[1], (p[2] - vb.c[2]) / vb.r[2]);
    let w = vb.amp * (1 - smoothstep(0, 1, q));
    // só o lado correto e a face externa
    if (vb.side && p[0] * vb.side < 0.15) w *= smoothstep(-0.2, 0.3, p[0] * vb.side);
    if (vb.nzMax !== undefined) w *= smoothstep(vb.nzMax + 0.4, vb.nzMax - 0.3, nrm[v * 3 + 2]);
    if (vb.name === 'belly') w *= smoothstep(-0.2, 0.5, nrm[v * 3 + 2]);
    if (vb.name.startsWith('thigh')) w *= smoothstep(-0.2, 0.5, nrm[v * 3] * vb.side * 0.7 - Math.abs(nrm[v * 3 + 1]) * 0.3 + 0.35);
    if (w < 0.01) continue;
    for (const [b, bw] of m) m.set(b, bw * (1 - w));
    m.set(boneIndex.get(vb.name), w);
  }
  infl[k] = [...m.entries()];
}
const topN = (list, n = 4) => {
  const l = list.slice().sort((a, b) => b[1] - a[1]).slice(0, n);
  const s = l.reduce((a, b) => a + b[1], 0) || 1;
  return l.map(([b, w]) => [b, w / s]);
};

// ---------------------------------------------------------------- arrays finais da malha
const bindA = new Uint16Array(N);
const bindB = new Uint16Array(N);
const bindT = new Float32Array(N);
const skinIndex = new Uint8Array(N * 4);
const skinWeight = new Uint8Array(N * 4);
const quantizeW = (list) => {
  const out = new Array(4).fill(0);
  let tot = 0;
  list.forEach(([, w], i) => {
    out[i] = Math.round(w * 255);
    tot += out[i];
  });
  out[0] += 255 - tot; // ajusta no maior
  return out;
};
for (let i = 0; i < N; i++) {
  const v = finalList[i];
  let list;
  if (v < NV) {
    const k = baseMap.get(v);
    bindA[i] = k;
    bindB[i] = k;
    bindT[i] = 0;
    list = topN(infl[k]);
  } else {
    const [A, B, t] = clipDesc[v - NV];
    const ka = baseMap.get(A);
    const kb = baseMap.get(B);
    bindA[i] = ka;
    bindB[i] = kb;
    bindT[i] = t;
    const m = new Map();
    for (const [b, w] of infl[ka]) m.set(b, (m.get(b) || 0) + w * (1 - t));
    for (const [b, w] of infl[kb]) m.set(b, (m.get(b) || 0) + w * t);
    list = topN([...m.entries()]);
  }
  const q = quantizeW(list);
  list.forEach(([b], j) => {
    skinIndex[i * 4 + j] = b;
    skinWeight[i * 4 + j] = q[j];
  });
}
const indices = new Uint16Array(clipped.length * 3);
clipped.forEach((t, i) => {
  indices[i * 3] = finalIndex.get(t[0]);
  indices[i * 3 + 1] = finalIndex.get(t[1]);
  indices[i * 3 + 2] = finalIndex.get(t[2]);
});

// ---------------------------------------------------------------- laços de borda (tampas)
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
const posOfFinal = (i) => {
  const v = finalList[i];
  if (v < NV) return P3(Pdef, v);
  const [A, B, t] = clipDesc[v - NV];
  return add(mul(P3(Pdef, A), 1 - t), mul(P3(Pdef, B), t));
};
for (const l of loops) {
  const bb = [[1e9, 1e9, 1e9], [-1e9, -1e9, -1e9]];
  for (const i of l) {
    const p = posOfFinal(i);
    for (let k = 0; k < 3; k++) {
      bb[0][k] = Math.min(bb[0][k], p[k]);
      bb[1][k] = Math.max(bb[1][k], p[k]);
    }
  }
  console.log(`  laço ${l.length}: min ${bb[0].map((x) => x.toFixed(2))} max ${bb[1].map((x) => x.toFixed(2))}`);
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
  if (ids.length === 0) {
    manifest.push([name, totalEntries, 0, 0]);
    continue;
  }
  const scale = maxAbs / 32767;
  for (const k of ids) tIdx.push(k);
  for (const d of ds) tDelta.push(Math.max(-32767, Math.min(32767, Math.round(d / scale))));
  manifest.push([name, totalEntries, ids.length, scale]);
  totalEntries += ids.length;
}
console.log(`  ${targetNames.length} targets, ${totalEntries} entradas`);

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
  basePosCompact[k * 3] = basePos[v * 3] * SCALE;
  basePosCompact[k * 3 + 1] = basePos[v * 3 + 1] * SCALE;
  basePosCompact[k * 3 + 2] = basePos[v * 3 + 2] * SCALE;
});
const body = packSections([
  ['basePos', basePosCompact],
  ['bindA', bindA],
  ['bindB', bindB],
  ['bindT', bindT],
  ['skinIndex', skinIndex],
  ['skinWeight', skinWeight],
  ['indices', indices],
]);
const tgt = packSections([
  ['idx', Uint16Array.from(tIdx)],
  ['delta', Int16Array.from(tDelta)],
]);

const bodyJson = {
  version: 1,
  units: 'm',
  baseCount: NB,
  vertCount: N,
  triCount: indices.length / 3,
  sections: body.meta,
  bones: bonesOut,
  loops,
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
console.log(`> ok: body.bin ${(body.buf.length / 1024).toFixed(0)} KB (gz ${(gz(body.buf).length / 1024).toFixed(0)} KB), targets.bin ${(tgt.buf.length / 1024).toFixed(0)} KB (gz ${(gz(tgt.buf).length / 1024).toFixed(0)} KB)`);
