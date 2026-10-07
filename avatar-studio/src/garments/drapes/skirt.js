// Saia (Drape): grade em anel presa na cintura, ajustada ao envelope do corpo atual.
import * as THREE from 'three';
import { Cloth } from '../../physics/cloth.js';

const smoothstep = (a, b, x) => {
  const t = Math.min(1, Math.max(0, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
};

/** Envelope radial do corpo (máx. distância ao eixo) por ângulo, em faixas de altura. */
export function bodyEnvelope(body, ys, cols, axis) {
  const pos = body.pos;
  const n = body.N;
  const band = 0.014;
  const env = ys.map(() => new Float32Array(cols));
  for (let v = 0; v < n; v++) {
    const y = pos[v * 3 + 1];
    for (let r = 0; r < ys.length; r++) {
      if (Math.abs(y - ys[r]) > band) continue;
      const dx = pos[v * 3] - axis.x;
      const dz = pos[v * 3 + 2] - axis.z;
      const rad = Math.hypot(dx, dz);
      const th = Math.atan2(dx, dz); // 0 = frente (+z), cresce para +x (esquerda do corpo)
      const c = Math.round(((th + 2 * Math.PI) % (2 * Math.PI)) / ((2 * Math.PI) / cols)) % cols;
      if (rad > env[r][c]) env[r][c] = rad;
    }
  }
  // preenche buracos e suaviza
  for (const e of env) {
    for (let it = 0; it < 2; it++) {
      for (let c = 0; c < cols; c++) {
        const a = e[(c + cols - 1) % cols], b = e[(c + 1) % cols];
        if (e[c] === 0) e[c] = (a + b) / 2 || Math.max(a, b);
        else e[c] = Math.max(e[c], 0.5 * e[c] + 0.25 * (a + b));
      }
    }
  }
  return env;
}

/**
 * params: { length (m, da cintura até a barra), flare (0..1.2), pleats (0 = liso), rows, cols,
 *           yWaist (m, opcional: deslocamento em relação à cintura natural), extra (m: franzido/anágua) }
 */
export function buildSkirtRest(body, ctx, params) {
  const { length, flare, pleats = 0, rows = 9, cols = 32, yShift = 0, widen = 0 } = params;
  const rl = body.pkg.meta.rulers;
  const P = body.morph.positions;
  let yW = 0;
  for (const v of rl.waist) yW += P[v * 3 + 1];
  yW = yW / rl.waist.length + yShift;
  // eixo do corpo na altura da cintura: centro da seção
  let minZ = 1e9, maxZ = -1e9;
  for (let v = 0; v < body.N; v++) {
    if (Math.abs(body.pos[v * 3 + 1] - yW) < 0.012) {
      minZ = Math.min(minZ, body.pos[v * 3 + 2]);
      maxZ = Math.max(maxZ, body.pos[v * 3 + 2]);
    }
  }
  const axis = new THREE.Vector3(0, yW, (minZ + maxZ) / 2 - 0.004);
  const ys = [];
  for (let r = 0; r < rows; r++) ys.push(yW - (length * r) / (rows - 1));
  const env = bodyEnvelope(body, ys, cols, axis);
  const wEnv = env[0];
  const rest = new Float32Array(rows * cols * 3);
  const hip = Math.max(...env[Math.min(rows - 1, Math.round(rows * 0.25))]);
  for (let r = 0; r < rows; r++) {
    const t = r / (rows - 1);
    for (let c = 0; c < cols; c++) {
      const th = (c / cols) * 2 * Math.PI;
      const rW = wEnv[c] + 0.006;
      const hem = Math.max(rW, env[Math.min(rows - 1, Math.round(rows * 0.25))][c]) + 0.025 + flare * (0.07 + 0.55 * length) + widen;
      let rad = rW + (hem - rW) * Math.pow(t, 0.85);
      rad = Math.max(rad, env[r][c] + 0.008 + 0.006 * t);
      if (pleats > 0) rad *= 1 + 0.04 * Math.pow(t, 0.7) * Math.sin(th * pleats);
      const k = (r * cols + c) * 3;
      rest[k] = axis.x + Math.sin(th) * rad;
      rest[k + 1] = ys[r];
      rest[k + 2] = axis.z + Math.cos(th) * rad;
    }
  }
  const circ = 2 * Math.PI * (Math.max(...wEnv) + hip) * 0.5;
  return { rest, rows, cols, length, yW, circ, axis };
}

export function createSkirtCloth(body, ctx, params) {
  const rest = buildSkirtRest(body, ctx, params);
  const attach = body.rig.index.get('root');
  const cloth = new Cloth(body, {
    rows: rest.rows,
    cols: rest.cols,
    wrap: true,
    rest: rest.rest,
    attach,
    pinRows: 1,
    shape: [params.shapeTop ?? 0.5, params.shapeHem ?? 0.035],
    subU: params.pleats > 0 ? 4 : 3,
    subV: 3,
    hemLength: rest.length,
    seamOffset: Math.floor(rest.cols / 2), // a emenda do padrão fica nas costas
    uv: (fr, fc) => [(fc / rest.cols) * rest.circ, (fr / (rest.rows - 1)) * rest.length],
  });
  cloth.meta = rest;
  cloth.params = params;
  return cloth;
}

/** Reajusta a saia ao corpo atual (após morph): recalcula o formato de repouso e recomeça a simulação. */
export function refitSkirt(cloth, body, ctx, { soft = true } = {}) {
  const rest = buildSkirtRest(body, ctx, cloth.params);
  cloth.meta = rest;
  if (soft) cloth.retarget(rest.rest);
  else cloth.setRest(rest.rest);
}
