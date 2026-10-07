// Anatomia da superfície (relevo e sombreamento): a malha base é lisa, então clavículas, tendões do pescoço,
// esterno, costelas, linha alba, umbigo, ossos do quadril, coluna e covinhas são definidos aqui como marcas
// sobre a malha de referência (estado neutro) e desenhados no shader da pele como campo de altura + cavidade.
// Como as marcas vivem no espaço de referência (aRest), acompanham qualquer morph sem esticar.
//
// Índices dos pontos no array enviado ao shader (cada ponto = vec3, em metros):
export const A = {
  CLAV: 0, // 2 lados × 5 pontos (crista da clavícula, do esterno ao acrômio)
  SCM: 10, // 2 lados × 3 pontos (esternocleidomastóideo)
  NOTCH: 16, // 1 ponto (incisura jugular)
  COST: 17, // 2 lados × 4 pontos (arco costal)
  LINEA: 25, // 3 pontos: xifoide, umbigo, púbis
  NAVEL: 28, // 1 ponto
  ASIS: 29, // 2 lados × 2 pontos (espinha ilíaca → púbis: prega inguinal)
  SPINE: 33, // 3 pontos: C7, meio das costas, sacro
  DIMPLE: 36, // 2 pontos (covinhas lombares)
  SCAP: 38, // 2 lados × 2 pontos (espinha da escápula)
  RIBS: 42, // 2 lados × 1 ponto (centro das costelas laterais)
  COUNT: 44,
};

/**
 * Encaixa um ponto na superfície: média dos vértices próximos a (x, y) com normal voltada para `facing`
 * (frente +z, costas -z). Devolve [x, y, z].
 */
function makeSurf(ctx) {
  const { N, pos, nrm } = ctx.ref ? { N: ctx.N, pos: ctx.ref.pos, nrm: ctx.ref.normals } : ctx;
  return (x, y, facing = 1, rx = 0.012, ry = 0.012) => {
    let sx = 0, sy = 0, sz = 0, sw = 0;
    for (let v = 0; v < N; v++) {
      const vx = pos[v * 3], vy = pos[v * 3 + 1];
      const dx = vx - x, dy = vy - y;
      if (Math.abs(dx) > rx || Math.abs(dy) > ry) continue;
      if (nrm[v * 3 + 2] * facing < 0.1) continue;
      const w = 1 - (dx * dx) / (rx * rx) * 0.5 - (dy * dy) / (ry * ry) * 0.5;
      sx += vx * w; sy += vy * w; sz += pos[v * 3 + 2] * w; sw += w;
    }
    if (sw === 0) return [x, y, facing * 0.05];
    return [sx / sw, sy / sw, sz / sw];
  };
}

/** Pontos de referência (Float32Array de A.COUNT × 3) e dados auxiliares. */
export function computeAnatomy(ctx) {
  const surf = makeSurf(ctx);
  const P = new Float32Array(A.COUNT * 3);
  const put = (i, p) => {
    P[i * 3] = p[0]; P[i * 3 + 1] = p[1]; P[i * 3 + 2] = p[2];
  };
  const L = ctx.L;
  const yNeck = L.y.neckBase; // base do pescoço (0.527)

  // incisura jugular: mínimo do perfil sagital na base do pescoço
  put(A.NOTCH, surf(0, yNeck - 0.009, 1, 0.006, 0.01));

  for (const s of [1, -1]) {
    const k = s > 0 ? 0 : 1;
    // clavícula: da incisura ao acrômio (crista na frente do ombro, levemente ascendente e depois descendente)
    const cy = [yNeck - 0.017, yNeck - 0.012, yNeck - 0.012, yNeck - 0.02, yNeck - 0.036];
    const cx = [0.022, 0.052, 0.085, 0.116, 0.144];
    for (let i = 0; i < 5; i++) put(A.CLAV + k * 5 + i, surf(cx[i] * s, cy[i], 1, 0.01, 0.01));
    // esternocleidomastóideo: da cabeça esternal ao lado do pescoço, perto do corte
    put(A.SCM + k * 3, surf(0.017 * s, yNeck - 0.008, 1, 0.008, 0.008));
    put(A.SCM + k * 3 + 1, surf(0.023 * s, yNeck + 0.034, 1, 0.009, 0.012));
    put(A.SCM + k * 3 + 2, surf(0.025 * s, yNeck + 0.064, 1, 0.009, 0.014));
    // arco costal: do xifoide para baixo e para o lado
    const yx = L.y.underbust + 0.012;
    put(A.COST + k * 4, surf(0.014 * s, yx, 1, 0.01, 0.01));
    put(A.COST + k * 4 + 1, surf(0.058 * s, yx - 0.03, 1, 0.012, 0.012));
    put(A.COST + k * 4 + 2, surf(0.098 * s, yx - 0.065, 1, 0.012, 0.012));
    put(A.COST + k * 4 + 3, surf(0.125 * s, yx - 0.105, 1, 0.012, 0.012));
    // prega inguinal: espinha ilíaca anterior → púbis
    put(A.ASIS + k * 2, surf(0.112 * s, L.y.hipJoint + 0.045, 1, 0.012, 0.012));
    put(A.ASIS + k * 2 + 1, surf(0.03 * s, L.y.crotch + 0.045, 1, 0.012, 0.012));
    // escápula (costas): da coluna para o ombro
    put(A.SCAP + k * 2, surf(0.034 * s, L.y.bust + 0.085, -1, 0.012, 0.012));
    put(A.SCAP + k * 2 + 1, surf(0.125 * s, L.y.bust + 0.135, -1, 0.012, 0.012));
    // covinhas lombares (sacro)
    put(A.DIMPLE + k, surf(0.046 * s, L.y.hipJoint + 0.042, -1, 0.01, 0.01));
    // costelas laterais
    put(A.RIBS + k, surf(0.135 * s, L.y.underbust - 0.045, 1, 0.014, 0.02));
  }

  // linha alba: xifoide → umbigo → púbis
  const navel = findNavel(ctx, surf);
  put(A.LINEA, surf(0, L.y.underbust + 0.004, 1, 0.006, 0.01));
  put(A.LINEA + 1, navel);
  put(A.LINEA + 2, surf(0, L.y.crotch + 0.07, 1, 0.006, 0.01));
  put(A.NAVEL, navel);
  // coluna: C7 → meio → sacro
  put(A.SPINE, surf(0, yNeck - 0.012, -1, 0.006, 0.01));
  put(A.SPINE + 1, surf(0, L.y.waist + 0.02, -1, 0.006, 0.012));
  put(A.SPINE + 2, surf(0, L.y.hipJoint + 0.03, -1, 0.006, 0.012));
  return P;
}

/** Umbigo: centróide dos vértices afetados pelos alvos de umbigo, encaixado na superfície frontal. */
function findNavel(ctx, surf) {
  const body = ctx.body;
  const T = body.morph.T;
  let sy = 0, sz = 0, n = 0;
  for (const name of ['stomach/stomach-navel-in', 'stomach/stomach-navel-out']) {
    const i = body.morph.index.get(name);
    if (i === undefined || !T.count[i]) continue;
    for (let o = T.offset[i], e = o + T.count[i]; o < e; o++) {
      const v = T.idx[o] * 3;
      sy += ctx.ref.P[v + 1];
      sz += ctx.ref.P[v + 2];
      n++;
    }
  }
  if (!n) return surf(0, ctx.L.y.waist - 0.03, 1, 0.006, 0.01);
  return surf(0, sy / n, 1, 0.005, 0.008);
}
