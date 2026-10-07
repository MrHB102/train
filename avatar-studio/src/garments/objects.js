// Objetos livres presos a um osso: laço/gravata borboleta e rabo de coelha (pompom de pelo com mola).
// A posição de encaixe vem de um ponto da superfície de referência preso ao corpo (triângulo + baricêntricas),
// então acompanha qualquer morph; o objeto em si é rígido no osso (e o pompom balança numa mola 3D).
import * as THREE from 'three';
import { getSurface } from './ribbon.js';

const smooth = (a, b, x) => {
  const t = Math.min(1, Math.max(0, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
};

/** Ponto de superfície: lança um raio (de fora para dentro) na referência e guarda triângulo + baricêntricas. */
export function surfaceAnchor(ctx, origin, dir) {
  const hit = getSurface(ctx).cast(origin, dir, 2);
  return hit ? { verts: hit.verts, bary: hit.bary } : null;
}

/** Posição e normal atuais (espaço do avatar) de uma âncora na superfície do corpo. */
export function anchorNow(anchor, body, out = {}) {
  const P = body.pos;
  const N = body.normals;
  const p = (out.p ||= new THREE.Vector3());
  const n = (out.n ||= new THREE.Vector3());
  p.set(0, 0, 0);
  n.set(0, 0, 0);
  for (let k = 0; k < 3; k++) {
    const v = anchor.verts[k] * 3;
    const w = anchor.bary[k];
    p.x += P[v] * w; p.y += P[v + 1] * w; p.z += P[v + 2] * w;
    n.x += N[v] * w; n.y += N[v + 1] * w; n.z += N[v + 2] * w;
  }
  n.normalize();
  return out;
}

// ------------------------------------------------------------------------------------------------ laço
/** Gravata borboleta / laço: dois lóbulos fofos de cetim e um nó central, no plano x-y (frente +z). */
export function makeBowGeometry(size = 1) {
  const pos = [], nor = [], uv = [], edge = [], idx = [];
  const addSheet = (sx, sheet, nu, nv) => {
    const base = pos.length / 3;
    for (let i = 0; i <= nu; i++) {
      const u = i / nu;
      const hh = 0.0042 + 0.0128 * Math.pow(u, 0.85);
      const x = sx * (0.0065 + 0.031 * u);
      for (let j = 0; j <= nv; j++) {
        const v = (j / nv) * 2 - 1;
        const fat = Math.pow(Math.max(0, 1 - v * v), 0.55) * Math.sin(Math.PI * Math.min(1, u * 1.12 + 0.07));
        const ripple = 0.0005 * Math.sin(v * 9.4) * u;
        const z = sheet * (0.0044 * fat * (sheet > 0 ? 1 : 0.55) + ripple * (sheet > 0 ? 1 : 0));
        const y = v * hh;
        pos.push(x * size, y * size, z * size);
        nor.push(0, 0, sheet);
        uv.push(x * size, y * size);
        edge.push(Math.min(1 - Math.abs(v), 1 - u) * 0.006 * size);
      }
    }
    for (let i = 0; i < nu; i++) {
      for (let j = 0; j < nv; j++) {
        const a = base + i * (nv + 1) + j, b = a + 1, c = a + (nv + 1) + 1, d = a + (nv + 1);
        if ((sx > 0) === (sheet > 0)) idx.push(a, b, c, a, c, d);
        else idx.push(a, c, b, a, d, c);
      }
    }
  };
  for (const sx of [1, -1]) {
    addSheet(sx, 1, 10, 12);
    addSheet(sx, -1, 10, 12);
  }
  // nó central: elipsoide com leve vinco
  const kb = pos.length / 3;
  const nuK = 14, nvK = 10;
  for (let i = 0; i <= nvK; i++) {
    const th = (i / nvK) * Math.PI;
    for (let j = 0; j <= nuK; j++) {
      const ph = (j / nuK) * Math.PI * 2;
      const crease = 1 - 0.1 * Math.pow(Math.abs(Math.sin(ph * 2)), 4);
      const x = Math.sin(th) * Math.cos(ph) * 0.0062 * crease;
      const y = Math.cos(th) * 0.0075;
      const z = Math.sin(th) * Math.sin(ph) * 0.0058 + 0.0016;
      pos.push(x * size, y * size, z * size);
      nor.push(Math.sin(th) * Math.cos(ph), Math.cos(th), Math.sin(th) * Math.sin(ph));
      uv.push(x * size, y * size);
      edge.push(0.02);
    }
  }
  for (let i = 0; i < nvK; i++) {
    for (let j = 0; j < nuK; j++) {
      const a = kb + i * (nuK + 1) + j, b = a + 1, c = a + nuK + 2, d = a + nuK + 1;
      idx.push(a, d, c, a, c, b);
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  g.setAttribute('aUv', new THREE.Float32BufferAttribute(uv, 2));
  g.setAttribute('aEdge', new THREE.Float32BufferAttribute(edge, 1));
  g.setAttribute('aRest', new THREE.Float32BufferAttribute(pos.slice(), 3));
  g.setIndex(idx);
  g.computeVertexNormals();
  return g;
}

// ------------------------------------------------------------------------------------------------ pelo
/** Material de pelo em camadas (shell fur): cada instância é uma casca da esfera, com alpha por ruído 3D. */
export class FurMaterial extends THREE.MeshPhysicalMaterial {
  constructor({ noise, color = '#fbfbfb', length = 0.012, density = 46 } = {}) {
    super({ color: 0xffffff, roughness: 0.92, metalness: 0, sheen: 1, sheenRoughness: 0.55, sheenColor: new THREE.Color(1, 1, 1) });
    this.u = {
      uNoise: { value: noise },
      uFurColor: { value: new THREE.Color(color) },
      uFurLen: { value: length },
      uFurDensity: { value: density },
    };
  }
  customProgramCacheKey() {
    return 'fur-v1';
  }
  onBeforeCompile(shader) {
    Object.assign(shader.uniforms, this.u);
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\nattribute float aShell;\nuniform float uFurLen;\nvarying float vShell;\nvarying vec3 vObj;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvShell = aShell;\nvObj = position;\ntransformed += normal * (aShell * uFurLen);');
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', '#include <common>\nuniform highp sampler3D uNoise;\nuniform vec3 uFurColor;\nuniform float uFurDensity;\nvarying float vShell;\nvarying vec3 vObj;')
      .replace(
        '#include <map_fragment>',
        `#include <map_fragment>
        vec4 fn = texture(uNoise, vObj * uFurDensity);
        float fn2 = texture(uNoise, vObj * uFurDensity * 2.3 + 0.37).g;
        float strand = mix(fn.r, fn2, 0.4);
        float cut = vShell * vShell * 0.8 + 0.18 * vShell;
        if (vShell > 0.001 && strand < cut) discard;
        diffuseColor.rgb = uFurColor * mix(0.58, 1.06, vShell) * (0.94 + 0.12 * fn.b);`
      );
  }
  setColor(c) {
    this.u.uFurColor.value.set(c);
    this.sheenColor.set(c);
  }
}

/** Esfera de pelo: N cascas num InstancedMesh (uma chamada de desenho). */
export function makeFurBall(noise, { radius = 0.045, color = '#fbfbfb', shells = 18, length = 0.013 } = {}) {
  const geo = new THREE.SphereGeometry(radius, 28, 18);
  const arr = new Float32Array(shells);
  for (let i = 0; i < shells; i++) arr[i] = i / (shells - 1);
  geo.setAttribute('aShell', new THREE.InstancedBufferAttribute(arr, 1));
  const mat = new FurMaterial({ noise, color, length, density: 46 / (radius / 0.045) });
  const mesh = new THREE.InstancedMesh(geo, mat, shells);
  const m = new THREE.Matrix4();
  for (let i = 0; i < shells; i++) mesh.setMatrixAt(i, m.identity());
  mesh.frustumCulled = false;
  mesh.castShadow = true;
  return { mesh, material: mat, geometry: geo };
}

// ------------------------------------------------------------------------------------------------ rabo
/**
 * Rabo de coelha: pompom de pelo preso ao osso da pelve com uma mola 3D amortecida
 *   d'' = -ω² d - 2ζω d' - ganho · a_âncora
 * (mesmo modelo do Jiggle): balança ao andar, dançar e saltar.
 */
export class BunnyTail {
  constructor({ ctx, body, noise, o, style }) {
    this.body = body;
    this.o = o;
    this.bone = body.rig.bones[body.rig.index.get('root')];
    this.boneIdx = body.rig.index.get('root');
    const L = ctx.L;
    // âncora: costas, logo acima do sulco entre os glúteos
    const y = L.y.hipJoint + 0.012 + o.height;
    this.anchor = surfaceAnchor(ctx, [0, y, -0.6], [0, 0, 1]);
    this.radius = 0.045 * o.size;
    const fur = makeFurBall(noise, { radius: this.radius, color: style.color, length: 0.013 * o.size });
    this.fur = fur;
    this.group = new THREE.Group();
    this.group.name = 'tail';
    this.group.add(fur.mesh);
    this.bone.add(this.group);
    this.d = new THREE.Vector3();
    this.v = new THREE.Vector3();
    this.prevA = null;
    this.prevV = new THREE.Vector3();
    this.af = new THREE.Vector3();
    this._p = new THREE.Vector3();
    this._q = new THREE.Quaternion();
    this._m = new THREE.Matrix4();
    this._state = {};
    this.refit();
    this.off = body.onChange(() => this.refit());
  }

  /** Reposiciona o encaixe no osso (o corpo mudou). */
  refit() {
    if (!this.anchor) return;
    const { p, n } = anchorNow(this.anchor, this.body, this._state);
    const head = this.body.rig.headWorld[this.boneIdx];
    // centro do pompom: sai da pele para trás e levemente para cima
    this.rest = new THREE.Vector3(p.x + n.x * this.radius * 0.85, p.y + n.y * this.radius * 0.85 + this.radius * 0.1, p.z + n.z * this.radius * 0.85).sub(head);
    this.group.position.copy(this.rest);
  }

  update(dt) {
    if (!this.anchor || dt <= 0) return;
    const bone = this.bone;
    const grp = this.body.group;
    // âncora no espaço do avatar (osso da pelve levando o ponto de repouso)
    const a = this._p.copy(this.rest).applyMatrix4(bone.matrixWorld);
    grp.worldToLocal(a);
    if (!this.prevA) {
      this.prevA = a.clone();
      return;
    }
    const vel = a.clone().sub(this.prevA).divideScalar(dt);
    const acc = vel.clone().sub(this.prevV).divideScalar(dt);
    const l = acc.length();
    if (l > 90) acc.multiplyScalar(90 / l);
    this.af.lerp(acc, Math.min(1, dt * 40));
    this.prevA.copy(a);
    this.prevV.copy(vel);
    const w = Math.PI * 2 * 3.0;
    const zeta = 0.16;
    const gain = 1.7;
    const steps = Math.min(8, Math.max(1, Math.ceil(dt * 240)));
    const hh = dt / steps;
    for (let s = 0; s < steps; s++) {
      this.v.x += (-w * w * this.d.x - 2 * zeta * w * this.v.x - this.af.x * gain) * hh;
      this.v.y += (-w * w * this.d.y - 2 * zeta * w * this.v.y - this.af.y * gain - 9.8 * 0.0) * hh;
      this.v.z += (-w * w * this.d.z - 2 * zeta * w * this.v.z - this.af.z * gain) * hh;
      this.d.addScaledVector(this.v, hh);
    }
    const len = this.d.length();
    const maxD = 0.075;
    if (len > 1e-6) {
      const soft = maxD * Math.tanh(len / maxD);
      if (soft < len) {
        this.d.multiplyScalar(soft / len);
        this.v.multiplyScalar(0.9);
      }
    }
    // deslocamento (avatar) → referencial do osso
    bone.getWorldQuaternion(this._q);
    const qi = new THREE.Quaternion();
    grp.getWorldQuaternion(qi).invert();
    this._q.premultiply(qi).invert();
    this.group.position.copy(this.rest).add(this.d.clone().applyQuaternion(this._q));
  }

  setStyle(style) {
    this.fur.material.setColor(style.color);
  }

  dispose() {
    this.off?.();
    this.group.removeFromParent();
    this.fur.geometry.dispose();
    this.fur.material.dispose();
  }
}

// ------------------------------------------------------------------------------------------------ laço preso ao pescoço
export class NeckBow {
  constructor({ ctx, body, material, o, collarMid }) {
    this.body = body;
    this.ctx = ctx;
    const rig = body.rig;
    this.boneIdx = rig.index.get('neck01');
    this.bone = rig.bones[this.boneIdx];
    const L = ctx.L;
    this.y = L.y.neckBase + (collarMid ?? 0.026) + o.lift * 0 - 0.004;
    this.anchor = surfaceAnchor(ctx, [0, this.y, 0.6], [0, 0, -1]);
    this.geometry = makeBowGeometry(o.size);
    this.mesh = new THREE.Mesh(this.geometry, material);
    this.mesh.castShadow = true;
    this.mesh.frustumCulled = false;
    this.group = new THREE.Group();
    this.group.add(this.mesh);
    this.bone.add(this.group);
    this._state = {};
    this.refit();
    this.off = body.onChange(() => this.refit());
  }

  refit() {
    if (!this.anchor) return;
    const { p, n } = anchorNow(this.anchor, this.body, this._state);
    const head = this.body.rig.headWorld[this.boneIdx];
    this.group.position.set(p.x + n.x * 0.0075, p.y + n.y * 0.0075, p.z + n.z * 0.0075).sub(head);
    // orienta o plano do laço para fora, ao longo da normal da pele
    const z = n.clone();
    const up = new THREE.Vector3(0, 1, 0);
    const x = new THREE.Vector3().crossVectors(up, z).normalize();
    const y = new THREE.Vector3().crossVectors(z, x);
    this.group.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(x, y, z));
  }

  dispose() {
    this.off?.();
    this.group.removeFromParent();
    this.geometry.dispose();
  }
}

void smooth;
