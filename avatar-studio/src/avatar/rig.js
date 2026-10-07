// Rig do Body: ossos THREE.Bone sem rotação de repouso (eixos globais), reposicionados a cada morph.
import * as THREE from 'three';

export class Rig {
  constructor(pkg) {
    this.pkg = pkg;
    const defs = pkg.meta.bones;
    this.defs = defs;
    this.count = defs.length;
    this.names = defs.map((b) => b.n);
    this.index = new Map(this.names.map((n, i) => [n, i]));
    this.parent = defs.map((b) => b.p);
    this.bones = defs.map((b) => {
      const bone = new THREE.Bone();
      bone.name = b.n;
      return bone;
    });
    this.root = this.bones[0];
    defs.forEach((b, i) => {
      if (b.p >= 0) this.bones[b.p].add(this.bones[i]);
    });
    this.headWorld = defs.map(() => new THREE.Vector3());
    this.tailWorld = defs.map(() => new THREE.Vector3());
    this.restLocal = defs.map(() => new THREE.Vector3());
    this.offset = defs.map(() => new THREE.Vector3()); // deslocamentos dinâmicos (Jiggle, root motion)
    this.skeleton = new THREE.Skeleton(this.bones, defs.map(() => new THREE.Matrix4()));

    // vértices influenciados por cada junta virtual (para posicionar a junta no centróide ponderado)
    this.virtualInfluence = new Map();
    const { skinIndex, skinWeight } = pkg;
    for (let i = 0; i < defs.length; i++) if (defs[i].v) this.virtualInfluence.set(i, []);
    const nv = pkg.meta.vertCount;
    for (let v = 0; v < nv; v++) {
      for (let j = 0; j < 4; j++) {
        const b = skinIndex[v * 4 + j];
        const list = this.virtualInfluence.get(b);
        if (list && skinWeight[v * 4 + j] > 0) list.push(v, skinWeight[v * 4 + j] / 255);
      }
    }
  }

  /** Atualiza as posições de repouso a partir das posições base morfadas e dos vértices do corpo. */
  updateRest(P, bodyPos) {
    const tmp = new THREE.Vector3();
    for (let i = 0; i < this.count; i++) {
      const d = this.defs[i];
      if (d.v) {
        const inf = this.virtualInfluence.get(i);
        let sw = 0;
        const c = this.headWorld[i].set(0, 0, 0);
        for (let k = 0; k < inf.length; k += 2) {
          const w = inf[k + 1] * inf[k + 1];
          const v = inf[k] * 3;
          c.x += bodyPos[v] * w;
          c.y += bodyPos[v + 1] * w;
          c.z += bodyPos[v + 2] * w;
          sw += w;
        }
        if (sw > 0) c.multiplyScalar(1 / sw);
        this.tailWorld[i].copy(c);
      } else {
        this.headWorld[i].set(0, 0, 0);
        for (const v of d.h) this.headWorld[i].x += P[v * 3], this.headWorld[i].y += P[v * 3 + 1], this.headWorld[i].z += P[v * 3 + 2];
        this.headWorld[i].multiplyScalar(1 / d.h.length);
        this.tailWorld[i].set(0, 0, 0);
        for (const v of d.t) this.tailWorld[i].x += P[v * 3], this.tailWorld[i].y += P[v * 3 + 1], this.tailWorld[i].z += P[v * 3 + 2];
        this.tailWorld[i].multiplyScalar(1 / d.t.length);
      }
    }
    for (let i = 0; i < this.count; i++) {
      const p = this.parent[i];
      this.restLocal[i].copy(this.headWorld[i]);
      if (p >= 0) this.restLocal[i].sub(this.headWorld[p]);
      this.skeleton.boneInverses[i].makeTranslation(-this.headWorld[i].x, -this.headWorld[i].y, -this.headWorld[i].z);
    }
    void tmp;
    this.applyOffsets();
  }

  /** bone.position = repouso + deslocamento dinâmico. */
  applyOffsets() {
    for (let i = 0; i < this.count; i++) this.bones[i].position.copy(this.restLocal[i]).add(this.offset[i]);
  }

  resetPose() {
    for (let i = 0; i < this.count; i++) {
      this.bones[i].quaternion.identity();
      this.offset[i].set(0, 0, 0);
    }
    this.applyOffsets();
  }
}
