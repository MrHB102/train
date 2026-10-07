// Construtores de peças: cada um recebe (ctx, options, { style, dresser, entry }) e devolve as partes da peça:
//   { shells: [spec], ribbons: [spec], objects: [{ id, object, update, dispose }], drapes: [...] }
// Os specs de Shell levam `field` (metros, <= 0 dentro), `offsetFn`, `uv`, `layer` e `opaque`; o Dresser
// anexa o material. Camadas: base 1 · meias 2 · peças 3 · por cima 4 · acessórios 5.
// Espessuras (m): base 1.6 mm · meias 2.2 mm · peças 3.6 mm · por cima 4.8 mm.
import { FABRICS } from '../shaders/fabric.js';
import { smoothstep, mix, excludeLimbs, excludeArms, highLegCut, neckBand, legAxial } from './fields.js';
import { baseTop, baseBottom } from './recipes/base.js';
import { skirt, apron } from './drapes.js';
import { NeckBow, BunnyTail } from './objects.js';
import { shoes } from './shoes.js';

const TAU = Math.PI * 2;
const clamp01 = (x) => Math.min(1, Math.max(0, x));

const seeThrough = (style) => !!(FABRICS[style.fabric]?.transparent || FABRICS[style.fabric]?.cutout);
const cylUv = (ctx, radius = 0.16, cz = 0) => (v) => [Math.atan2(ctx.pos[v * 3], ctx.pos[v * 3 + 2] - cz) * radius, ctx.pos[v * 3 + 1]];
const legCyl = (ctx, radius = 0.065) => (v) => {
  const x = ctx.pos[v * 3];
  const cx = x >= 0 ? 0.105 : -0.105;
  return [Math.atan2(x - cx, ctx.pos[v * 3 + 2] - 0.02) * radius, ctx.pos[v * 3 + 1]];
};

const crotchZone = (ctx) => (v) => {
  const { pos, L } = ctx;
  const x = Math.abs(pos[v * 3]);
  const y = pos[v * 3 + 1];
  return (1 - smoothstep(0.015, 0.075, x)) * smoothstep(L.y.crotch - 0.07, L.y.crotch + 0.03, y) * (1 - smoothstep(L.y.crotch + 0.08, L.y.crotch + 0.16, y));
};

/** Linha da borda superior de busto: reta, coração (sweetheart) ou em V; mais baixa nas costas e sob o braço. */
function necklineY(kind, ctx, yBase) {
  return (x, z) => {
    const ax = Math.abs(x);
    let y = yBase;
    if (kind === 1) y += -0.03 * (1 - smoothstep(0, 0.075, ax)) + 0.011 * (smoothstep(0.02, 0.09, ax) - smoothstep(0.09, 0.15, ax));
    else if (kind === 3) y += -0.075 * Math.max(0, 1 - ax / 0.1);
    y -= 0.032 * (1 - smoothstep(-0.1, 0.04, z)); // costas mais baixas
    y -= 0.03 * smoothstep(0.12, 0.2, ax); // cai sob o braço
    return y;
  };
}

// --------------------------------------------------------------------------------------------------- base
const asParts = (res) => ({ shells: [{ ...res.shell, layer: 1 }], ribbons: res.ribbons });
const base_top = (ctx, o) => asParts(baseTop(ctx, o));
const base_bottom = (ctx, o) => asParts(baseBottom(ctx, o));

// --------------------------------------------------------------------------------------------------- collant
function leotard(ctx, o, { style }) {
  const { L, mask, pos } = ctx;
  const limbs = excludeLimbs(ctx, { thresh: 0.4 });
  const yBase = L.y.bust + 0.055 + 0.06 * o.topHeight;
  const top = necklineY(o.neckline ?? 1, ctx, yBase);
  const yTie = L.y.hipJoint + 0.015 + 0.075 * o.legCut;
  const leg = highLegCut(ctx, {
    yHip: yTie,
    yCrotch: L.y.crotch + 0.014,
    xHip: 0.168,
    xCrotch: 0.012,
    backDrop: 0.09 * o.backDrop,
    frontDrop: 0,
  });
  const pad = o.padding;
  const shell = {
    name: 'leotard',
    layer: 3,
    opaque: !seeThrough(style),
    offsetFn: (v) => 0.0036 + 0.011 * pad * smoothstep(0.03, 0.4, mask.breast[v]) + 0.004 * crotchZone(ctx)(v),
    field: (v) => Math.max(pos[v * 3 + 1] - top(pos[v * 3], pos[v * 3 + 2]), limbs(v), leg(v)),
    uv: cylUv(ctx),
    uvPeriod: TAU * 0.16,
    castShadow: true,
  };
  return { shells: [shell] };
}

// --------------------------------------------------------------------------------------------------- corpete / blusas
function bodice(ctx, o, { style }) {
  const { L, mask, pos } = ctx;
  const nk = o.neckline;
  const yBot = L.y.waist - 0.015 + o.length;
  const arms = nk === 2 ? excludeArms(ctx, 0.5) : excludeLimbs(ctx, { thresh: 0.4 });
  const top = nk === 2 ? null : necklineY(nk === 1 ? 1 : 0, ctx, L.y.bust + 0.082);
  const neckHi = L.y.neckBase - 0.016;
  const shell = {
    name: 'bodice',
    layer: 3,
    opaque: !seeThrough(style),
    offsetFn: (v) => 0.0036 + 0.011 * o.padding * smoothstep(0.03, 0.4, mask.breast[v]),
    field: (v) => {
      const x = pos[v * 3], y = pos[v * 3 + 1], z = pos[v * 3 + 2];
      const upper = top ? y - top(x, z) : y - neckHi + 0.03 * (1 - smoothstep(0, 0.07, Math.abs(x))) * smoothstep(-0.02, 0.06, z);
      return Math.max(yBot - y, upper, arms(v));
    },
    uv: cylUv(ctx),
    uvPeriod: TAU * 0.16,
    castShadow: true,
  };
  return { shells: [shell] };
}

function cropTee(ctx, o, { style }) {
  const { L, pos } = ctx;
  const arms = excludeArms(ctx, 0.55);
  const yBot = mix(L.y.underbust - 0.012, L.y.waist - 0.02, o.length);
  const yTop = mix(L.y.bust + 0.105, L.y.neckBase - 0.02, o.neck);
  const shell = {
    name: 'cropTee',
    layer: 3,
    opaque: !seeThrough(style),
    offsetFn: () => 0.0038,
    field: (v) => {
      const x = pos[v * 3], y = pos[v * 3 + 1], z = pos[v * 3 + 2];
      const scoop = 0.05 * (1 - smoothstep(0, 0.09, Math.abs(x))) * smoothstep(-0.02, 0.06, z) * (1 - o.neck * 0.6);
      return Math.max(yBot - y, y - yTop + scoop, arms(v));
    },
    uv: cylUv(ctx),
    uvPeriod: TAU * 0.16,
    castShadow: true,
  };
  return { shells: [shell] };
}

function tubeTop(ctx, o, { style }) {
  const res = baseTop(ctx, { style: 'bandeau', padding: o.padding });
  const shell = { ...res.shell, name: 'tubeTop', layer: 3, opaque: !seeThrough(style), castShadow: true };
  const mask = ctx.mask;
  shell.offsetFn = (v) => 0.0036 + 0.011 * o.padding * smoothstep(0.03, 0.4, mask.breast[v]);
  return { shells: [shell] };
}

// --------------------------------------------------------------------------------------------------- calças e shorts
function shorts(ctx, o, { style }) {
  const { L, pos } = ctx;
  const yTop = L.y.waist - 0.07 + o.rise;
  const dLeg = L.hip.L.y - L.y.crotch + o.length;
  const shell = {
    name: 'shorts',
    layer: 3,
    opaque: !seeThrough(style),
    offsetFn: (v) => 0.0036 + 0.004 * crotchZone(ctx)(v),
    field: (v) => {
      const x = pos[v * 3], y = pos[v * 3 + 1], z = pos[v * 3 + 2];
      let f = y - yTop;
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
    castShadow: true,
  };
  return { shells: [shell] };
}

function leggings(ctx, o, { style }) {
  const U = legAxial(ctx);
  const { L, pos } = ctx;
  const lens = ctx._legLen;
  const yTop = L.y.waist - 0.06 + o.rise;
  const uBot = mix(lens.shin + 0.03, 0.045, o.length);
  const limbs = excludeLimbs(ctx);
  const shell = {
    name: 'leggings',
    layer: 3,
    opaque: !seeThrough(style),
    offsetFn: (v) => 0.0034 + 0.003 * crotchZone(ctx)(v),
    field: (v) => Math.max(pos[v * 3 + 1] - yTop, uBot - U[v], limbs(v)),
    edge: (v) => Math.min(yTop - pos[v * 3 + 1], U[v] - uBot),
    uv: legCyl(ctx),
    uvPeriod: TAU * 0.065,
    castShadow: true,
  };
  return { shells: [shell] };
}

// --------------------------------------------------------------------------------------------------- meias e meia-calça
function legwear(ctx, o, { style }) {
  const U = legAxial(ctx);
  const { L, mask, pos } = ctx;
  const lens = ctx._legLen;
  const uThighTop = lens.shin + lens.thigh - 0.153; // ~8 cm abaixo da virilha
  const t = o.top;
  const stockings = t <= 0.8;
  const uTop = mix(0.06, uThighTop, t / 0.8);
  const yW = mix(L.y.hips - 0.03, L.y.waist + 0.02, clamp01((t - 0.8) / 0.2));
  const uBot = o.feet ? -1 : 0.035;
  const limbs = excludeLimbs(ctx);
  const shell = {
    name: 'legwear',
    layer: 2,
    opaque: !seeThrough(style),
    offsetFn: () => 0.0022,
    field: stockings
      ? (v) => Math.max(U[v] - uTop, uBot - U[v], (0.5 - mask.leg[v]) * 0.06)
      : (v) => Math.max(pos[v * 3 + 1] - yW, uBot - U[v], limbs(v)),
    edge: stockings ? (v) => uTop - U[v] : (v) => yW - pos[v * 3 + 1],
    uv: legCyl(ctx),
    uvPeriod: TAU * 0.065,
  };
  return { shells: [shell] };
}

// --------------------------------------------------------------------------------------------------- gola e mangas
function collar(ctx, o, { style }) {
  const { L, pos } = ctx;
  const a = L.neckAxis;
  const bs = L.neck.base;
  const d0 = o.lift;
  const d1 = o.lift + o.height;
  // anel entre dois planos perpendiculares ao eixo do pescoço, limitado em raio (não pega os ombros)
  const along = (v) => (pos[v * 3] - bs.x) * a.x + (pos[v * 3 + 1] - bs.y) * a.y + (pos[v * 3 + 2] - bs.z) * a.z;
  const radial = (v) => {
    const d = along(v);
    return Math.hypot(pos[v * 3] - bs.x - a.x * d, pos[v * 3 + 1] - bs.y - a.y * d, pos[v * 3 + 2] - bs.z - a.z * d);
  };
  const cz = bs.z + (d0 + o.height / 2) * (a.z / a.y) + 0.02;
  const shell = {
    name: 'collar',
    layer: 3,
    opaque: !seeThrough(style),
    offsetFn: () => 0.0046,
    field: (v) => Math.max(d0 - along(v), along(v) - d1, radial(v) - 0.068),
    edge: (v) => Math.min(along(v) - d0, d1 - along(v)),
    uv: (v) => [Math.atan2(pos[v * 3], pos[v * 3 + 2] - cz) * 0.045, pos[v * 3 + 1]],
    uvPeriod: TAU * 0.045,
    castShadow: true,
  };
  return { shells: [shell] };
}

function puffSleeves(ctx, o, { style }) {
  const { mask, pos, L } = ctx;
  const arm = L.arm;
  const axial = (v) => {
    const g = pos[v * 3] >= 0 ? arm.L : arm.R;
    return (pos[v * 3] - g.head.x) * g.axis.x + (pos[v * 3 + 1] - g.head.y) * g.axis.y + (pos[v * 3 + 2] - g.head.z) * g.axis.z;
  };
  const uHem = (v) => (pos[v * 3] >= 0 ? arm.L : arm.R).uCut - 0.004;
  const shell = {
    name: 'puffSleeves',
    layer: 4,
    opaque: !seeThrough(style),
    // balão: nasce na cava, incha no meio e fecha elástico perto da barra
    offsetFn: (v) => {
      const g = pos[v * 3] >= 0 ? arm.L : arm.R;
      const t = clamp01((axial(v) - g.uIn) / (g.uCut - g.uIn));
      const bell = Math.pow(Math.sin(Math.PI * clamp01(t * 1.05)), 1.1);
      return 0.0048 + o.puff * (0.017 * bell + 0.004 * t * t);
    },
    field: (v) => Math.max((0.3 - mask.arm[v]) * 0.05, axial(v) - uHem(v)),
    edge: (v) => uHem(v) - axial(v),
    uv: (v) => {
      const g = pos[v * 3] >= 0 ? arm.L : arm.R;
      return [Math.atan2(pos[v * 3 + 2] - g.head.z, pos[v * 3 + 1] - g.head.y) * 0.05, axial(v)];
    },
    uvPeriod: TAU * 0.05,
    castShadow: true,
  };
  return { shells: [shell] };
}

// --------------------------------------------------------------------------------------------------- objetos
function bowtie(ctx, o, { dresser, entry }) {
  const collar = dresser.entries.get('neck');
  const mid = collar ? collar.options.lift + collar.options.height / 2 : 0.026;
  const bow = new NeckBow({ ctx, body: ctx.body, material: entry.mat, o, collarMid: mid });
  return { objects: [{ id: 'bowtie', object: bow, dispose: () => bow.dispose() }] };
}

function tail(ctx, o, { style, entry, dresser }) {
  const t = new BunnyTail({ ctx, body: ctx.body, noise: dresser.noise, o, style });
  return { objects: [{ id: 'tail', object: t, update: (dt) => t.update(dt), dispose: () => t.dispose() }] };
}

export const BUILDERS = {
  base_top,
  base_bottom,
  leotard,
  bodice,
  cropTee,
  tubeTop,
  shorts,
  leggings,
  legwear,
  collar,
  puffSleeves,
  skirt,
  apron,
  bowtie,
  tail,
  shoes,
};

void highLegCut;
