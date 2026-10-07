// Peças de tecido simulado (Drapes): saia e avental. Ficam presas à cintura (osso raiz), seguem o corpo
// quando ele muda (sem reiniciar a simulação) e colidem com cápsulas das pernas, quadril e glúteos.
import * as THREE from 'three';
import { Cloth } from '../physics/cloth.js';
import { createSkirtCloth, refitSkirt, buildSkirtRest } from './drapes/skirt.js';
import { smoothstep, excludeLimbs } from './fields.js';

const clamp01 = (x) => Math.min(1, Math.max(0, x));

function drapeMesh(cloth, material, body) {
  const mesh = new THREE.Mesh(cloth.geometry, material);
  mesh.frustumCulled = false;
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  body.group.add(mesh);
  return mesh;
}

/** Atualização comum: refaz o formato de repouso (no máx. 10×/s) enquanto o corpo muda e avança a física. */
function makeUpdater(cloth, body, dresser, refit) {
  let pending = false;
  let acc = 0;
  const off = body.onChange(() => (pending = true));
  return {
    update(dt) {
      acc += dt;
      if (pending && acc > 0.1) {
        pending = false;
        acc = 0;
        refit();
      }
      cloth.stiffness = dresser.cloth.stiffness * (cloth.userStiffness ?? 1);
      cloth.step(dt, dresser.colliders.update(), dresser.cloth.wind);
    },
    off,
  };
}

// ------------------------------------------------------------------------------------------------ saia
export function skirt(ctx, o, { dresser, entry }) {
  const body = ctx.body;
  const params = { length: o.length, flare: o.flare, pleats: o.pleats ? 26 : 0, yShift: o.rise };
  const cloth = createSkirtCloth(body, ctx, params);
  cloth.userStiffness = o.stiffness;
  const mesh = drapeMesh(cloth, entry.mat, body);
  const up = makeUpdater(cloth, body, dresser, () => refitSkirt(cloth, body, ctx));
  return {
    drapes: [
      {
        id: 'skirt',
        object: { dispose() { up.off(); mesh.removeFromParent(); cloth.geometry.dispose(); } },
        update: (dt) => up.update(dt),
      },
    ],
  };
}

// ------------------------------------------------------------------------------------------------ avental
/** Raio do anel de saia (rest) em (ângulo, profundidade abaixo da cintura), por interpolação bilinear. */
function skirtRadius(rest, rows, cols, axis, length) {
  const rad = (r, c) => {
    const k = (r * cols + (((c % cols) + cols) % cols)) * 3;
    return Math.hypot(rest[k] - axis.x, rest[k + 2] - axis.z);
  };
  return (theta, d) => {
    const fr = clamp01(d / length) * (rows - 1);
    const r0 = Math.min(rows - 2, Math.floor(fr));
    const t = fr - r0;
    const fc = (((theta / (Math.PI * 2)) % 1) + 1) % 1 * cols;
    const c0 = Math.floor(fc);
    const u = fc - c0;
    const a = rad(r0, c0) * (1 - u) + rad(r0, c0 + 1) * u;
    const b = rad(r0 + 1, c0) * (1 - u) + rad(r0 + 1, c0 + 1) * u;
    return a * (1 - t) + b * t;
  };
}

export function apron(ctx, o, { dresser, entry }) {
  const body = ctx.body;
  const sk = dresser.entries.get('skirt');
  const skLen = sk ? sk.options.length : o.length + 0.05;
  const len = Math.min(o.length, skLen - 0.015);
  const skParams = sk ? { length: sk.options.length, flare: sk.options.flare, pleats: 0, yShift: sk.options.rise } : { length: skLen, flare: 0.8, pleats: 0, yShift: 0 };
  const rows = 9;
  const cols = 13;
  const buildRest = () => {
    const full = buildSkirtRest(body, ctx, { ...skParams, rows: 13, cols: 64 });
    const radius = skirtRadius(full.rest, 13, 64, full.axis, skParams.length);
    const rest = new Float32Array(rows * cols * 3);
    for (let r = 0; r < rows; r++) {
      const t = r / (rows - 1);
      const d = len * t;
      const half = 0.72 + (0.98 - 0.72) * Math.pow(t, 0.8);
      for (let c = 0; c < cols; c++) {
        const f = (c / (cols - 1)) * 2 - 1;
        const th = f * half;
        const rad = radius(th, d) + 0.011 + 0.008 * t;
        const k = (r * cols + c) * 3;
        rest[k] = full.axis.x + Math.sin(th) * rad;
        rest[k + 1] = full.yW - d;
        rest[k + 2] = full.axis.z + Math.cos(th) * rad;
      }
    }
    return { rest, yW: full.yW };
  };
  const base = buildRest();
  const widthM = 0.2;
  const cloth = new Cloth(body, {
    rows,
    cols,
    wrap: false,
    rest: base.rest,
    attach: body.rig.index.get('root'),
    pinRows: 1,
    shape: [0.55, 0.04],
    subU: 3,
    subV: 3,
    hemLength: len,
    uv: (fr, fc) => [(fc / (cols - 1) - 0.5) * widthM, (fr / (rows - 1)) * len],
  });
  cloth.userStiffness = 1;
  const mesh = drapeMesh(cloth, entry.mat, body);
  const up = makeUpdater(cloth, body, dresser, () => cloth.retarget(buildRest().rest));
  const out = {
    drapes: [{ id: 'apron.panel', object: { dispose() { up.off(); mesh.removeFromParent(); cloth.geometry.dispose(); } }, update: (dt) => up.update(dt) }],
    shells: [],
  };

  // cós na cintura (+ peitilho com alças) recortados da superfície, por cima da saia/corpete
  const { L, pos } = ctx;
  const yc = base.yW;
  const limbs = excludeLimbs(ctx, { thresh: 0.4 });
  const band = {
    name: 'apron.band',
    layer: 4,
    offsetFn: () => 0.0052,
    edge: () => 1, // sem acabamento nas bordas do cós (o recorte ondulado é só na barra do painel)
    field: (v) => Math.max(Math.abs(pos[v * 3 + 1] - yc) - 0.0165, limbs(v)),
    uv: (v) => [Math.atan2(pos[v * 3], pos[v * 3 + 2]) * 0.16, pos[v * 3 + 1]],
    uvPeriod: Math.PI * 2 * 0.16,
    castShadow: true,
  };
  out.shells.push(band);
  if (o.bib) {
    const yLo = yc + 0.01;
    const yHi = L.y.bust + 0.085;
    const yStrapTop = L.y.neckBase - 0.012;
    const halfW = (y) => 0.088 + 0.03 * smoothstep(yLo, L.y.underbust, y) - 0.028 * smoothstep(L.y.bust, yHi, y);
    out.shells.push({
      name: 'apron.bib',
      layer: 4,
      offsetFn: () => 0.0052,
      edge: () => 1,
      field: (v) => {
        const x = Math.abs(pos[v * 3]), y = pos[v * 3 + 1], z = pos[v * 3 + 2];
        const bib = Math.max(yLo - y, y - yHi, x - halfW(y), 0.03 - z);
        const strap = Math.max(Math.abs(x - 0.0565) - 0.0115, yc - y, y - yStrapTop, limbs(v));
        return Math.min(bib, strap);
      },
      uv: (v) => [pos[v * 3], pos[v * 3 + 1]],
      castShadow: true,
    });
  }
  return out;
}
