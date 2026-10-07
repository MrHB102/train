// Sapatos de salto (scarpin) e botins, gerados proceduralmente sobre o pé do Body:
//  - cabedal: Shell recortado da superfície do pé, com garganta (abertura do peito do pé) e bico fechado;
//  - sola: Shell da faixa inferior do pé, mais espessa e com cor própria (solado vermelho, preto…);
//  - salto agulha: objeto rígido no osso do pé, inclinado pelo mesmo ângulo que a animação usa para "calçar" o
//    salto, de modo que fica perpendicular ao chão quando a pessoa está parada.
import * as THREE from 'three';
import { smoothstep, legAxial } from './fields.js';

const TAU = Math.PI * 2;

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
  constructor({ body, animator, side, material, thickness = 1 }) {
    this.body = body;
    this.animator = animator;
    this.side = side;
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
    const drop = (fm.ball + 0.03) * Math.sin(theta);
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

/** Construtor da peça 'shoes'. options: { heel (m), style 0 = scarpin, 1 = botim, thickness (espessura do salto) } */
export function shoes(ctx, o, { style, dresser, entry }) {
  const U = legAxial(ctx);
  const { pos, nrm, L, ref, rig } = ctx;
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
  const region = (v) => Math.max(U[v] - uCap, (ank.L.z - 0.08) - pos[v * 3 + 2]);
  const upperField = (v) => {
    const f = region(v);
    if (boot) return f;
    const { yl, zl, dx } = foot(v);
    return Math.max(f, Math.min(yl - yTop(zl), zVamp(dx) - zl));
  };
  // bico: no trecho dos dedos o deslocamento é radial a partir do eixo do pé, até um envelope liso (elipse na
  // seção, afinando na ponta): as cinco superfícies dos dedos viram uma ponta arredondada contínua
  const axisAt = (v) => {
    const sd = pos[v * 3] >= 0 ? ank.L : ank.R;
    const sg = pos[v * 3] >= 0 ? 1 : -1;
    const zl = pos[v * 3 + 2] - sd.z;
    return { x: sd.x + sg * 0.009 * smoothstep(0.05, 0.15, zl), y: floorRef + 0.0115, zl };
  };
  const toeW = (zl) => smoothstep(0.1, 0.15, zl);
  const toeInfo = (v) => {
    const a = axisAt(v);
    const w = toeW(a.zl);
    if (w <= 0) return null;
    const dx = pos[v * 3] - a.x;
    const dy = pos[v * 3 + 1] - a.y;
    const r = Math.hypot(dx, dy) || 1e-6;
    const taper = Math.sqrt(Math.max(0.05, 1 - Math.pow(Math.max(0, a.zl - 0.125) / 0.095, 2)));
    const cx = dx / r;
    const cy = dy / r;
    const hull = Math.hypot(cx * 0.046 * taper, cy * 0.0215 * taper);
    return { w, d: [cx, cy, 0], extra: Math.max(0, hull - r) };
  };
  const toe = (v) => {
    const t = toeInfo(v);
    return t ? t.w * t.extra : 0;
  };
  const toeDir = (v) => {
    const t = toeInfo(v);
    return t ? { d: t.d, w: t.w } : null;
  };
  const upper = {
    name: 'shoes.upper',
    layer: 3,
    offsetFn: (v) => 0.0042 + toe(v),
    dirFn: toeDir,
    field: upperField,
    uv: (v) => [pos[v * 3] * 1.0 + pos[v * 3 + 2], pos[v * 3 + 1]],
    castShadow: true,
  };
  const sole = {
    name: 'shoes.sole',
    layer: 4,
    material: entry.mat2,
    dirFn: toeDir,
    // faixa inferior do pé: mais grossa embaixo, afinando até a espessura do cabedal na borda
    offsetFn: (v) => {
      const { yl } = foot(v);
      return 0.0042 + toe(v) + 0.006 * smoothstep(0.016, 0.005, yl) + 0.0016 * Math.max(0, -nrm[v * 3 + 1]);
    },
    // faixa inferior do pé; nos dedos só a parte de baixo (senão a sola cobre as laterais dos dedos)
    field: (v) => {
      const f = foot(v);
      return Math.max(region(v), f.yl - (0.018 - 0.012 * toeW(f.zl)));
    },
    edge: () => 1,
    uv: (v) => [pos[v * 3], pos[v * 3 + 2]],
    castShadow: true,
  };
  const objects = [];
  for (const side of ['L', 'R']) {
    const post = new HeelPost({ body: ctx.body, animator: dresser.sim.animator, side, material: entry.mat2, thickness: o.thickness });
    objects.push({ id: `heel${side}`, object: post, update: () => post.update(), dispose: () => post.dispose() });
  }
  return { shells: [upper, sole], objects };
}

void TAU;
