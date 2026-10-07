// Caps: fecham os Cuts (pescoço e ombros) com uma cúpula rasa que acompanha morphs, pose e Jiggle.
import * as THREE from 'three';

const RINGS = 5;
const DOME = 0.3; // altura da cúpula relativa ao raio médio do Cut

export class Caps {
  constructor(pkg, bodyPos) {
    this.pkg = pkg;
    this.loops = pkg.meta.loops;
    const { skinIndex, skinWeight } = pkg;
    const verts = [];
    const tris = [];
    this.layout = []; // por laço: {start, n}
    const w4 = (v) => {
      const m = new Map();
      for (let j = 0; j < 4; j++) {
        const wt = skinWeight[v * 4 + j];
        if (wt) m.set(skinIndex[v * 4 + j], wt / 255);
      }
      return m;
    };
    const skinI = [];
    const skinW = [];
    for (const loop of this.loops) {
      const n = loop.length;
      const start = skinI.length / 4;
      const loopW = loop.map(w4);
      const centerW = new Map();
      for (const m of loopW) for (const [b, w] of m) centerW.set(b, (centerW.get(b) || 0) + w / n);
      for (let k = 0; k < RINGS; k++) {
        const s = k / RINGS;
        for (let i = 0; i < n; i++) {
          const mix = new Map();
          for (const [b, w] of loopW[i]) mix.set(b, (mix.get(b) || 0) + w * (1 - s));
          for (const [b, w] of centerW) mix.set(b, (mix.get(b) || 0) + w * s);
          const top = [...mix.entries()].sort((a, b) => b[1] - a[1]).slice(0, 4);
          const tot = top.reduce((a, b) => a + b[1], 0) || 1;
          for (let j = 0; j < 4; j++) {
            skinI.push(top[j] ? top[j][0] : 0);
            skinW.push(top[j] ? top[j][1] / tot : 0);
          }
        }
      }
      // vértice central
      {
        const top = [...centerW.entries()].sort((a, b) => b[1] - a[1]).slice(0, 4);
        const tot = top.reduce((a, b) => a + b[1], 0) || 1;
        for (let j = 0; j < 4; j++) {
          skinI.push(top[j] ? top[j][0] : 0);
          skinW.push(top[j] ? top[j][1] / tot : 0);
        }
      }
      const center = start + RINGS * n;
      for (let k = 0; k < RINGS - 1; k++) {
        for (let i = 0; i < n; i++) {
          const a = start + k * n + i;
          const b = start + k * n + ((i + 1) % n);
          const c = start + (k + 1) * n + ((i + 1) % n);
          const d = start + (k + 1) * n + i;
          tris.push(a, b, c, a, c, d);
        }
      }
      for (let i = 0; i < n; i++) {
        const a = start + (RINGS - 1) * n + i;
        const b = start + (RINGS - 1) * n + ((i + 1) % n);
        tris.push(a, b, center);
      }
      this.layout.push({ start, n, center });
      for (let q = 0; q < RINGS * n + 1; q++) verts.push(0, 0, 0);
    }
    this.count = verts.length / 3;
    this.position = new Float32Array(verts);
    this.normal = new Float32Array(verts.length);
    this.index = Uint16Array.from(tris);
    this.skinIndex = Uint8Array.from(skinI);
    this.skinWeight = Float32Array.from(skinW);
    this.refAxes = pkg.meta.loopAxes.map((a) => new THREE.Vector3(...a));
    this.signs = this.loops.map(() => 1);
    this.geometry = new THREE.BufferGeometry();
    this.geometry.setAttribute('position', new THREE.BufferAttribute(this.position, 3).setUsage(THREE.DynamicDrawUsage));
    this.geometry.setAttribute('normal', new THREE.BufferAttribute(this.normal, 3).setUsage(THREE.DynamicDrawUsage));
    this.geometry.setAttribute('skinIndex', new THREE.Uint8BufferAttribute(this.skinIndex, 4));
    this.geometry.setAttribute('skinWeight', new THREE.Float32BufferAttribute(this.skinWeight, 4));
    this.geometry.setIndex(new THREE.BufferAttribute(this.index, 1));
    this.flipped = false;
    // sinal do normal de Newell de cada laço em relação ao eixo de saída de referência
    this.loops.forEach((_, li) => {
      this.signs[li] = 1;
      this.signs[li] = Math.sign(this._axis(li, bodyPos).dot(this.refAxes[li])) || 1;
    });
    this.update(bodyPos);
    // orientação dos triângulos: a normal do primeiro triângulo deve coincidir com o eixo de saída
    {
      const I = this.index;
      const P = this.position;
      const a = new THREE.Vector3().fromArray(P, I[0] * 3);
      const b = new THREE.Vector3().fromArray(P, I[1] * 3);
      const c = new THREE.Vector3().fromArray(P, I[2] * 3);
      const nrm = b.sub(a).cross(c.sub(a));
      if (nrm.dot(this._axis(0, bodyPos)) < 0) {
        for (let t = 0; t < I.length; t += 3) {
          const tmp = I[t + 1];
          I[t + 1] = I[t + 2];
          I[t + 2] = tmp;
        }
        this.geometry.index.needsUpdate = true;
      }
    }
    this.update(bodyPos);
  }

  /** Eixo de saída do Cut: normal de Newell do laço (sinal fixado pela referência). */
  _axis(li, pos) {
    const loop = this.loops[li];
    const n = loop.length;
    let nx = 0, ny = 0, nz = 0;
    for (let i = 0; i < n; i++) {
      const a = loop[i] * 3;
      const b = loop[(i + 1) % n] * 3;
      nx += (pos[a + 1] - pos[b + 1]) * (pos[a + 2] + pos[b + 2]);
      ny += (pos[a + 2] - pos[b + 2]) * (pos[a] + pos[b]);
      nz += (pos[a] - pos[b]) * (pos[a + 1] + pos[b + 1]);
    }
    return new THREE.Vector3(nx, ny, nz).normalize().multiplyScalar(this.signs[li]);
  }

  /** bodyPos: posições dos vértices do corpo (a malha dos Caps nasce dos laços de borda). */
  update(bodyPos) {
    const pos = this.position;
    const c = new THREE.Vector3();
    const t = new THREE.Vector3();
    this.loops.forEach((loop, li) => {
      const { start, n, center } = this.layout[li];
      c.set(0, 0, 0);
      for (const v of loop) c.x += bodyPos[v * 3], c.y += bodyPos[v * 3 + 1], c.z += bodyPos[v * 3 + 2];
      c.multiplyScalar(1 / n);
      const axis = this._axis(li, bodyPos);
      let radius = 0;
      for (const v of loop) radius += Math.hypot(bodyPos[v * 3] - c.x, bodyPos[v * 3 + 1] - c.y, bodyPos[v * 3 + 2] - c.z);
      radius /= n;
      const H = DOME * radius;
      for (let k = 0; k < RINGS; k++) {
        const s = k / RINGS;
        const lift = H * Math.sin(s * Math.PI * 0.5);
        for (let i = 0; i < n; i++) {
          const v = loop[i];
          const o = (start + k * n + i) * 3;
          t.set(bodyPos[v * 3], bodyPos[v * 3 + 1], bodyPos[v * 3 + 2]).lerp(c, s);
          pos[o] = t.x + axis.x * lift;
          pos[o + 1] = t.y + axis.y * lift;
          pos[o + 2] = t.z + axis.z * lift;
        }
      }
      const o = center * 3;
      pos[o] = c.x + axis.x * H;
      pos[o + 1] = c.y + axis.y * H;
      pos[o + 2] = c.z + axis.z * H;
    });
    this._normals();
    this.geometry.attributes.position.needsUpdate = true;
    this.geometry.attributes.normal.needsUpdate = true;
  }

  _normals() {
    const P = this.position;
    const N = this.normal;
    N.fill(0);
    const I = this.index;
    for (let t = 0; t < I.length; t += 3) {
      const a = I[t] * 3, b = I[t + 1] * 3, c = I[t + 2] * 3;
      const ux = P[b] - P[a], uy = P[b + 1] - P[a + 1], uz = P[b + 2] - P[a + 2];
      const vx = P[c] - P[a], vy = P[c + 1] - P[a + 1], vz = P[c + 2] - P[a + 2];
      const nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx;
      for (const o of [a, b, c]) {
        N[o] += nx;
        N[o + 1] += ny;
        N[o + 2] += nz;
      }
    }
    for (let i = 0; i < N.length; i += 3) {
      const l = Math.hypot(N[i], N[i + 1], N[i + 2]) || 1;
      N[i] /= l;
      N[i + 1] /= l;
      N[i + 2] /= l;
    }
  }
}
