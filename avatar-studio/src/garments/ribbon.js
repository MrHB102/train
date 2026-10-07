// Ribbon: fita ou cordão colado à superfície do Body (alças, cordões de biquíni, laços, correntes, debruns).
// O caminho é um conjunto de amostras presas a triângulos do corpo (triângulo + baricêntricas), então a fita
// acompanha qualquer morph, pose e Jiggle como um Shell (ADR 0005) — e pode ser mais fina que a malha.
import * as THREE from 'three';
import { SurfaceIndex } from '../geometry/raycast.js';

export function getSurface(ctx) {
  if (!ctx._surface) ctx._surface = new SurfaceIndex(ctx.ref.pos, ctx.pkg.indices);
  return ctx._surface;
}

/** Anel horizontal em torno de um eixo vertical, de a0 a a1 (rad; 0 = frente, + = lado esquerdo do corpo). */
export function ringPath(ctx, { y, axis = [0, 0], a0 = 0, a1 = Math.PI * 2, n = 160, R = 0.5, closed }) {
  const S = getSurface(ctx);
  const out = [];
  const full = Math.abs(a1 - a0 - Math.PI * 2) < 1e-6;
  const cnt = full ? n : n + 1;
  for (let i = 0; i < cnt; i++) {
    const th = a0 + ((a1 - a0) * i) / n;
    const s = Math.sin(th), c = Math.cos(th);
    const hit = S.cast([axis[0] + R * s, y, axis[1] + R * c], [-s, 0, -c], R * 2);
    if (hit) out.push(hit);
  }
  return { samples: out, closed: closed ?? full };
}

/** Linha poligonal na frente (facing = +1) ou nas costas (-1), dada em coordenadas (x, y) de referência. */
export function linePath(ctx, pts, { facing = 1, step = 0.003 } = {}) {
  const S = getSurface(ctx);
  const out = [];
  for (let k = 0; k < pts.length - 1; k++) {
    const [x0, y0] = pts[k];
    const [x1, y1] = pts[k + 1];
    const len = Math.hypot(x1 - x0, y1 - y0);
    const m = Math.max(1, Math.ceil(len / step));
    for (let i = 0; i < m + (k === pts.length - 2 ? 1 : 0); i++) {
      const t = i / m;
      const hit = S.cast([x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, facing * 0.5], [0, 0, -facing], 1.2);
      if (hit) out.push(hit);
    }
  }
  return { samples: out, closed: false };
}

const tmpA = new THREE.Vector3();
const tmpB = new THREE.Vector3();
const tmpC = new THREE.Vector3();

export class Ribbon {
  /**
   * spec: { name, samples, closed, width (m | (i,n)=>m), offset (m | (i,n)=>m), profile: 'flat'|'round',
   *         sides, material, layer, castShadow, uvScale }
   */
  constructor(ctx, spec) {
    this.ctx = ctx;
    this.spec = spec;
    this.layer = spec.layer ?? 2;
    this.opaque = false; // não esconde o corpo por baixo
    this.covered = new Set();
    this.srcTri = new Uint32Array(0);
    const { pkg } = ctx;
    const samples = spec.samples;
    const n = (this.n = samples.length);
    const round = spec.profile === 'round';
    this.round = round;
    this.sides = round ? spec.sides ?? 6 : 2;
    const S = this.sides;
    this.count = n * S;
    this.position = new Float32Array(this.count * 3);
    this.normal = new Float32Array(this.count * 3);
    const rest = new Float32Array(this.count * 3);
    const uv = new Float32Array(this.count * 2);
    const edge = new Float32Array(this.count);
    const skinIndex = new Uint8Array(this.count * 4);
    const skinWeight = new Float32Array(this.count * 4);
    this.widthAt = (i) => (typeof spec.width === 'function' ? spec.width(i, n) : spec.width ?? 0.005);
    this.offsetAt = (i) => (typeof spec.offset === 'function' ? spec.offset(i, n) : spec.offset ?? 0.002);

    let arc = 0;
    let prev = null;
    samples.forEach((smp, i) => {
      const m = new Map();
      for (let k = 0; k < 3; k++) {
        const v = smp.verts[k];
        for (let j = 0; j < 4; j++) {
          const w = (pkg.skinWeight[v * 4 + j] / 255) * smp.bary[k];
          if (w) m.set(pkg.skinIndex[v * 4 + j], (m.get(pkg.skinIndex[v * 4 + j]) || 0) + w);
        }
      }
      const top = [...m.entries()].sort((x, y) => y[1] - x[1]).slice(0, 4);
      const tot = top.reduce((s2, e) => s2 + e[1], 0) || 1;
      const p = smp.point;
      if (prev) arc += Math.hypot(p[0] - prev[0], p[1] - prev[1], p[2] - prev[2]);
      prev = p;
      const w = this.widthAt(i);
      for (let s = 0; s < S; s++) {
        const o = i * S + s;
        for (let j = 0; j < 4; j++) {
          skinIndex[o * 4 + j] = top[j] ? top[j][0] : 0;
          skinWeight[o * 4 + j] = top[j] ? top[j][1] / tot : 0;
        }
        rest[o * 3] = p[0]; rest[o * 3 + 1] = p[1]; rest[o * 3 + 2] = p[2];
        const cross = round ? Math.sin((s / S) * Math.PI * 2) * (w / 2) : (s === 0 ? -1 : 1) * (w / 2);
        uv[o * 2] = arc * (spec.uvScale ?? 1);
        uv[o * 2 + 1] = cross;
        edge[o] = round ? (w / 2) * (1 - Math.abs(Math.sin((s / S) * Math.PI * 2))) : w / 2 - Math.abs(cross);
      }
    });

    const ind = [];
    const segs = spec.closed ? n : n - 1;
    for (let i = 0; i < segs; i++) {
      const i2 = (i + 1) % n;
      for (let s = 0; s < (round ? S : 1); s++) {
        const s2 = round ? (s + 1) % S : 1;
        const a = i * S + s, b = i * S + s2, c = i2 * S + s2, d = i2 * S + s;
        ind.push(a, b, c, a, c, d);
      }
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(this.position, 3).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute('normal', new THREE.BufferAttribute(this.normal, 3).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute('aRest', new THREE.BufferAttribute(rest, 3));
    g.setAttribute('aUv', new THREE.BufferAttribute(uv, 2));
    g.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
    g.setAttribute('aEdge', new THREE.BufferAttribute(edge, 1));
    g.setAttribute('skinIndex', new THREE.Uint8BufferAttribute(skinIndex, 4));
    g.setAttribute('skinWeight', new THREE.Float32BufferAttribute(skinWeight, 4));
    this.indexArr = Uint32Array.from(ind);
    g.setIndex(new THREE.BufferAttribute(this.indexArr, 1));
    this.geometry = g;
    this.mesh = new THREE.SkinnedMesh(g, spec.material);
    this.mesh.name = spec.name;
    this.mesh.frustumCulled = false;
    this.mesh.castShadow = !!spec.castShadow;
    this.mesh.receiveShadow = true;
    this.mesh.bind(ctx.body.rig.skeleton, new THREE.Matrix4());
    this.oriented = false;
    this.update(ctx.body.pos, ctx.body.normals);
  }

  refresh() {
    this.update(this.ctx.body.pos, this.ctx.body.normals);
  }

  setHiddenSource() {}

  update(bodyPos, bodyNormals) {
    const { samples } = this.spec;
    const n = this.n;
    const S = this.sides;
    const P = this.position;
    const N = this.normal;
    const closed = this.spec.closed;
    const cen = (this._cen ??= new Float32Array(n * 3));
    const nor = (this._nor ??= new Float32Array(n * 3));
    for (let i = 0; i < n; i++) {
      const { verts, bary } = samples[i];
      let x = 0, y = 0, z = 0, nx = 0, ny = 0, nz = 0;
      for (let k = 0; k < 3; k++) {
        const v = verts[k] * 3;
        x += bodyPos[v] * bary[k]; y += bodyPos[v + 1] * bary[k]; z += bodyPos[v + 2] * bary[k];
        nx += bodyNormals[v] * bary[k]; ny += bodyNormals[v + 1] * bary[k]; nz += bodyNormals[v + 2] * bary[k];
      }
      const l = Math.hypot(nx, ny, nz) || 1;
      nx /= l; ny /= l; nz /= l;
      nor[i * 3] = nx; nor[i * 3 + 1] = ny; nor[i * 3 + 2] = nz;
      const off = this.offsetAt(i) + (this.round ? this.widthAt(i) / 2 : 0);
      cen[i * 3] = x + nx * off;
      cen[i * 3 + 1] = y + ny * off;
      cen[i * 3 + 2] = z + nz * off;
    }
    for (let i = 0; i < n; i++) {
      const ip = closed ? (i + n - 1) % n : Math.max(0, i - 1);
      const inx = closed ? (i + 1) % n : Math.min(n - 1, i + 1);
      tmpA.set(cen[inx * 3] - cen[ip * 3], cen[inx * 3 + 1] - cen[ip * 3 + 1], cen[inx * 3 + 2] - cen[ip * 3 + 2]);
      tmpB.set(nor[i * 3], nor[i * 3 + 1], nor[i * 3 + 2]);
      tmpC.crossVectors(tmpB, tmpA).normalize(); // lateral
      const w = this.widthAt(i);
      for (let s = 0; s < S; s++) {
        const o = (i * S + s) * 3;
        if (this.round) {
          const ph = (s / S) * Math.PI * 2;
          const c = Math.cos(ph), sn = Math.sin(ph);
          const dx = tmpC.x * c + tmpB.x * sn, dy = tmpC.y * c + tmpB.y * sn, dz = tmpC.z * c + tmpB.z * sn;
          P[o] = cen[i * 3] + dx * (w / 2); P[o + 1] = cen[i * 3 + 1] + dy * (w / 2); P[o + 2] = cen[i * 3 + 2] + dz * (w / 2);
          N[o] = dx; N[o + 1] = dy; N[o + 2] = dz;
        } else {
          const sg = s === 0 ? -1 : 1;
          P[o] = cen[i * 3] + tmpC.x * sg * (w / 2); P[o + 1] = cen[i * 3 + 1] + tmpC.y * sg * (w / 2); P[o + 2] = cen[i * 3 + 2] + tmpC.z * sg * (w / 2);
          N[o] = tmpB.x; N[o + 1] = tmpB.y; N[o + 2] = tmpB.z;
        }
      }
    }
    if (!this.oriented) {
      // orienta o enrolamento pelas normais (uma vez)
      const I = this.indexArr;
      let acc = 0;
      for (let t = 0; t < Math.min(I.length, 600); t += 3) {
        const a = I[t] * 3, b = I[t + 1] * 3, c = I[t + 2] * 3;
        const ux = P[b] - P[a], uy = P[b + 1] - P[a + 1], uz = P[b + 2] - P[a + 2];
        const vx = P[c] - P[a], vy = P[c + 1] - P[a + 1], vz = P[c + 2] - P[a + 2];
        const gx = uy * vz - uz * vy, gy = uz * vx - ux * vz, gz = ux * vy - uy * vx;
        acc += gx * N[a] + gy * N[a + 1] + gz * N[a + 2];
      }
      if (acc < 0) {
        for (let t = 0; t < I.length; t += 3) {
          const tmp = I[t + 1];
          I[t + 1] = I[t + 2];
          I[t + 2] = tmp;
        }
        this.geometry.index.needsUpdate = true;
      }
      this.oriented = true;
    }
    this.geometry.attributes.position.needsUpdate = true;
    this.geometry.attributes.normal.needsUpdate = true;
  }

  dispose() {
    this.geometry.dispose();
    this.mesh.removeFromParent();
  }
}
