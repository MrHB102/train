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
import { RING as TOE_RING } from '../src/garments/shoes.js';

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

// 5) avental: alças contínuas (sem saltos nem voltas), fitas sem acabamento de borda, peitilho por cima do corpete com
//    enchimento e painel sempre por fora da saia (a saia é outro tecido simulado) nos corpos extremos
{
  body.setState({}, neutralDials());
  dresser.applyOutfit('maid');
  const apron = dresser.entries.get('apron');
  const straps = apron.parts.filter((p) => p.kind === 'ribbon');
  let strapIssues = [];
  for (const st of straps) {
    const S = st.spec.samples;
    let prev = null;
    let ymax = -1e9;
    for (let i = 1; i < S.length; i++) {
      const d = [0, 1, 2].map((k) => S[i].point[k] - S[i - 1].point[k]);
      const l = Math.hypot(...d);
      const t = d.map((v) => v / (l || 1));
      if (l < 2e-4 || l > 6e-3) strapIssues.push(`${st.id}: passo de ${(l * 1000).toFixed(1)} mm em ${i}`);
      if (prev && t[0] * prev[0] + t[1] * prev[1] + t[2] * prev[2] < 0.5) strapIssues.push(`${st.id}: volta brusca em ${i}`);
      prev = t;
      ymax = Math.max(ymax, S[i].point[1]);
    }
    if (S.length < 60) strapIssues.push(`${st.id}: só ${S.length} amostras`);
    if (ymax < ctx.L.y.neckBase - 0.05) strapIssues.push(`${st.id}: não passa pelo ombro (topo ${ymax.toFixed(3)})`);
    if (S.at(-1).point[1] > ctx.base?.yW + 0.03 && S.length) strapIssues.push(`${st.id}: não chega ao cós`);
    if (Math.min(...st.obj.geometry.attributes.aEdge.array) < 0.5) strapIssues.push(`${st.id}: aEdge < 0,5 (o picotado descartaria a fita)`);
  }
  check('avental: 2 alças contínuas passando pelo ombro até o cós, sem acabamento de borda', straps.length === 2 && strapIssues.length === 0, strapIssues.slice(0, 3).join('; ') || `${straps.map((x) => x.spec.samples.length).join(' e ')} amostras`);

  dresser.setItemOptions('top', { padding: 1 });
  const bodice = dresser.entries.get('top').parts.find((p) => p.kind === 'shell').spec;
  const bib = apron.parts.find((p) => p.kind === 'shell' && p.spec.name === 'apron.bib').spec;
  let worstLift = Infinity;
  let overlap = 0;
  for (let v = 0; v < ctx.N; v++) {
    if (bodice.field(v, ctx) > 0.002 || bib.field(v, ctx) > 0) continue;
    overlap++;
    worstLift = Math.min(worstLift, bib.offsetFn(v, ctx) - bodice.offsetFn(v, ctx));
  }
  check('avental: peitilho passa por cima do corpete com enchimento máximo (≥ 1 mm de folga em todo o vértice comum)', overlap > 200 && worstLift >= 0.001 - 1e-9, `${overlap} vértices, folga mínima ${(worstLift * 1000).toFixed(2)} mm`);
  dresser.setItemOptions('top', { padding: 0.3 });

  // painel x saia: raio do painel menos raio da saia, na malha de render (o que se vê), 4 s parado
  const renderRadius = (sk, th, y) => {
    const { fu, fv, pos, subU, cols, seamOffset } = sk;
    const nc = fu - 1;
    let ax = 0, az = 0;
    for (let i = 0; i < nc; i++) { ax += pos[i * 3]; az += pos[i * 3 + 2]; }
    ax /= nc; az /= nc;
    let f = (((th / (Math.PI * 2)) % 1) + 1) % 1 * cols * subU - seamOffset * subU;
    f = ((f % (cols * subU)) + cols * subU) % (cols * subU);
    const i0 = Math.floor(f) % nc, i1 = (i0 + 1) % nc, u = f - Math.floor(f);
    const col = (i) => {
      let j = 0;
      while (j < fv - 2 && pos[((j + 1) * fu + i) * 3 + 1] > y) j++;
      const y0 = pos[(j * fu + i) * 3 + 1], y1 = pos[((j + 1) * fu + i) * 3 + 1];
      const t = y0 === y1 ? 0 : Math.min(1, Math.max(0, (y0 - y) / (y0 - y1)));
      const r0 = Math.hypot(pos[(j * fu + i) * 3] - ax, pos[(j * fu + i) * 3 + 2] - az);
      const r1 = Math.hypot(pos[((j + 1) * fu + i) * 3] - ax, pos[((j + 1) * fu + i) * 3 + 2] - az);
      return r0 * (1 - t) + r1 * t;
    };
    return { r: col(i0) * (1 - u) + col(i1) * u, ax, az };
  };
  const apronStates = { ...BODY_STATES, exagerado: { traits: { 'thighs.contact': 1 }, dials: { bustSize: 2.1, glutesSize: 2, hipSize: 1.2, curves: 1.2, anime: 0.9, thickness: 1.2 } } };
  for (const [sname, st] of Object.entries(apronStates)) {
    body.setState({ ...Object.fromEntries(Object.keys(body.values).map((k) => [k, body.values[k]])), ...st.traits }, { ...neutralDials(), ...st.dials });
    dresser.applyOutfit('maid');
    animator.setMotion('none');
    for (let f = 0; f < 240; f++) {
      animator.update(1 / 60);
      colliders.update();
      dresser.update(1 / 60);
    }
    const sk = dresser.entries.get('skirt').parts.find((p) => p.kind === 'drape').cloth;
    const ap = dresser.entries.get('apron').parts.find((p) => p.kind === 'drape').cloth;
    let worst = Infinity;
    let worstAt = '';
    for (let j = 1; j < ap.fv; j++) {
      for (let i = 0; i < ap.fu; i++) {
        const k = (j * ap.fu + i) * 3;
        const sr = renderRadius(sk, 0, ap.pos[k + 1]);
        const dx = ap.pos[k] - sr.ax, dz = ap.pos[k + 2] - sr.az;
        const th = Math.atan2(dx, dz);
        const rs = renderRadius(sk, th, ap.pos[k + 1]).r;
        const gapHere = Math.hypot(dx, dz) - rs;
        if (gapHere < worst) { worst = gapHere; worstAt = `j=${j} i=${i} y=${ap.pos[k + 1].toFixed(3)} th=${(th * 57.3).toFixed(0)}°`; }
      }
    }
    // dobras: vértices de render cuja normal destoa muito da do vizinho (o tecido se dobraria sobre si)
    let folds = 0;
    for (let j = 1; j < ap.fv - 1; j++) {
      for (let i = 1; i < ap.fu - 1; i++) {
        const k = (j * ap.fu + i) * 3;
        for (const o of [k + 3, k + ap.fu * 3]) {
          if (ap.nrm[k] * ap.nrm[o] + ap.nrm[k + 1] * ap.nrm[o + 1] + ap.nrm[k + 2] * ap.nrm[o + 2] < 0.8) folds++;
        }
      }
    }
    check(`avental (${sname}): painel sem dobras agudas`, folds === 0, `${folds} vértices`);
    check(`avental (${sname}): painel por fora da saia na malha de render`, worst > 0.003, `folga mínima ${(worst * 1000).toFixed(1)} mm (${worstAt})`);
  }
  body.setState({}, neutralDials());
}

// 6) sapatos: o bico envolve os dedos (nenhum vértice do pé fora do casco), fecha além do dedão e o corpo sobe a sola
for (const [sname, st] of Object.entries(BODY_STATES)) {
  body.setState({ ...Object.fromEntries(Object.keys(body.values).map((k) => [k, body.values[k]])), ...st.traits }, { ...neutralDials(), ...st.dials });
  dresser.clear();
  check(`sapatos (${sname}): sem peça, sola não levanta o corpo`, body.groundLift === 0, `${body.groundLift}`);
  for (const style of [0, 1]) {
    dresser.addItem('shoes', { options: { style, heel: 0.08 } });
    const boxes = dresser.entries.get('shoes').parts.filter((p) => p.id.startsWith('toe')).map((p) => p.obj);
    let worst = Infinity;
    let tipOver = Infinity;
    let finite = true;
    for (const box of boxes) {
      for (const x of box.position) if (!Number.isFinite(x)) finite = false;
      const P = box.position;
      const nr = (P.length / 3 - 1) / TOE_RING;
      const zOf = (r) => P[r * TOE_RING * 3 + 2];
      const side = box.side;
      const mk = side === 'L' ? ctx.mask.footL : ctx.mask.footR;
      let maxZ = -Infinity;
      for (let v = 0; v < ctx.N; v++) {
        if (mk[v] < 0.5 || (side === 'L') !== (body.pos[v * 3] > 0)) continue;
        const z = body.pos[v * 3 + 2];
        maxZ = Math.max(maxZ, z);
        // só acima da folha de corte do Shell: adiante dela o bico é a única peça
        if (z < zOf(0) + 0.012 || z > zOf(nr - 1)) continue;
        let r = 0;
        while (r < nr - 2 && zOf(r + 1) < z) r++;
        const t = (z - zOf(r)) / (zOf(r + 1) - zOf(r));
        const poly = [];
        for (let i = 0; i < TOE_RING; i++) {
          const a = (r * TOE_RING + i) * 3, b = ((r + 1) * TOE_RING + i) * 3;
          poly.push([P[a] * (1 - t) + P[b] * t, P[a + 1] * (1 - t) + P[b + 1] * t]);
        }
        const px = body.pos[v * 3], py = body.pos[v * 3 + 1];
        let inside = false;
        let dmin = Infinity;
        for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
          const [xi, yi] = poly[i], [xj, yj] = poly[j];
          if ((yi > py) !== (yj > py) && px < ((xj - xi) * (py - yi)) / (yj - yi) + xi) inside = !inside;
          const dx = xj - xi, dy = yj - yi;
          const tt = Math.max(0, Math.min(1, ((px - xi) * dx + (py - yi) * dy) / (dx * dx + dy * dy || 1)));
          dmin = Math.min(dmin, Math.hypot(px - (xi + dx * tt), py - (yi + dy * tt)));
        }
        worst = Math.min(worst, inside ? dmin : -dmin);
      }
      let tipZ = -Infinity;
      for (let k = 0; k < P.length / 3; k++) tipZ = Math.max(tipZ, P[k * 3 + 2]);
      tipOver = Math.min(tipOver, tipZ - maxZ);
    }
    check(`sapatos (${sname}, ${style ? 'botim' : 'scarpin'}): bico sem vértice do pé de fora, fecha além do dedão, valores finitos`, boxes.length === 2 && finite && worst > 0.0005 && tipOver > 0.008, `folga mínima ${(worst * 1000).toFixed(1)} mm, ponta ${(tipOver * 1000).toFixed(1)} mm além dos dedos`);
    check(`sapatos (${sname}, ${style ? 'botim' : 'scarpin'}): o corpo sobe a espessura da sola`, Math.abs(body.groundLift - 0.0066) < 1e-9 && Math.abs(body.group.position.y - (-body.floorY + 0.0066)) < 1e-9, `${(body.groundLift * 1000).toFixed(1)} mm`);
  }
  dresser.clear();
  check(`sapatos (${sname}): ao tirar, o corpo volta ao chão`, body.groundLift === 0 && Math.abs(body.group.position.y + body.floorY) < 1e-9, `${body.groundLift}`);
}

body.setState({}, neutralDials());

const fail = results.filter((r) => !r.ok).length;
console.log(`\n${results.length - fail}/${results.length} verificações ok`);
process.exit(fail ? 1 : 0);
