// Sapatos de salto (scarpin) e botins, gerados proceduralmente sobre o pé do Body:
//  - cabedal e sola: Shells recortados da superfície do pé até o início do bico (peito do pé, calcanhar, lateral);
//  - bico: casco procedural (ToeBox) que sai de dentro do cabedal e fecha em ponta redonda além dos dedos. A malha
//    do pé tem cinco dedos separados, e recortar/inflar isso deixava a ponta em frangalhos; aqui o bico é uma
//    superfície única, presa aos ossos do pé e do dedo (dobra na bola do pé), com a sola como segundo material;
//  - salto agulha: objeto rígido no osso do pé, inclinado pelo mesmo ângulo que a animação usa para "calçar" o
//    salto, de modo que fica perpendicular ao chão quando a pessoa está parada;
//  - o corpo sobe a espessura da sola (Body.setGroundLift): é a sola que toca o chão, não a pele.
import * as THREE from 'three';
import { smoothstep, legAxial } from './fields.js';

/** Espessura da sola abaixo do pé (m) e altura da borda da sola acima da planta do pé (m). */
const SOLE = 0.0066;
const WELT = 0.0125;
/** Altura (z em relação ao tornozelo) em que o Shell termina e o bico (ToeBox) já está por fora. */
const Z_CUT = 0.096;
const Z_BOX0 = 0.088;
const Z_BOX1 = 0.16;
const Z_TIP = 0.184;

/** Salto agulha: sólido de revolução com o topo em y = 0 e a ponta em y = -1 (eixo para baixo). */
function postGeometry() {
  const prof = [
    [0.0, -1.0],
    [0.0033, -1.0],
    [0.004, -0.96],
    [0.0048, -0.6],
    [0.0062, -0.3],
    [0.0082, -0.1],
    [0.0092, -0.02],
    [0.0, 0.0],
  ];
  const g = new THREE.LatheGeometry(prof.map(([r, y]) => new THREE.Vector2(r, y)), 18);
  const pos = g.attributes.position;
  const n = pos.count;
  const aUv = new Float32Array(n * 2);
  const aEdge = new Float32Array(n).fill(0.02);
  const aRest = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) {
    aUv[i * 2] = pos.getX(i) + pos.getZ(i);
    aUv[i * 2 + 1] = pos.getY(i);
    aRest[i * 3] = pos.getX(i);
    aRest[i * 3 + 1] = pos.getY(i);
    aRest[i * 3 + 2] = pos.getZ(i);
  }
  g.setAttribute('aUv', new THREE.BufferAttribute(aUv, 2));
  g.setAttribute('aEdge', new THREE.BufferAttribute(aEdge, 1));
  g.setAttribute('aRest', new THREE.BufferAttribute(aRest, 3));
  return g;
}

/** Salto: rígido no osso do pé; ajusta posição, inclinação e comprimento ao salto atual (heelMeters). */
export class HeelPost {
  constructor({ body, animator, side, material, thickness = 1, lift = 0 }) {
    this.body = body;
    this.animator = animator;
    this.side = side;
    this.lift = lift;
    this.rig = body.rig;
    this.boneIdx = this.rig.index.get(`foot.${side}`);
    this.mesh = new THREE.Mesh(postGeometry(), material);
    this.mesh.castShadow = true;
    this.mesh.frustumCulled = false;
    this.thickness = thickness;
    this.group = new THREE.Group();
    this.group.add(this.mesh);
    this.rig.bones[this.boneIdx].add(this.group);
    this._h = -1;
    this.refit();
    this.off = body.onChange(() => {
      this._h = -1;
      this.refit();
    });
  }

  refit() {
    const head = this.rig.headWorld[this.boneIdx];
    const ankleH = Math.max(0.05, head.y - this.body.floorY);
    // centro do calcanhar: logo atrás e abaixo do tornozelo (referencial do osso do pé)
    this.local = new THREE.Vector3(0, -ankleH + 0.0004, -0.03);
  }

  update() {
    const h = this.animator.heelMeters;
    if (Math.abs(h - this._h) < 1e-5 && this._h >= 0) return;
    this._h = h;
    this.group.visible = h > 0.012;
    if (!this.group.visible) return;
    const fm = this.animator.footMetrics(this.side);
    const theta = Math.min(1.0, Math.asin(Math.min(0.95, h / fm.len)));
    // direção "para baixo no mundo" no referencial do pé (que está inclinado de theta)
    const u = new THREE.Vector3(0, -Math.cos(theta), Math.sin(theta));
    this.mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, -1, 0), u);
    // o calcanhar sobe (bola + 3 cm) · sen θ; o chão fica `lift` abaixo da planta do pé (a sola)
    const drop = (fm.ball + 0.03) * Math.sin(theta) + this.lift;
    this.mesh.scale.set(this.thickness, drop, this.thickness);
    this.group.position.copy(this.local);
  }

  setStyle() {}

  dispose() {
    this.off?.();
    this.group.removeFromParent();
    this.mesh.geometry.dispose();
  }
}

// ------------------------------------------------------------------------------------------------ bico
/**
 * Seções do pé de referência (pé esquerdo, relativas ao tornozelo) do início do bico até onde os dedos acabam:
 * limites em x (lado), altura da planta e do peito do pé. Vêm da própria malha, então o bico envolve os dedos.
 */
function footSections(ctx) {
  if (ctx._footSections) return ctx._footSections;
  const { pos, mask, N, ref, rig } = ctx;
  const ank = ref.heads[rig.index.get('foot.L')];
  const ball = ref.heads[rig.index.get('toe3-1.L')];
  const verts = [];
  let floor = Infinity;
  for (let v = 0; v < N; v++) {
    if (pos[v * 3] > 0 && mask.footL[v] > 0.5) {
      verts.push(v);
      floor = Math.min(floor, pos[v * 3 + 1]);
    }
  }
  const secs = [];
  const dz = 0.008;
  for (let z = Z_BOX0; z <= Z_BOX1 + 1e-9; z += dz) {
    let x0 = Infinity, x1 = -Infinity, y1 = -Infinity, n = 0;
    for (const v of verts) {
      if (Math.abs(pos[v * 3 + 2] - ank.z - z) > 0.0065) continue;
      n++;
      x0 = Math.min(x0, pos[v * 3] - ank.x);
      x1 = Math.max(x1, pos[v * 3] - ank.x);
      y1 = Math.max(y1, pos[v * 3 + 1] - floor);
    }
    secs.push(n ? { z, x0, x1, y1 } : null);
  }
  for (let k = 0; k < secs.length; k++) if (!secs[k]) secs[k] = { ...secs[Math.max(0, k - 1)], z: Z_BOX0 + k * dz };
  // suaviza (os dedos fazem calombos) sem nunca ficar por dentro do pé: expande com o vizinho e depois [1 2 1]/4
  {
    const copy = secs.map((s) => ({ ...s }));
    const grow = (k, key, pick) => pick(copy[Math.max(0, k - 1)][key], copy[k][key], copy[Math.min(secs.length - 1, k + 1)][key]);
    const ext = secs.map((_, k) => ({ x0: grow(k, 'x0', Math.min), x1: grow(k, 'x1', Math.max), y1: grow(k, 'y1', Math.max) }));
    for (let k = 0; k < secs.length; k++) {
      for (const key of ['x0', 'x1', 'y1']) secs[k][key] = 0.25 * ext[Math.max(0, k - 1)][key] + 0.5 * ext[k][key] + 0.25 * ext[Math.min(secs.length - 1, k + 1)][key];
    }
  }
  return (ctx._footSections = { secs, floor, ballZ: ball.z - ank.z });
}

export const RING = 28;
/** Superelipse (expoente 2/n): seção levemente "quadrada", como a de um bico de sapato. */
const sgnPow = (x, p) => Math.sign(x) * Math.pow(Math.abs(x), p);

/**
 * Bico do sapato: anéis do início do bico (dentro do cabedal) até a ponta, em coordenadas relativas ao tornozelo
 * do pé esquerdo (dx, altura acima da planta, z). Devolve anéis + índices (cabedal primeiro, sola depois).
 */
function toeLoft(ctx) {
  const { secs } = footSections(ctx);
  const rings = [];
  // seção em (xc ± hw, de -SOLE até `top`), alturas relativas à planta do pé
  const ringOf = (z, xc, hw, top, k = 1) => {
    const ymid = (top - SOLE) / 2;
    const hh = (top + SOLE) / 2;
    const pts = [];
    for (let i = 0; i < RING; i++) {
      const th = (i / RING) * Math.PI * 2;
      pts.push([xc + k * hw * sgnPow(Math.cos(th), 2 / 2.3), ymid + k * hh * sgnPow(Math.sin(th), 2 / 2.3), z]);
    }
    return pts;
  };
  let last = null;
  secs.forEach((s) => {
    const u = (s.z - Z_BOX0) / (Z_TIP - Z_BOX0);
    const room = Math.sin(Math.PI * Math.min(1, u * 1.15)); // folga para os dedos no meio do bico
    // margem: nasce 1,2 mm por dentro do cabedal (4,2 mm) e chega a 4,5 mm
    const m = 0.003 + 0.0015 * smoothstep(0, 0.14, u);
    last = { z: s.z, xc: (s.x0 + s.x1) / 2, hw: (s.x1 - s.x0) / 2 + m + 0.0015 * room, top: s.y1 + m + 0.0025 * room };
    rings.push(ringOf(last.z, last.xc, last.hw, last.top));
  });
  // ponta: calota que fecha em arco de círculo (a ponta tende ao lado do dedão)
  const J = 8;
  for (let j = 1; j <= J; j++) {
    const t = j / (J + 1);
    rings.push(ringOf(last.z + t * (Z_TIP - last.z), last.xc - 0.006 * t, last.hw, last.top, Math.sqrt(1 - t * t)));
  }
  return { rings, tip: [last.xc - 0.006, (last.top - SOLE) / 2, Z_TIP] };
}

/** Bico procedural de um pé: casco de duas cores (cabedal/sola) com pesos no osso do pé e no do dedo. */
export class ToeBox {
  constructor({ ctx, side, materials }) {
    this.ctx = ctx;
    this.body = ctx.body;
    this.side = side;
    this.sign = side === 'L' ? 1 : -1;
    this.rig = ctx.body.rig;
    const loft = toeLoft(ctx);
    const rings = loft.rings;
    const R = rings.length;
    const count = R * RING + 1;
    this.rel = new Float32Array(count * 3); // (dx, altura acima da planta, z) relativos ao tornozelo, deste lado
    rings.forEach((pts, r) => pts.forEach((p, i) => {
      const o = (r * RING + i) * 3;
      this.rel[o] = p[0] * this.sign;
      this.rel[o + 1] = p[1];
      this.rel[o + 2] = p[2];
    }));
    const tipO = (R * RING) * 3;
    this.rel[tipO] = loft.tip[0] * this.sign;
    this.rel[tipO + 1] = loft.tip[1];
    this.rel[tipO + 2] = loft.tip[2];

    // índices: cabedal (segmentos de cima) primeiro, depois a sola (segmentos de baixo, sen < -0,32)
    const up = [];
    const so = [];
    const flip = this.sign < 0;
    const push = (arr, a, b, c) => (flip ? arr.push(a, c, b) : arr.push(a, b, c));
    const isSole = (i) => Math.sin(((i + 0.5) / RING) * Math.PI * 2) < -0.32;
    for (let r = 0; r < R - 1; r++) {
      for (let i = 0; i < RING; i++) {
        const i2 = (i + 1) % RING;
        const a = r * RING + i, b = r * RING + i2, c = (r + 1) * RING + i2, d = (r + 1) * RING + i;
        const arr = isSole(i) ? so : up;
        push(arr, a, b, c);
        push(arr, a, c, d);
      }
    }
    for (let i = 0; i < RING; i++) {
      const i2 = (i + 1) % RING;
      push(isSole(i) ? so : up, (R - 1) * RING + i, (R - 1) * RING + i2, count - 1);
    }
    const index = Uint32Array.from([...up, ...so]);

    const g = new THREE.BufferGeometry();
    this.position = new Float32Array(count * 3);
    g.setAttribute('position', new THREE.BufferAttribute(this.position, 3).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute('normal', new THREE.BufferAttribute(new Float32Array(count * 3), 3).setUsage(THREE.DynamicDrawUsage));
    const aUv = new Float32Array(count * 2);
    const aRest = new Float32Array(count * 3);
    const skinIndex = new Uint8Array(count * 4);
    const skinWeight = new Float32Array(count * 4);
    const footIdx = this.rig.index.get(`foot.${side}`);
    const toeIdx = this.rig.index.get(`toe3-1.${side}`);
    for (let k = 0; k < count; k++) {
      const dx = this.rel[k * 3], dy = this.rel[k * 3 + 1], z = this.rel[k * 3 + 2];
      aUv[k * 2] = dx + z;
      aUv[k * 2 + 1] = dy;
      aRest[k * 3] = dx;
      aRest[k * 3 + 1] = dy;
      aRest[k * 3 + 2] = z;
      const wToe = smoothstep(0.105, 0.13, z);
      skinIndex[k * 4] = footIdx;
      skinIndex[k * 4 + 1] = toeIdx;
      skinWeight[k * 4] = 1 - wToe;
      skinWeight[k * 4 + 1] = wToe;
    }
    g.setAttribute('aUv', new THREE.BufferAttribute(aUv, 2));
    g.setAttribute('uv', new THREE.BufferAttribute(aUv, 2));
    g.setAttribute('aEdge', new THREE.BufferAttribute(new Float32Array(count).fill(1), 1));
    g.setAttribute('aRest', new THREE.BufferAttribute(aRest, 3));
    g.setAttribute('skinIndex', new THREE.Uint8BufferAttribute(skinIndex, 4));
    g.setAttribute('skinWeight', new THREE.Float32BufferAttribute(skinWeight, 4));
    g.setIndex(new THREE.BufferAttribute(index, 1));
    g.addGroup(0, up.length, 0);
    g.addGroup(up.length, so.length, 1);
    this.geometry = g;
    this.mesh = new THREE.SkinnedMesh(g, materials);
    this.mesh.name = `shoes.toe${side}`;
    this.mesh.frustumCulled = false;
    this.mesh.castShadow = true;
    this.mesh.receiveShadow = true;
    this.mesh.bind(this.rig.skeleton, new THREE.Matrix4());
    this.body.group.add(this.mesh);

    const sec = footSections(ctx);
    this.refBall = sec.ballZ; // distância tornozelo → dedo no corpo de referência
    this.toeIdx = toeIdx;
    this.footIdx = footIdx;
    this.refit();
    this.off = this.body.onChange(() => this.refit());
  }

  /** Acompanha o pé do corpo atual: posição do tornozelo, escala pelo comprimento do pé, chão. */
  refit() {
    const A = this.rig.headWorld[this.footIdx];
    const T = this.rig.headWorld[this.toeIdx];
    const s = Math.max(0.5, Math.min(1.8, (T.z - A.z) / this.refBall));
    const floor = this.body.floorY;
    const P = this.position;
    const rel = this.rel;
    for (let k = 0; k < P.length / 3; k++) {
      P[k * 3] = A.x + rel[k * 3] * s;
      P[k * 3 + 1] = floor + rel[k * 3 + 1];
      P[k * 3 + 2] = A.z + rel[k * 3 + 2] * s;
    }
    this.geometry.attributes.position.needsUpdate = true;
    this.geometry.computeVertexNormals();
  }

  setStyle() {}

  dispose() {
    this.off?.();
    this.geometry.dispose();
    this.mesh.removeFromParent();
  }
}

/** Construtor da peça 'shoes'. options: { heel (m), style 0 = scarpin, 1 = botim, thickness (espessura do salto) } */
export function shoes(ctx, o, { style, dresser, entry }) {
  const U = legAxial(ctx);
  const { pos, nrm, ref, rig } = ctx;
  const floorRef = Math.min(...Array.from({ length: ctx.N }, (_, v) => pos[v * 3 + 1]).filter((_, i) => i % 7 === 0));
  const ank = { L: ref.heads[rig.index.get('foot.L')], R: ref.heads[rig.index.get('foot.R')] };
  const boot = o.style === 1;
  const uCap = 0.012 + (boot ? 0.115 : 0);
  const foot = (v) => {
    const sd = pos[v * 3] >= 0 ? ank.L : ank.R;
    return { yl: pos[v * 3 + 1] - floorRef, zl: pos[v * 3 + 2] - sd.z, dx: Math.abs(pos[v * 3] - sd.x) };
  };
  // altura da boca do sapato (linha do cabedal) em função de z: alta no calcanhar, baixa no meio do pé
  const yTop = (zl) => 0.073 - 0.034 * smoothstep(-0.012, 0.045, zl) + 0.004 * smoothstep(0.06, 0.098, zl);
  const zVamp = (dx) => 0.1 + 0.012 * smoothstep(0.015, 0.05, dx); // fecha o peito do pé
  const region = (v) => Math.max(U[v] - uCap, ank.L.z - 0.08 - pos[v * 3 + 2], foot(v).zl - Z_CUT);
  const upperField = (v) => {
    const f = region(v);
    if (boot) return f;
    const { yl, zl, dx } = foot(v);
    return Math.max(f, Math.min(yl - yTop(zl), zVamp(dx) - zl));
  };
  const upper = {
    name: 'shoes.upper',
    layer: 3,
    offsetFn: () => 0.0042,
    field: upperField,
    uv: (v) => [pos[v * 3] * 1.0 + pos[v * 3 + 2], pos[v * 3 + 1]],
    castShadow: true,
  };
  const sole = {
    name: 'shoes.sole',
    layer: 4,
    material: entry.mat2,
    // faixa inferior do pé: mais grossa embaixo, afinando até a espessura do cabedal na borda
    offsetFn: (v) => 0.0042 + (SOLE - 0.0042 - 0.0008) * smoothstep(WELT, 0.003, foot(v).yl) + 0.0008 * Math.max(0, -nrm[v * 3 + 1]),
    field: (v) => Math.max(region(v), foot(v).yl - WELT),
    edge: () => 1,
    uv: (v) => [pos[v * 3], pos[v * 3 + 2]],
    castShadow: true,
  };
  const objects = [];
  ctx.body.setGroundLift(SOLE);
  objects.push({ id: 'ground', object: { dispose: () => ctx.body.setGroundLift(0) } });
  for (const side of ['L', 'R']) {
    const post = new HeelPost({ body: ctx.body, animator: dresser.sim.animator, side, material: entry.mat2, thickness: o.thickness, lift: SOLE });
    objects.push({ id: `heel${side}`, object: post, update: () => post.update(), dispose: () => post.dispose() });
    const box = new ToeBox({ ctx, side, materials: [entry.mat, entry.mat2] });
    objects.push({ id: `toe${side}`, object: box, dispose: () => box.dispose() });
  }
  return { shells: [upper, sole], objects };
}
