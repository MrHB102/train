// Campos de corte reutilizáveis para Shells: cada função devolve field(v) -> metros (<= 0 dentro da peça).
// Combine com max (interseção) e min (união). Tudo no espaço de referência (mulher padrão), y para cima.
import { getSurface } from './ribbon.js';
export const clamp01 = (x) => Math.min(1, Math.max(0, x));
export const smoothstep = (a, b, x) => {
  const t = clamp01((x - a) / (b - a));
  return t * t * (3 - 2 * t);
};
export const mix = (a, b, t) => a + (b - a) * t;

/** Exclui braços/ombros: a peça não cobre onde o peso de braço/ombro passa de `thresh`. */
export function excludeLimbs(ctx, { thresh = 0.45, shoulders = true } = {}) {
  const { mask } = ctx;
  return (v) => (mask.arm[v] + (shoulders ? mask.shoulderL[v] + mask.shoulderR[v] : 0) - thresh) * 0.06;
}

/** Só o braço (mantém o ombro): para peças que cobrem o ombro mas não descem pelo braço. */
export function excludeArms(ctx, thresh = 0.45) {
  const { mask } = ctx;
  return (v) => (mask.arm[v] - thresh) * 0.06;
}

/** Faixa horizontal entre duas alturas (y0 embaixo, y1 em cima); funções permitem variar com x/z. */
export function yBand(ctx, y0, y1) {
  const { pos } = ctx;
  const lo = typeof y0 === 'function' ? y0 : () => y0;
  const hi = typeof y1 === 'function' ? y1 : () => y1;
  return (v) => {
    const x = pos[v * 3], y = pos[v * 3 + 1], z = pos[v * 3 + 2];
    return Math.max(lo(x, y, z) - y, y - hi(x, y, z));
  };
}

/** Anel ao longo do eixo do pescoço entre as distâncias d0 e d1 (m) a partir da base do pescoço. */
export function neckBand(ctx, d0, d1, thresh = 0.5) {
  const { L, mask, pos } = ctx;
  const b = L.neck.base;
  const a = L.neckAxis;
  return (v) => {
    const d = (pos[v * 3] - b.x) * a.x + (pos[v * 3 + 1] - b.y) * a.y + (pos[v * 3 + 2] - b.z) * a.z;
    return Math.max(d0 - d, d - d1, (thresh - mask.neck[v]) * 0.05);
  };
}

/**
 * Abertura de perna em linha reta no plano x-y (maiô cavado): do quadril (xHip, yHip) até perto da virilha
 * (xCrotch, yCrotch). Positivo = lado da perna (removido). Nas costas a linha desce `backDrop` (mais cobertura).
 */
export function highLegCut(ctx, { yHip, yCrotch, xHip = 0.175, xCrotch = 0.012, backDrop = 0.05, frontDrop = 0 }) {
  const { pos } = ctx;
  const dx = xCrotch - xHip;
  const dy = yCrotch - yHip;
  const len = Math.hypot(dx, dy);
  return (v) => {
    const x = Math.abs(pos[v * 3]);
    const y = pos[v * 3 + 1];
    const z = pos[v * 3 + 2];
    const cross = (dx * (y - yHip) - dy * (x - xHip)) / len;
    const drop = backDrop * smoothstep(0.02, -0.07, z) - frontDrop * smoothstep(0.02, 0.1, z);
    return cross - drop;
  };
}

/** Plano perpendicular ao eixo da coxa/canela, a uma distância `d` (m) do quadril/joelho (positivo = abaixo). */
export function legPlane(ctx, side, from, d, axisName = 'thighAxis') {
  const { L, pos } = ctx;
  const o = L[from][side];
  const a = L[axisName][side];
  const s = side === 'L' ? 1 : -1;
  return (v) => {
    const x = pos[v * 3];
    if (s * x < -0.004) return -1;
    return (x - o.x) * a.x + (pos[v * 3 + 1] - o.y) * a.y + (pos[v * 3 + 2] - o.z) * a.z - d;
  };
}

/** Coordenadas de padrão cilíndricas (arco em metros, altura) ao redor de um eixo vertical em (cx, cz). */
export function cylUv(ctx, cx = 0, cz = 0, radius = 0.15) {
  const { pos } = ctx;
  return (v) => [Math.atan2(pos[v * 3] - cx, pos[v * 3 + 2] - cz) * radius, pos[v * 3 + 1]];
}

/** Padrão cilíndrico por perna (eixo vertical em x = ±0.1): u = arco em torno da perna, v = altura. */
export function legUv(ctx, radius = 0.065) {
  const { pos } = ctx;
  return (v) => {
    const x = pos[v * 3];
    const cx = x >= 0 ? 0.105 : -0.105;
    return [Math.atan2(x - cx, pos[v * 3 + 2] - 0.02) * radius, pos[v * 3 + 1]];
  };
}

/**
 * Coordenada ao longo da perna (m) por vértice: distância axial a partir do tornozelo, seguindo
 * tornozelo → joelho → quadril (com mistura suave no joelho) e continuando acima do quadril. Negativa nos pés.
 * Meias, legging e shorts usam isso para cortar em planos perpendiculares à perna.
 */
export function legAxial(ctx) {
  if (ctx._legU) return ctx._legU;
  const { L, pos, N } = ctx;
  const out = new Float32Array(N);
  const seg = {};
  for (const side of ['L', 'R']) {
    const A = L.ankle[side], K = L.knee[side], H = L.hip[side];
    const us = K.clone().sub(A);
    const lshin = us.length();
    us.normalize();
    const ut = H.clone().sub(K).normalize();
    const nb = us.clone().add(ut).normalize();
    seg[side] = { A, K, us, ut, nb, lshin, lthigh: H.distanceTo(K) };
  }
  for (let v = 0; v < N; v++) {
    const x = pos[v * 3], y = pos[v * 3 + 1], z = pos[v * 3 + 2];
    const g = seg[x >= 0 ? 'L' : 'R'];
    const px = x - g.A.x, py = y - g.A.y, pz = z - g.A.z;
    const ushin = px * g.us.x + py * g.us.y + pz * g.us.z;
    const kx = x - g.K.x, ky = y - g.K.y, kz = z - g.K.z;
    const uthigh = g.lshin + kx * g.ut.x + ky * g.ut.y + kz * g.ut.z;
    const w = smoothstep(-0.04, 0.04, kx * g.nb.x + ky * g.nb.y + kz * g.nb.z);
    out[v] = ushin + (uthigh - ushin) * w;
  }
  ctx._legU = out;
  ctx._legLen = { shin: seg.L.lshin, thigh: seg.L.lthigh };
  return out;
}

const RING_BINS = 96;

/**
 * Anéis horizontais do tronco na malha de referência: para cada altura (a cada 1 cm, da virilha à base do pescoço), o
 * arco (m) com sinal a partir da linha central da frente, medido SOBRE a superfície (raios saindo do centro da
 * seção), e a circunferência. É o que dá a um padrão (bolinhas, xadrez) a mesma escala no busto e na cintura.
 */
export function torsoRings(ctx) {
  if (ctx._torsoRings) return ctx._torsoRings;
  const S = getSurface(ctx);
  const { L } = ctx;
  const y0 = L.y.crotch + 0.01;
  const dy = 0.01;
  const n = Math.ceil((L.y.neckBase + 0.02 - y0) / dy) + 1;
  const C = RING_BINS;
  const zc = new Float32Array(n);
  const circ = new Float32Array(n);
  const arc = new Float32Array(n * (C + 1));
  const R = new Float32Array(C + 1);
  let have = false;
  for (let k = 0; k < n; k++) {
    const y = y0 + k * dy;
    const f = S.cast([0, y, 0.8], [0, 0, -1], 1.6);
    const b = S.cast([0, y, -0.8], [0, 0, 1], 1.6);
    let valid = !!(f && b);
    if (valid) {
      const z0 = (f.point[2] + b.point[2]) / 2;
      let ok = 0;
      for (let c = 0; c <= C; c++) {
        const th = -Math.PI + (c * 2 * Math.PI) / C;
        const h = c === C ? null : S.cast([0, y, z0], [Math.sin(th), 0, Math.cos(th)], 0.5);
        R[c] = h ? Math.hypot(h.point[0], h.point[2] - z0) : NaN;
        if (h) ok++;
      }
      R[C] = R[0];
      valid = ok > C * 0.6;
      if (valid) {
        // buracos (raio que sai pelo corte de um braço): interpola entre os vizinhos válidos
        for (let c = 0; c <= C; c++) {
          if (!Number.isNaN(R[c])) continue;
          let a = c, bb = c;
          while (Number.isNaN(R[(a + C) % C]) && c - a < C) a--;
          while (Number.isNaN(R[bb % C]) && bb - c < C) bb++;
          const ra = R[(a + C) % C], rb = R[bb % C];
          R[c] = bb === a ? ra : ra + ((rb - ra) * (c - a)) / (bb - a);
        }
        zc[k] = z0;
      }
    }
    if (!valid) {
      // anel sem seção (acima/abaixo do tronco): repete o anterior, ou um círculo de 14 cm
      if (have) {
        zc[k] = zc[k - 1];
        circ[k] = circ[k - 1];
        arc.copyWithin(k * (C + 1), (k - 1) * (C + 1), k * (C + 1));
      } else {
        zc[k] = 0;
        for (let c = 0; c <= C; c++) R[c] = 0.14;
        valid = true;
      }
      if (have) continue;
    }
    have = true;
    let s = 0;
    const cum = new Float32Array(C + 1);
    let px = R[0] * Math.sin(-Math.PI), pz = R[0] * Math.cos(-Math.PI);
    for (let c = 1; c <= C; c++) {
      const th = -Math.PI + (c * 2 * Math.PI) / C;
      const qx = R[c] * Math.sin(th), qz = R[c] * Math.cos(th);
      s += Math.hypot(qx - px, qz - pz);
      cum[c] = s;
      px = qx;
      pz = qz;
    }
    circ[k] = s;
    for (let c = 0; c <= C; c++) arc[k * (C + 1) + c] = cum[c] - cum[C / 2];
  }
  return (ctx._torsoRings = { y0, dy, n, C, zc, circ, arc });
}

/**
 * Coordenadas de padrão do tronco: [u, v, período]. u = arco sobre a superfície a partir da linha central da frente
 * (o padrão não estica no busto), v = altura; a emenda fica nas costas, com período = circunferência naquela altura.
 */
export function torsoUv(ctx) {
  const r = torsoRings(ctx);
  const { pos } = ctx;
  const { C } = r;
  return (v) => {
    const x = pos[v * 3], y = pos[v * 3 + 1], z = pos[v * 3 + 2];
    const f = clamp01((y - r.y0) / (r.dy * (r.n - 1))) * (r.n - 1);
    const k0 = Math.min(r.n - 2, Math.floor(f));
    const t = f - k0;
    const at = (k) => {
      const th = Math.atan2(x, z - r.zc[k]);
      const fc = ((th + Math.PI) / (2 * Math.PI)) * C;
      const c0 = Math.min(C - 1, Math.floor(fc));
      const w = fc - c0;
      return r.arc[k * (C + 1) + c0] * (1 - w) + r.arc[k * (C + 1) + c0 + 1] * w;
    };
    return [at(k0) * (1 - t) + at(k0 + 1) * t, y, r.circ[k0] * (1 - t) + r.circ[k0 + 1] * t];
  };
}
