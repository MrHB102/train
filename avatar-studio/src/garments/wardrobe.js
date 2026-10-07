// Wardrobe: guarda os Shells ativos, resolve camadas e esconde o que está coberto por roupa por cima.
// Isso impede o corpo (ou uma camada interna) de "vazar" por baixo do tecido em qualquer morph/pose
// e reduz overdraw.
import * as THREE from 'three';
import { Shell } from './shell.js';

export class Wardrobe {
  constructor(body, ctx) {
    this.body = body;
    this.ctx = ctx;
    this.items = new Map(); // id -> Shell
    this.bodyIndex = body.pkg.indices;
    body.onChange((b) => this.items.forEach((s) => s.update(b.pos, b.normals)));
  }

  add(id, spec) {
    this.remove(id, true);
    const shell = new Shell(this.ctx, spec);
    shell.id = id;
    this.items.set(id, shell);
    this.body.group.add(shell.mesh);
    this.updateCoverage();
    return shell;
  }

  remove(id, silent = false) {
    const s = this.items.get(id);
    if (!s) return;
    s.dispose();
    this.items.delete(id);
    if (!silent) this.updateCoverage();
  }

  clear() {
    for (const s of [...this.items.values()]) s.dispose();
    this.items.clear();
    this.updateCoverage();
  }

  /** Recalcula quais triângulos de cada camada ficam visíveis. */
  updateCoverage() {
    const shells = [...this.items.values()].filter((s) => s.mesh.visible);
    const bodyHidden = new Set();
    for (const s of shells) if (s.opaque) for (const t of s.covered) bodyHidden.add(t);
    const I = this.bodyIndex;
    const keep = [];
    for (let t = 0; t < I.length; t += 3) if (!bodyHidden.has(t / 3)) keep.push(I[t], I[t + 1], I[t + 2]);
    this.body.geometry.setIndex(new THREE.BufferAttribute(Uint32Array.from(keep), 1));
    for (const s of shells) {
      const hidden = new Set();
      for (const o of shells) if (o !== s && o.opaque && o.layer > s.layer) for (const t of o.covered) hidden.add(t);
      s.setHiddenSource(hidden);
    }
  }
}
