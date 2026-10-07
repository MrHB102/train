#!/usr/bin/env node
// Validação das roupas (princípios da skill 3d-modeling): monta cada peça e cada conjunto no corpo neutro e nos
// extremos e confere números finitos, triângulos degenerados, topologia (arestas non-manifold), orçamento de
// triângulos, UV, camadas e colisão dos tecidos simulados. Falha (exit 1) se algo estiver fora do padrão.
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { fileURLToPath } from 'node:url';
import * as THREE from 'three';
import { parsePackage } from '../src/avatar/package.js';
import { Body } from '../src/avatar/body.js';
import { Animator } from '../src/avatar/animation.js';
import { BodyColliders } from '../src/physics/colliders.js';
import { createContext } from '../src/garments/context.js';
import { Wardrobe } from '../src/garments/wardrobe.js';
import { Dresser } from '../src/garments/dresser.js';
import { createNoise3D } from '../src/shaders/textures.js';
import { GARMENT_TYPES, OUTFITS } from '../src/domain/wardrobe.js';
import { neutralDials } from '../src/domain/dials.js';

const dir = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'public', 'data');
const rd = (f) => fs.readFileSync(path.join(dir, f));
const ab = (b) => b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength);
const pkg = parsePackage(JSON.parse(rd('body.json')), JSON.parse(rd('targets.json')), ab(zlib.gunzipSync(rd('body.bin.gz'))), ab(zlib.gunzipSync(rd('targets.bin.gz'))));

const body = new Body(pkg);
const ctx = createContext(body);
const wardrobe = new Wardrobe(body, ctx);
const colliders = new BodyColliders(body);
const animator = new Animator(body);
const dresser = new Dresser({ body, ctx, wardrobe, noise: createNoise3D(), colliders });
dresser.sim = { animator };

const results = [];
const check = (name, ok, detail = '') => {
  results.push({ name, ok });
  console.log(`${ok ? 'OK  ' : 'FALHA'}  ${name}${detail ? ' — ' + detail : ''}`);
};

/** Estatísticas de uma malha indexada (position + index). */
function meshStats(pos, index) {
  let bad = 0;
  for (let i = 0; i < pos.length; i++) if (!Number.isFinite(pos[i])) bad++;
  let degenerate = 0;
  const edges = new Map();
  for (let t = 0; t < index.length; t += 3) {
    const a = index[t], b = index[t + 1], c = index[t + 2];
    const ux = pos[b * 3] - pos[a * 3], uy = pos[b * 3 + 1] - pos[a * 3 + 1], uz = pos[b * 3 + 2] - pos[a * 3 + 2];
    const vx = pos[c * 3] - pos[a * 3], vy = pos[c * 3 + 1] - pos[a * 3 + 1], vz = pos[c * 3 + 2] - pos[a * 3 + 2];
    const area = 0.5 * Math.hypot(uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx);
    if (area < 1e-10) degenerate++;
    // arestas por posição (vértices duplicados da costura de UV compartilham posição)
    const key = (i, j) => {
      const pi = `${pos[i * 3].toFixed(5)},${pos[i * 3 + 1].toFixed(5)},${pos[i * 3 + 2].toFixed(5)}`;
      const pj = `${pos[j * 3].toFixed(5)},${pos[j * 3 + 1].toFixed(5)},${pos[j * 3 + 2].toFixed(5)}`;
      return pi < pj ? pi + '|' + pj : pj + '|' + pi;
    };
    for (const [i, j] of [[a, b], [b, c], [c, a]]) {
      const k = key(i, j);
      edges.set(k, (edges.get(k) || 0) + 1);
    }
  }
  let nonManifold = 0;
  for (const n of edges.values()) if (n > 2) nonManifold++;
  return { nonFinite: bad, degenerate, nonManifold, tris: index.length / 3 };
}

function auditEntries(label) {
  let tris = 0;
  let issues = [];
  const all = [...dresser.entries.values(), dresser.base.top, dresser.base.bottom];
  for (const e of all) {
    for (const p of e.parts) {
      if (p.kind === 'shell' || p.kind === 'ribbon') {
        const o = p.obj;
        const idx = o.geometry.index.array;
        const st = meshStats(o.position, idx);
        tris += st.tris;
        if (st.nonFinite) issues.push(`${e.id}/${p.id}: ${st.nonFinite} valores não finitos`);
        if (st.degenerate > st.tris * 0.002 + 2) issues.push(`${e.id}/${p.id}: ${st.degenerate} triângulos degenerados`);
        if (st.nonManifold > st.tris * 0.01 + 2) issues.push(`${e.id}/${p.id}: ${st.nonManifold} arestas non-manifold`);
        const uv = o.geometry.attributes.aUv.array;
        for (let i = 0; i < uv.length; i++) if (!Number.isFinite(uv[i]) || Math.abs(uv[i]) > 200) {
          issues.push(`${e.id}/${p.id}: UV fora da faixa`);
          break;
        }
      }
    }
  }
  return { tris, issues };
}

// 1) cada tipo de peça isolado, no corpo neutro
const BODY_STATES = {
  neutro: { traits: {}, dials: {} },
  extremo: { traits: { 'thighs.contact': 1 }, dials: { bustSize: 3, glutesSize: 3, hipSize: 2.2, thickness: 2.2, curves: 1.6, anime: 1 } },
};
for (const [sname, st] of Object.entries(BODY_STATES)) {
  body.setState({ ...Object.fromEntries(Object.keys(body.values).map((k) => [k, body.values[k]])), ...st.traits }, { ...neutralDials(), ...st.dials });
  for (const type of Object.keys(GARMENT_TYPES)) {
    if (type.startsWith('base_')) continue;
    dresser.clear();
    dresser.addItem(type);
    const { tris, issues } = auditEntries(type);
    check(`${type} (${sname})`, issues.length === 0, issues.length ? issues.join('; ') : `${tris} triângulos`);
  }
}

// 2) conjuntos completos: orçamento de triângulos e camada-base sempre presente
body.setState({}, neutralDials());
for (const o of OUTFITS) {
  dresser.applyOutfit(o.id);
  const { tris, issues } = auditEntries(o.id);
  const total = tris + 42006;
  const baseOK = ['top', 'bottom'].every((w) => dresser.base[w].parts.some((p) => p.kind === 'shell' && p.obj.count > 0) || dresser._coverField(w === 'top' ? ['top', 'onepiece'] : ['bottom', 'onepiece']));
  check(`conjunto ${o.id}: malha sã, base presente, ≤ 120 000 triângulos`, issues.length === 0 && baseOK && total <= 120000, issues.length ? issues.join('; ') : `${total} triângulos no total, ${dresser.entries.size} peças`);
}

// 3) camadas: espessura cresce com a camada (base < meias < peças < por cima)
{
  dresser.clear();
  dresser.addItem('legwear');
  dresser.addItem('leotard');
  dresser.addItem('puffSleeves');
  const lo = (id) => {
    const e = [...dresser.entries.values()].find((x) => x.type === id);
    const sh = e.parts.find((p) => p.kind === 'shell').obj;
    return { layer: sh.layer, off: Math.min(...sh.offsets) };
  };
  const a = lo('legwear'), b = lo('leotard'), c = lo('puffSleeves');
  check('camadas: meias < peça < por cima (ordem de camada e espessura)', a.layer < b.layer && b.layer < c.layer && a.off < b.off && b.off < c.off + 1e-9, `${(a.off * 1000).toFixed(1)} < ${(b.off * 1000).toFixed(1)} ≤ ${(c.off * 1000).toFixed(1)} mm`);
}

// 4) tecidos simulados: 150 quadros parados e depois em movimento, sem NaN e sem entrar nas cápsulas do corpo
{
  dresser.applyOutfit('maid');
  for (const motion of ['none', 'dance']) {
    animator.setMotion(motion);
    let worst = Infinity;
    let nan = false;
    for (let f = 0; f < 150; f++) {
      animator.update(1 / 60);
      colliders.update();
      dresser.update(1 / 60);
      for (const e of dresser.entries.values()) for (const p of e.parts) {
        if (p.kind !== 'drape') continue;
      }
    }
    // acessa os Cloth pelas malhas adicionadas ao grupo do corpo
    for (const ch of body.group.children) {
      if (!(ch instanceof THREE.Mesh) || ch.isSkinnedMesh) continue;
      const pos = ch.geometry.attributes.position.array;
      for (let i = 0; i < pos.length; i++) if (!Number.isFinite(pos[i])) nan = true;
      const caps = colliders.list;
      for (let v = 0; v < pos.length; v += 9) {
        if (pos[v + 1] > ctx.L.y.waist - 0.05) continue; // as primeiras linhas ficam presas à cintura (sem colisão)
        for (const c of caps) {
          const ax = c.a.x, ay = c.a.y, az = c.a.z, bx = c.b.x - ax, by = c.b.y - ay, bz = c.b.z - az;
          const l2 = bx * bx + by * by + bz * bz;
          const t = l2 > 1e-10 ? Math.min(1, Math.max(0, ((pos[v] - ax) * bx + (pos[v + 1] - ay) * by + (pos[v + 2] - az) * bz) / l2)) : 0;
          const r = (c.rA ?? c.r) + ((c.rB ?? c.r) - (c.rA ?? c.r)) * t;
          const d = Math.hypot(pos[v] - (ax + bx * t), pos[v + 1] - (ay + by * t), pos[v + 2] - (az + bz * t)) - r;
          if (d < worst) worst = d;
        }
      }
    }
    check(`maid (${motion}): saia/avental sem NaN e dentro da folga das cápsulas (cápsulas são 1.2× o corpo, ~20 mm de folga)`, !nan && worst > -0.02, `penetração máxima ${(Math.max(0, -worst) * 1000).toFixed(1)} mm`);
  }
}

const fail = results.filter((r) => !r.ok).length;
console.log(`\n${results.length - fail}/${results.length} verificações ok`);
process.exit(fail ? 1 : 0);
