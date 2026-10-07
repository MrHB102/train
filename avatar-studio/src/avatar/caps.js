// Caps: fecham os Cuts (pescoço e ombros) com uma cúpula rasa que acompanha morphs, pose e Jiggle.
// O anel externo coincide com o contorno do corte; os anéis internos vão para o plano médio do laço e
// sobem em cúpula. As normais são analíticas (calota esférica), então o sombreamento é liso mesmo quando
// o contorno do corte é irregular.
import * as THREE from 'three';

const RINGS = 6;
const DOME = 0.28; // altura da cúpula relativa ao raio médio do Cut
const TILT = (DOME * Math.PI) / 2; // inclinação da normal na borda da cúpula
const BEAD = 8; // lados do anel arredondado que cobre a borda do corte
const BEAD_R = 0.0042; // raio do anel (m): maior que o serrilhado do corte (~2.5 mm)

export class Caps {
  constructor(pkg, bodyPos) {
    this.pkg = pkg;
    this.loops = pkg.meta.loops;
    const { skinIndex, skinWeight } = pkg;
    const tris = [];
    this.layout = []; // por laço: {start, n, center, triStart, triEnd}
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
    let count = 0;
    for (const loop of this.loops) {
      const n = loop.length;
      const start = count;
      const loopW = loop.map(w4);
      const centerW = new Map();
      for (const m of loopW) for (const [b, w] of m) centerW.set(b, (centerW.get(b) || 0) + w / n);
      const pushSkin = (mix) => {
        const top = [...mix.entries()].sort((a, b) => b[1] - a[1]).slice(0, 4);
        const tot = top.reduce((a, b) => a + b[1], 0) || 1;
        for (let j = 0; j < 4; j++) {
          skinI.push(top[j] ? top[j][0] : 0);
          skinW.push(top[j] ? top[j][1] / tot : 0);
        }
      };
      for (let k = 0; k < RINGS; k++) {
        const s = k / RINGS;
        for (let i = 0; i < n; i++) {
          const mix = new Map();
          for (const [b, w] of loopW[i]) mix.set(b, (mix.get(b) || 0) + w * (1 - s));
          for (const [b, w] of centerW) mix.set(b, (mix.get(b) || 0) + w * s);
          pushSkin(mix);
        }
      }
      pushSkin(centerW); // vértice central
      const center = start + RINGS * n;
      // anel arredondado (bead): BEAD vértices ao redor de cada vértice da borda, com os pesos dele
      const beadStart = start + RINGS * n + 1;
      for (let i = 0; i < n; i++) for (let j = 0; j < BEAD; j++) pushSkin(loopW[i]);
      const triStart = tris.length;
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
      for (let i = 0; i < n; i++) {
        const i2 = (i + 1) % n;
        for (let j = 0; j < BEAD; j++) {
          const j2 = (j + 1) % BEAD;
          const a = beadStart + i * BEAD + j;
          const b = beadStart + i * BEAD + j2;
          const c = beadStart + i2 * BEAD + j2;
          const d = beadStart + i2 * BEAD + j;
          tris.push(a, b, c, a, c, d);
        }
      }
      this.layout.push({ start, n, center, beadStart, triStart, triEnd: tris.length });
      count += RINGS * n + 1 + n * BEAD;
    }
    this.count = count;
    this.position = new Float32Array(count * 3);
    this.normal = new Float32Array(count * 3);
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
    // sinal do normal de Newell de cada laço em relação ao eixo de saída de referência
    this.loops.forEach((_, li) => {
      this.signs[li] = Math.sign(this._axis(li, bodyPos).dot(this.refAxes[li])) || 1;
    });
    this.update(bodyPos);
    // orientação de cada triângulo pelas normais analíticas dos seus vértices
    {
      const I = this.index;
      const P = this.position;
      const Nn = this.normal;
      const a = new THREE.Vector3();
      const b = new THREE.Vector3();
      const c = new THREE.Vector3();
      const nv = new THREE.Vector3();
      for (let t = 0; t < I.length; t += 3) {
        a.fromArray(P, I[t] * 3);
        b.fromArray(P, I[t + 1] * 3);
        c.fromArray(P, I[t + 2] * 3);
        const g = b.sub(a).cross(c.sub(a));
        nv.set(0, 0, 0);
        for (let k = 0; k < 3; k++) nv.x += Nn[I[t + k] * 3], nv.y += Nn[I[t + k] * 3 + 1], nv.z += Nn[I[t + k] * 3 + 2];
        if (g.dot(nv) < 0) {
          const tmp = I[t + 1];
          I[t + 1] = I[t + 2];
          I[t + 2] = tmp;
        }
      }
      this.geometry.index.needsUpdate = true;
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
    const nor = this.normal;
    const c = new THREE.Vector3();
    const rad = new THREE.Vector3();
    this.loops.forEach((loop, li) => {
      const { start, n, center, beadStart } = this.layout[li];
      c.set(0, 0, 0);
      for (const v of loop) c.x += bodyPos[v * 3], c.y += bodyPos[v * 3 + 1], c.z += bodyPos[v * 3 + 2];
      c.multiplyScalar(1 / n);
      const axis = this._axis(li, bodyPos);
      let radius = 0;
      for (const v of loop) radius += Math.hypot(bodyPos[v * 3] - c.x, bodyPos[v * 3 + 1] - c.y, bodyPos[v * 3 + 2] - c.z);
      radius /= n;
      const H = DOME * radius;
      for (let i = 0; i < n; i++) {
        const v = loop[i] * 3;
        const dx = bodyPos[v] - c.x, dy = bodyPos[v + 1] - c.y, dz = bodyPos[v + 2] - c.z;
        const off = dx * axis.x + dy * axis.y + dz * axis.z; // distância ao plano médio do laço
        rad.set(dx - axis.x * off, dy - axis.y * off, dz - axis.z * off); // direção radial no plano
        const rl = rad.length() || 1;
        const rx = rad.x / rl, ry = rad.y / rl, rz = rad.z / rl;
        // anel arredondado centrado na borda projetada no plano médio
        for (let j = 0; j < BEAD; j++) {
          const th = (j / BEAD) * Math.PI * 2;
          const cr = Math.cos(th), sr = Math.sin(th);
          const o = (beadStart + i * BEAD + j) * 3;
          pos[o] = c.x + rad.x + (rx * cr + axis.x * sr) * BEAD_R;
          pos[o + 1] = c.y + rad.y + (ry * cr + axis.y * sr) * BEAD_R;
          pos[o + 2] = c.z + rad.z + (rz * cr + axis.z * sr) * BEAD_R;
          nor[o] = rx * cr + axis.x * sr;
          nor[o + 1] = ry * cr + axis.y * sr;
          nor[o + 2] = rz * cr + axis.z * sr;
        }
        for (let k = 0; k < RINGS; k++) {
          const s = k / RINGS;
          const lift = H * Math.sin(s * Math.PI * 0.5) + off * Math.pow(1 - s, 3);
          const o = (start + k * n + i) * 3;
          pos[o] = c.x + rad.x * (1 - s) + axis.x * lift;
          pos[o + 1] = c.y + rad.y * (1 - s) + axis.y * lift;
          pos[o + 2] = c.z + rad.z * (1 - s) + axis.z * lift;
          const g = TILT * Math.cos(s * Math.PI * 0.5);
          let nx = axis.x + rx * g, ny = axis.y + ry * g, nz = axis.z + rz * g;
          const l = Math.hypot(nx, ny, nz) || 1;
          nor[o] = nx / l; nor[o + 1] = ny / l; nor[o + 2] = nz / l;
        }
      }
      const o = center * 3;
      pos[o] = c.x + axis.x * H;
      pos[o + 1] = c.y + axis.y * H;
      pos[o + 2] = c.z + axis.z * H;
      nor[o] = axis.x; nor[o + 1] = axis.y; nor[o + 2] = axis.z;
    });
    this.geometry.attributes.position.needsUpdate = true;
    this.geometry.attributes.normal.needsUpdate = true;
  }
}
