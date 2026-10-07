// Base Layer: top bandeau + boyshorts. Sempre presentes por baixo de tudo (o Body nunca aparece nu).
const clamp01 = (x) => Math.min(1, Math.max(0, x));
const smoothstep = (a, b, x) => {
  const t = clamp01((x - a) / (b - a));
  return t * t * (3 - 2 * t);
};
const cylUv = (cx = 0, cz = 0.0, radius = 0.16) => (v, ctx) => {
  const x = ctx.pos[v * 3] - cx;
  const z = ctx.pos[v * 3 + 2] - cz;
  return [Math.atan2(x, z) * radius, ctx.pos[v * 3 + 1]];
};

export function baseTop(ctx, params = { padding: 0 }) {
  const { L, mask, pos } = ctx;
  const yLo = L.y.underbust - 0.05;
  const yHi = L.y.bust + 0.1;
  return {
    name: 'base.top',
    slot: 'top',
    params,
    // padding 0 = tecido fino que marca o contorno do busto ("tenda"); 1 = bojo acolchoado e liso
    offsetFn: (v) => 0.0016 + 0.0085 * params.padding * smoothstep(0.03, 0.4, mask.breast[v]),
    field: (v) => {
      const y = pos[v * 3 + 1];
      const limb = (mask.arm[v] + mask.shoulderL[v] + mask.shoulderR[v] - 0.45) * 0.06;
      return Math.max(yLo - y, y - yHi, limb);
    },
    uv: cylUv(),
  };
}

export function baseBottom(ctx) {
  const { L, pos } = ctx;
  const yWaist = L.y.waist - 0.115;
  const d = L.hip.L.clone().sub(L.hip.L).length(); // 0
  void d;
  const crotchZone = (v) => {
    const x = Math.abs(pos[v * 3]);
    const y = pos[v * 3 + 1];
    return (1 - smoothstep(0.015, 0.075, x)) * smoothstep(L.y.crotch - 0.07, L.y.crotch + 0.03, y) * (1 - smoothstep(L.y.crotch + 0.08, L.y.crotch + 0.16, y));
  };
  const dLeg = L.hip.L.y - L.y.crotch + 0.095; // abertura da perna: ~9.5 cm abaixo do cruzamento
  return {
    name: 'base.bottom',
    slot: 'bottom',
    offsetFn: (v) => 0.0016 + 0.004 * crotchZone(v),
    field: (v) => {
      const x = pos[v * 3];
      const y = pos[v * 3 + 1];
      const z = pos[v * 3 + 2];
      let f = y - yWaist;
      for (const side of ['L', 'R']) {
        const s = side === 'L' ? 1 : -1;
        if (s * x < -0.004) continue;
        const h = L.hip[side];
        const a = L.thighAxis[side];
        const along = (x - h.x) * a.x + (y - h.y) * a.y + (z - h.z) * a.z;
        f = Math.max(f, along - dLeg);
      }
      return f;
    },
    uv: cylUv(),
  };
}
void clamp01;
