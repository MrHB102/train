// Shell: roupa que gruda na superfície do Body e deforma com ele (ADR 0005).
// Recorta a malha do corpo de referência com um campo escalar (F <= 0 fica) e liga cada vértice novo
// ao corpo por (a, b, t) + deslocamento ao longo da normal. Pesos de skinning vêm do próprio corpo.
// Cada Shell conhece os triângulos do corpo que cobre por inteiro, para o Wardrobe esconder o que está
// por baixo (impede o corpo de vazar pelo tecido em qualquer morph/pose).
import * as THREE from 'three';
import { clipTriangles, compactClip } from '../geometry/clip.js';

export class Shell {
  /**
   * spec: { name, field(v,ctx)->metros (<=0 dentro), snap, offset|offsetFn(v,ctx), uv(v,ctx)->[u,v],
   *         material, castShadow, layer, opaque, coverMargin }
   */
  constructor(ctx, spec) {
    this.ctx = ctx;
    this.spec = spec;
    this.layer = spec.layer ?? 3;
    this.opaque = spec.opaque !== false;
    const { N, pkg } = ctx;
    const F = new Float32Array(N);
    for (let v = 0; v < N; v++) F[v] = spec.field(v, ctx);
    const edge = Float32Array.from(F); // distância (m) à borda antes do snap
    const res = compactClip(clipTriangles(pkg.indices, F, spec.snap ?? 0.0002));
    this.vertices = res.vertices;
    this.count = this.vertices.length;
    const M = this.count;
    this.srcTri = res.srcTri; // triângulo do corpo que originou cada triângulo do Shell
    this.indices = res.tris;

    // triângulos do corpo totalmente cobertos (com margem) por este Shell
    this.covered = new Set();
    {
      const I = pkg.indices;
      const margin = spec.coverMargin ?? 0.005;
      for (let t = 0; t < I.length; t += 3) {
        if (edge[I[t]] <= -margin && edge[I[t + 1]] <= -margin && edge[I[t + 2]] <= -margin) this.covered.add(t / 3);
      }
    }

    this.position = new Float32Array(M * 3);
    this.normal = new Float32Array(M * 3);
    const rest = new Float32Array(M * 3);
    const uvA = new Float32Array(M * 2);
    const edgeA = new Float32Array(M);
    this.offsets = new Float32Array(M);
    const skinIndex = new Uint8Array(M * 4);
    const skinWeight = new Float32Array(M * 4);
    const ref = ctx.ref;
    this.vertices.forEach((vt, k) => {
      const { a, b, t } = vt;
      for (let c = 0; c < 3; c++) rest[k * 3 + c] = ref.pos[a * 3 + c] * (1 - t) + ref.pos[b * 3 + c] * t;
      edgeA[k] = t === 0 ? Math.max(0, -edge[a]) : 0;
      if (spec.uv) {
        const uv = spec.uv(a, ctx, b, t);
        uvA[k * 2] = uv[0];
        uvA[k * 2 + 1] = uv[1];
      }
      const m = new Map();
      for (let j = 0; j < 4; j++) {
        const wa = pkg.skinWeight[a * 4 + j] / 255;
        if (wa) m.set(pkg.skinIndex[a * 4 + j], (m.get(pkg.skinIndex[a * 4 + j]) || 0) + wa * (1 - t));
        if (t) {
          const wb = pkg.skinWeight[b * 4 + j] / 255;
          if (wb) m.set(pkg.skinIndex[b * 4 + j], (m.get(pkg.skinIndex[b * 4 + j]) || 0) + wb * t);
        }
      }
      const top = [...m.entries()].sort((x, y) => y[1] - x[1]).slice(0, 4);
      const tot = top.reduce((s, e) => s + e[1], 0) || 1;
      for (let j = 0; j < 4; j++) {
        skinIndex[k * 4 + j] = top[j] ? top[j][0] : 0;
        skinWeight[k * 4 + j] = top[j] ? top[j][1] / tot : 0;
      }
    });
    this.refreshOffsets();

    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(this.position, 3).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute('normal', new THREE.BufferAttribute(this.normal, 3).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute('aRest', new THREE.BufferAttribute(rest, 3));
    g.setAttribute('aUv', new THREE.BufferAttribute(uvA, 2));
    g.setAttribute('uv', new THREE.BufferAttribute(uvA, 2));
    g.setAttribute('aEdge', new THREE.BufferAttribute(edgeA, 1));
    g.setAttribute('skinIndex', new THREE.Uint8BufferAttribute(skinIndex, 4));
    g.setAttribute('skinWeight', new THREE.Float32BufferAttribute(skinWeight, 4));
    g.setIndex(new THREE.BufferAttribute(this.indices, 1));
    this.geometry = g;
    this.mesh = new THREE.SkinnedMesh(g, spec.material);
    this.mesh.name = spec.name;
    this.mesh.frustumCulled = false;
    this.mesh.castShadow = !!spec.castShadow;
    this.mesh.receiveShadow = true;
    this.mesh.bind(ctx.body.rig.skeleton, new THREE.Matrix4());
    this.update(ctx.body.pos, ctx.body.normals);
  }

  /** (Re)avalia a espessura por vértice (após mudar parâmetros da receita). */
  refreshOffsets() {
    const { spec, ctx } = this;
    this.vertices.forEach((vt, k) => {
      const { a, b, t } = vt;
      this.offsets[k] = spec.offsetFn ? spec.offsetFn(a, ctx) * (1 - t) + (t ? spec.offsetFn(b, ctx) * t : 0) : spec.offset ?? 0.003;
    });
  }

  refresh() {
    this.refreshOffsets();
    this.update(this.ctx.body.pos, this.ctx.body.normals);
  }

  /** Mostra só os triângulos não cobertos por camadas superiores (índices de triângulos do corpo). */
  setHiddenSource(hidden) {
    const I = this.indices;
    const keep = [];
    for (let t = 0; t < I.length; t += 3) {
      if (!hidden || !hidden.has(this.srcTri[t / 3])) keep.push(I[t], I[t + 1], I[t + 2]);
    }
    this.geometry.setIndex(new THREE.BufferAttribute(Uint32Array.from(keep), 1));
  }

  /** Reposiciona sobre o Body atual (chamado a cada mudança de Trait). */
  update(bodyPos, bodyNormals) {
    const P = this.position;
    const N = this.normal;
    const off = this.offsets;
    for (let k = 0; k < this.count; k++) {
      const { a, b, t } = this.vertices[k];
      const s = 1 - t;
      let nx = bodyNormals[a * 3] * s + bodyNormals[b * 3] * t;
      let ny = bodyNormals[a * 3 + 1] * s + bodyNormals[b * 3 + 1] * t;
      let nz = bodyNormals[a * 3 + 2] * s + bodyNormals[b * 3 + 2] * t;
      const l = Math.hypot(nx, ny, nz) || 1;
      nx /= l; ny /= l; nz /= l;
      N[k * 3] = nx; N[k * 3 + 1] = ny; N[k * 3 + 2] = nz;
      const o = off[k];
      P[k * 3] = bodyPos[a * 3] * s + bodyPos[b * 3] * t + nx * o;
      P[k * 3 + 1] = bodyPos[a * 3 + 1] * s + bodyPos[b * 3 + 1] * t + ny * o;
      P[k * 3 + 2] = bodyPos[a * 3 + 2] * s + bodyPos[b * 3 + 2] * t + nz * o;
    }
    this.geometry.attributes.position.needsUpdate = true;
    this.geometry.attributes.normal.needsUpdate = true;
  }

  dispose() {
    this.geometry.dispose();
    this.mesh.removeFromParent();
  }
}
