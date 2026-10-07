// Base Layer: biquíni (top + calcinha), sempre por baixo de tudo — o Body nunca aparece nu.
//  - Top: triângulo (padrão, como nos criadores de personagem) ou bandeau; cordões são Ribbons.
//  - Calcinha: biquíni clássico com tiras laterais, ou boyshort.
// Cada receita devolve { shell, ribbons[] }: o Shell é recortado da superfície e cada Ribbon é um cordão.
// Todas as medidas estão no espaço de referência (mulher padrão, metros, y para cima, frente +z).
import { smoothstep, mix, excludeLimbs, highLegCut, neckBand } from '../fields.js';
import { ringPath, linePath, getSurface } from '../ribbon.js';

const TAU = Math.PI * 2;
const cylUv = (ctx, radius = 0.16) => (v) => [Math.atan2(ctx.pos[v * 3], ctx.pos[v * 3 + 2]) * radius, ctx.pos[v * 3 + 1]];

function nipples(ctx) {
  const { ref, rig } = ctx;
  return ['L', 'R'].map((s) => ref.tails[rig.index.get(`breast.${s}`)]);
}

/** Centro (z) do tronco numa altura y: média entre a frente e as costas, na linha central. */
function centerZ(ctx, y) {
  const S = getSurface(ctx);
  const f = S.cast([0, y, 0.6], [0, 0, -1], 1.5);
  const b = S.cast([0, y, -0.6], [0, 0, 1], 1.5);
  return f && b ? (f.point[2] + b.point[2]) / 2 : 0.01;
}

const cacheGet = (ctx, key, make) => {
  ctx._cache ??= new Map();
  if (!ctx._cache.has(key)) ctx._cache.set(key, make());
  return ctx._cache.get(key);
};

// ---------------------------------------------------------------------------------------------- top
/** Triângulo de cada seio (vista frontal), escalado em torno do mamilo pela cobertura. */
function cupTriangles(ctx, cover) {
  const nip = nipples(ctx);
  const yN = (nip[0].y + nip[1].y) / 2;
  return [1, -1].map((s, k) => {
    const n = nip[k];
    const P = (x, y) => [n.x + (s * x - n.x) * cover, n.y + (y - n.y) * cover];
    const A = P(0.006, yN - 0.046); // inferior interno (junto ao esterno)
    const B = P(0.182, yN - 0.046); // inferior externo (lado do tórax)
    const C = P(0.040, yN + 0.108); // topo (de onde sai o cordão do pescoço)
    const orient = Math.sign((B[0] - A[0]) * (C[1] - A[1]) - (B[1] - A[1]) * (C[0] - A[0])) || 1;
    const edge = (p, q) => {
      const dx = q[0] - p[0], dy = q[1] - p[1], l = Math.hypot(dx, dy);
      return (x, y) => (orient * (dx * (y - p[1]) - dy * (x - p[0]))) / l; // > 0 dentro
    };
    return { A, B, C, edges: [edge(A, B), edge(B, C), edge(C, A)] };
  });
}

export function baseTopTriangle(ctx, { padding = 0, cover = 1 } = {}) {
  const { pos, mask } = ctx;
  const tris = cupTriangles(ctx, cover);
  const shell = {
    name: 'base.top',
    params: { padding, cover },
    // padding 0 = tecido fino que marca o contorno do busto ("tenda"); 1 = bojo acolchoado e liso
    offsetFn: (v) => 0.0016 + 0.0085 * padding * smoothstep(0.03, 0.4, mask.breast[v]),
    field: (v) => {
      const x = pos[v * 3], y = pos[v * 3 + 1], z = pos[v * 3 + 2];
      let f = 1e9;
      for (const T of tris) f = Math.min(f, -Math.min(T.edges[0](x, y), T.edges[1](x, y), T.edges[2](x, y)));
      return Math.max(f, 0.01 - z);
    },
    uv: cylUv(ctx),
    uvPeriod: TAU * 0.16,
  };
  return { shell, ribbons: topStrings(ctx, cover) };
}

/** Cordões do top: faixa sob o busto, cordão do pescoço (halter) e as duas alças que sobem dos triângulos. */
function topStrings(ctx, cover) {
  return cacheGet(ctx, `topStrings:${cover.toFixed(2)}`, () => {
    const nip = nipples(ctx);
    const yN = (nip[0].y + nip[1].y) / 2;
    const yBand = yN - 0.046;
    const yNeck = ctx.L.y.neckBase + 0.019;
    const ribs = [];
    ribs.push({ name: 'base.top.band', ...ringPath(ctx, { y: yBand, axis: [0, centerZ(ctx, yBand)], n: 200 }) });
    ribs.push({ name: 'base.top.neck', ...ringPath(ctx, { y: yNeck, axis: [0, centerZ(ctx, yNeck)], n: 120 }) });
    for (const s of [1, -1]) {
      const n = nip[s > 0 ? 0 : 1];
      const top = [n.x + (s * 0.04 - n.x) * cover, n.y + (yN + 0.108 - n.y) * cover];
      ribs.push({ name: `base.top.halter${s > 0 ? 'L' : 'R'}`, ...linePath(ctx, [top, [s * 0.035, yN + 0.155], [s * 0.029, yNeck - 0.003]], { facing: 1, step: 0.003 }) });
    }
    return ribs;
  });
}

export function baseTopBandeau(ctx, { padding = 0 } = {}) {
  const { L, mask, pos } = ctx;
  const yLo = L.y.underbust - 0.05;
  const yHi = L.y.bust + 0.1;
  const limbs = excludeLimbs(ctx);
  const shell = {
    name: 'base.top',
    params: { padding },
    offsetFn: (v) => 0.0016 + 0.0085 * padding * smoothstep(0.03, 0.4, mask.breast[v]),
    field: (v) => Math.max(yLo - pos[v * 3 + 1], pos[v * 3 + 1] - yHi, limbs(v)),
    uv: cylUv(ctx),
    uvPeriod: TAU * 0.16,
  };
  return { shell, ribbons: [] };
}

export function baseTop(ctx, o = {}) {
  return (o.style === 'bandeau' ? baseTopBandeau : baseTopTriangle)(ctx, o);
}

// ---------------------------------------------------------------------------------------------- calcinha
export function baseBottomBikini(ctx, { rise = 0, cut = 0.5, backCover = 0.6 } = {}) {
  const { L, pos } = ctx;
  const yTie = L.y.hipJoint + 0.05 + rise; // altura das tiras laterais no quadril
  const yCF = L.y.crotch + 0.098 + rise * 0.5; // centro da borda superior, na frente
  const yCB = L.y.hipJoint + 0.014 + rise * 0.5; // centro da borda superior, atrás
  const legCut = highLegCut(ctx, {
    yHip: yTie - 0.004 + 0.03 * (cut - 0.5),
    yCrotch: L.y.crotch + 0.014,
    xHip: 0.15,
    xCrotch: 0.014,
    backDrop: 0.01 + 0.06 * backCover,
    frontDrop: 0,
  });
  const topY = (x, z) => {
    const k = Math.pow(smoothstep(0.0, 0.145, Math.abs(x)), 0.85);
    return mix(mix(yCB, yTie, k), mix(yCF, yTie, k), smoothstep(-0.09, 0.07, z));
  };
  const crotchZone = (v) => {
    const x = Math.abs(pos[v * 3]);
    const y = pos[v * 3 + 1];
    return (1 - smoothstep(0.015, 0.075, x)) * smoothstep(L.y.crotch - 0.07, L.y.crotch + 0.03, y) * (1 - smoothstep(L.y.crotch + 0.08, L.y.crotch + 0.16, y));
  };
  const shell = {
    name: 'base.bottom',
    params: { rise, cut, backCover },
    offsetFn: (v) => 0.0016 + 0.004 * crotchZone(v),
    field: (v) => Math.max(pos[v * 3 + 1] - topY(pos[v * 3], pos[v * 3 + 2]), legCut(v)),
    uv: cylUv(ctx),
    uvPeriod: TAU * 0.16,
  };
  return { shell, ribbons: bottomStrings(ctx, topY, yTie, rise) };
}

/** Cordão contínuo pela borda superior: acompanha o V da frente, o canto do quadril (tiras) e as costas. */
function bottomStrings(ctx, topY, yTie, rise) {
  return cacheGet(ctx, `bottomStrings:${rise.toFixed(3)}`, () => {
    const S = getSurface(ctx);
    const zc = centerZ(ctx, yTie);
    const samples = [];
    const n = 220;
    for (let i = 0; i < n; i++) {
      const th = (i / n) * TAU; // 0 = frente
      const s = Math.sin(th), c = Math.cos(th);
      let y = yTie;
      let hit = null;
      for (let it = 0; it < 3; it++) {
        hit = S.cast([0.5 * s, y, zc + 0.5 * c], [-s, 0, -c], 1.2);
        if (!hit) break;
        y = topY(hit.point[0], hit.point[2]);
      }
      if (hit) samples.push(hit);
    }
    return [{ name: 'base.bottom.cord', samples, closed: true }];
  });
}

export function baseBottomBoy(ctx) {
  const { L, pos } = ctx;
  const yWaist = L.y.waist - 0.115;
  const crotchZone = (v) => {
    const x = Math.abs(pos[v * 3]);
    const y = pos[v * 3 + 1];
    return (1 - smoothstep(0.015, 0.075, x)) * smoothstep(L.y.crotch - 0.07, L.y.crotch + 0.03, y) * (1 - smoothstep(L.y.crotch + 0.08, L.y.crotch + 0.16, y));
  };
  const dLeg = L.hip.L.y - L.y.crotch + 0.095; // abertura da perna: ~9.5 cm abaixo do cruzamento
  const shell = {
    name: 'base.bottom',
    offsetFn: (v) => 0.0016 + 0.004 * crotchZone(v),
    field: (v) => {
      const x = pos[v * 3], y = pos[v * 3 + 1], z = pos[v * 3 + 2];
      let f = y - yWaist;
      for (const side of ['L', 'R']) {
        const s = side === 'L' ? 1 : -1;
        if (s * x < -0.004) continue;
        const h = L.hip[side];
        const a = L.thighAxis[side];
        f = Math.max(f, (x - h.x) * a.x + (y - h.y) * a.y + (z - h.z) * a.z - dLeg);
      }
      return f;
    },
    uv: cylUv(ctx),
    uvPeriod: TAU * 0.16,
  };
  return { shell, ribbons: [] };
}

export function baseBottom(ctx, o = {}) {
  return o.style === 'boy' ? baseBottomBoy(ctx) : baseBottomBikini(ctx, o);
}

void neckBand;
