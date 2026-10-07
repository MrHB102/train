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
    // dilata uma coluna e suaviza com [1 2 1]/4: o resultado nunca fica abaixo do corpo, mas os degraus viram rampas
    // (o busto grande pendendo na altura da cintura deixava o anel com "penhascos" que dobravam o tecido)
    const src = Float32Array.from(e);
    const dil = new Float32Array(cols);
    for (let c = 0; c < cols; c++) dil[c] = Math.max(src[(c + cols - 1) % cols], src[c], src[(c + 1) % cols]);
    for (let c = 0; c < cols; c++) e[c] = 0.25 * dil[(c + cols - 1) % cols] + 0.5 * dil[c] + 0.25 * dil[(c + 1) % cols];
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

/**
 * Superfície da saia simulada como função (ângulo, altura) → raio, para peças que ficam por cima dela (o painel do
 * avental). Lê a malha de render (a que se vê, com a interpolação suave entre partículas): a coluna i é o ângulo
 * (i + seamOffset·subU) / (cols·subU) · 2π, com 0 = frente e + para +x.
 */
export class SkirtSurface {
  /** Lê as posições atuais da malha de render da saia. */
  read(cloth) {
    const { fu, fv, pos, subU, seamOffset } = cloth;
    const nc = fu - 1; // a última coluna repete a primeira
    this.nc = nc;
    this.rows = fv;
    this.shift = seamOffset * subU;
    let ax = 0;
    let az = 0;
    for (let i = 0; i < nc; i++) {
      ax += pos[i * 3];
      az += pos[i * 3 + 2];
    }
    this.ax = ax / nc;
    this.az = az / nc;
    const rho = (this.rho ??= new Float32Array(fv * nc));
    const ys = (this.ys ??= new Float32Array(fv * nc));
    for (let j = 0; j < fv; j++) {
      for (let i = 0; i < nc; i++) {
        const k = (j * fu + i) * 3;
        rho[j * nc + i] = Math.hypot(pos[k] - this.ax, pos[k + 2] - this.az);
        ys[j * nc + i] = pos[k + 1];
      }
    }
  }

  _column(i, y) {
    const { rows, nc, rho, ys } = this;
    let j = 0;
    while (j < rows - 2 && ys[(j + 1) * nc + i] > y) j++;
    const y0 = ys[j * nc + i];
    const y1 = ys[(j + 1) * nc + i];
    const t = y0 === y1 ? 0 : Math.min(1, Math.max(0, (y0 - y) / (y0 - y1)));
    return rho[j * nc + i] * (1 - t) + rho[(j + 1) * nc + i] * t;
  }

  /** Raio da saia (a partir do eixo lido) no ângulo `theta` (rad, 0 = frente, + para +x) e altura `y`. */
  radiusAt(theta, y) {
    const n = this.nc;
    let f = ((((theta / (Math.PI * 2)) % 1) + 1) % 1) * n - this.shift;
    f = ((f % n) + n) % n;
    const i0 = Math.floor(f);
    const u = f - i0;
    return this._column(i0, y) * (1 - u) + this._column((i0 + 1) % n, y) * u;
  }
}

export function createSkirtCloth(body, ctx, params) {
  const rest = buildSkirtRest(body, ctx, { ...params, pleats: 0 }); // as pregas ficam só na malha de render
  // raio médio de cada anel de repouso, interpolado entre linhas
  const meanR = [];
  for (let r = 0; r < rest.rows; r++) {
    let sum = 0;
    for (let c = 0; c < rest.cols; c++) {
      const k = (r * rest.cols + c) * 3;
      sum += Math.hypot(rest.rest[k] - rest.axis.x, rest.rest[k + 2] - rest.axis.z);
    }
    meanR.push(sum / rest.cols);
  }
  const ringR = (fr) => {
    const r0 = Math.min(rest.rows - 2, Math.floor(fr));
    const t = fr - r0;
    return meanR[r0] * (1 - t) + meanR[r0 + 1] * t;
  };
  // distância ao longo do tecido (da cintura para baixo), média das colunas: a saia rodada é inclinada, então a
  // altura subestimaria o comprimento e as bolinhas ficariam compridas
  const slant = [0];
  for (let r = 1; r < rest.rows; r++) {
    let sum = 0;
    for (let c = 0; c < rest.cols; c++) {
      const a = ((r - 1) * rest.cols + c) * 3;
      const b = (r * rest.cols + c) * 3;
      sum += Math.hypot(rest.rest[b] - rest.rest[a], rest.rest[b + 1] - rest.rest[a + 1], rest.rest[b + 2] - rest.rest[a + 2]);
    }
    slant.push(slant[r - 1] + sum / rest.cols);
  }
  const slantAt = (fr) => {
    const r0 = Math.min(rest.rows - 2, Math.floor(fr));
    const t = fr - r0;
    return slant[r0] * (1 - t) + slant[r0 + 1] * t;
  };
  const attach = body.rig.index.get('root');
  const cloth = new Cloth(body, {
    rows: rest.rows,
    cols: rest.cols,
    wrap: true,
    rest: rest.rest,
    attach,
    pinRows: 1,
    shape: [params.shapeTop ?? 0.5, params.shapeHem ?? 0.035],
    subU: params.pleats > 0 ? 6 : 3,
    pleats: params.pleats > 0 ? { count: params.pleats, amp: 0.026, power: 1.1 } : null,
    subV: 3,
    hemLength: rest.length,
    seamOffset: Math.floor(rest.cols / 2), // a emenda do padrão fica nas costas
    // padrão em metros SOBRE o tecido: u = arco no raio da própria linha (com 0 na frente), então bolinhas e
    // xadrez têm o mesmo tamanho na cintura e na barra (com u fixo elas se espremiam na cintura e esticavam na barra)
    uv: (fr, fc) => [(((fc + Math.floor(rest.cols / 2)) / rest.cols) * 2 * Math.PI - 2 * Math.PI) * ringR(fr), slantAt(fr)],
  });
  cloth.meta = rest;
  cloth.params = params;
  return cloth;
}

/** Reajusta a saia ao corpo atual (após morph): recalcula o formato de repouso e recomeça a simulação. */
export function refitSkirt(cloth, body, ctx, { soft = true } = {}) {
  const rest = buildSkirtRest(body, ctx, { ...cloth.params, pleats: 0 });
  cloth.meta = rest;
  if (soft) cloth.retarget(rest.rest);
  else cloth.setRest(rest.rest);
}
