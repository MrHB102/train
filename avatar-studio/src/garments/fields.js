// Campos de corte reutilizáveis para Shells: cada função devolve field(v) -> metros (<= 0 dentro da peça).
// Combine com max (interseção) e min (união). Tudo no espaço de referência (mulher padrão), y para cima.
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
