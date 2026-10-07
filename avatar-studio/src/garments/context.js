// Contexto de alfaiataria: marcos anatômicos e máscaras de região do Body de referência.
// Tudo em metros, y para cima, frente = +Z, esquerda do corpo = +X.
import * as THREE from 'three';

const sum = (a) => a.reduce((x, y) => x + y, 0);

export function createContext(body) {
  const ref = body.reference;
  const pkg = body.pkg;
  const rig = body.rig;
  const N = body.N;
  const names = rig.names;

  // máscaras por região a partir dos pesos de skinning (0..1 por vértice)
  const sets = {
    armL: names.filter((n) => /^(upperarm01|upperarm02)\.L$/.test(n)),
    armR: names.filter((n) => /^(upperarm01|upperarm02)\.R$/.test(n)),
    shoulderL: names.filter((n) => /^(clavicle|shoulder01)\.L$/.test(n)),
    shoulderR: names.filter((n) => /^(clavicle|shoulder01)\.R$/.test(n)),
    legL: names.filter((n) => /^(upperleg0[12]|lowerleg0[12]|foot|toe\d-\d)\.L$/.test(n)),
    legR: names.filter((n) => /^(upperleg0[12]|lowerleg0[12]|foot|toe\d-\d)\.R$/.test(n)),
    footL: names.filter((n) => /^(foot|toe\d-\d)\.L$/.test(n)),
    footR: names.filter((n) => /^(foot|toe\d-\d)\.R$/.test(n)),
    neck: names.filter((n) => /^neck0\d$/.test(n)),
    breast: names.filter((n) => /^breast\.[LR]$/.test(n)),
    glute: names.filter((n) => /^glute\.[LR]$/.test(n)),
    belly: names.filter((n) => n === 'belly'),
  };
  const mask = {};
  for (const [key, list] of Object.entries(sets)) {
    const ids = new Set(list.map((n) => rig.index.get(n)));
    const m = new Float32Array(N);
    for (let v = 0; v < N; v++) {
      let w = 0;
      for (let j = 0; j < 4; j++) if (ids.has(pkg.skinIndex[v * 4 + j])) w += pkg.skinWeight[v * 4 + j] / 255;
      m[v] = w;
    }
    mask[key] = m;
  }
  // suaviza as máscaras de braço/ombro na vizinhança da malha: bordas de roupa (cava, decote) menos serrilhadas
  {
    const { start, nb } = body.cavity;
    const smoothMask = (m, iters = 4) => {
      let a = m;
      let b = new Float32Array(N);
      for (let it = 0; it < iters; it++) {
        for (let v = 0; v < N; v++) {
          let sum = a[v] * 2;
          const s0 = start[v], s1 = start[v + 1];
          for (let k = s0; k < s1; k++) sum += a[nb[k]];
          b[v] = sum / (s1 - s0 + 2);
        }
        [a, b] = [b, a];
      }
      return a;
    };
    for (const key of ['armL', 'armR', 'shoulderL', 'shoulderR']) mask[key] = smoothMask(mask[key]);
  }
  mask.arm = mask.armL.map((x, i) => x + mask.armR[i]);
  mask.leg = mask.legL.map((x, i) => x + mask.legR[i]);

  const head = (n) => ref.heads[rig.index.get(n)];
  const rulerY = (k) => {
    const list = pkg.meta.rulers[k];
    return sum(list.map((v) => ref.P[v * 3 + 1])) / list.length;
  };
  // ápice do cruzamento das pernas: menor y de vértices na linha central
  let crotchY = Infinity;
  for (let v = 0; v < N; v++) {
    if (Math.abs(ref.pos[v * 3]) < 0.006 && ref.pos[v * 3 + 1] < crotchY && ref.pos[v * 3 + 1] > head('lowerleg01.L').y) crotchY = ref.pos[v * 3 + 1];
  }
  const L = {
    y: {
      bust: rulerY('bust'),
      underbust: rulerY('underbust'),
      waist: rulerY('waist'),
      hips: rulerY('hips'),
      thigh: rulerY('thigh'),
      knee: rulerY('knee'),
      calf: rulerY('calf'),
      ankle: rulerY('ankle'),
      crotch: crotchY,
      hipJoint: head('upperleg01.L').y,
      neckBase: head('neck01').y,
    },
    hip: { L: head('upperleg01.L').clone(), R: head('upperleg01.R').clone() },
    knee: { L: head('lowerleg01.L').clone(), R: head('lowerleg01.R').clone() },
    ankle: { L: head('foot.L').clone(), R: head('foot.R').clone() },
    neck: { base: head('neck01').clone(), top: head('neck03').clone() },
  };
  const axis = (a, b) => b.clone().sub(a).normalize();
  // eixo do braço (ombro → cotovelo) e distância axial do corte (onde o braço termina), por lado
  const tailOf = (n) => ref.tails[rig.index.get(n)];
  L.arm = {};
  for (const sd of ['L', 'R']) {
    const a = head(`upperarm01.${sd}`).clone();
    const ax = tailOf(`upperarm02.${sd}`).clone().sub(a).normalize();
    let uCut = 0;
    let uIn = 1e9;
    for (let v = 0; v < N; v++) {
      if (mask[`arm${sd}`][v] < 0.5) continue;
      const u = (ref.pos[v * 3] - a.x) * ax.x + (ref.pos[v * 3 + 1] - a.y) * ax.y + (ref.pos[v * 3 + 2] - a.z) * ax.z;
      if (u > uCut) uCut = u;
      if (u < uIn) uIn = u;
    }
    L.arm[sd] = { head: a, axis: ax, uCut, uIn };
  }
  L.thighAxis = { L: axis(L.hip.L, L.knee.L), R: axis(L.hip.R, L.knee.R) };
  L.shinAxis = { L: axis(L.knee.L, L.ankle.L), R: axis(L.knee.R, L.ankle.R) };
  L.neckAxis = axis(L.neck.base, L.neck.top);

  const p = (v) => new THREE.Vector3(ref.pos[v * 3], ref.pos[v * 3 + 1], ref.pos[v * 3 + 2]);
  return { body, N, ref, pkg, rig, mask, L, p, pos: ref.pos, nrm: ref.normals, indices: pkg.indices };
}
