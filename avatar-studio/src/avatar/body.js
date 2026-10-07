// Body: malha (com Cut e Caps), Rig e motor de morph. Fonte da verdade da forma do Avatar.
import * as THREE from 'three';
import { MorphEngine } from './morph.js';
import { Rig } from './rig.js';
import { Caps } from './caps.js';
import { neutralValues, normalizeAncestry } from '../domain/traits.js';

export class Body {
  constructor(pkg) {
    this.pkg = pkg;
    this.morph = new MorphEngine(pkg);
    this.rig = new Rig(pkg);
    this.values = neutralValues();
    this.N = pkg.meta.vertCount;
    this.pos = new Float32Array(this.N * 3); // posições do corpo na pose de repouso (m)
    this.normals = new Float32Array(this.N * 3);
    this.listeners = new Set();

    this.group = new THREE.Group();
    this.group.name = 'avatar';
    this.group.add(this.rig.root);

    // geometria do corpo
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(this.pos, 3).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute('normal', new THREE.BufferAttribute(this.normals, 3).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute('skinIndex', new THREE.Uint8BufferAttribute(pkg.skinIndex, 4));
    g.setAttribute('skinWeight', new THREE.Uint8BufferAttribute(pkg.skinWeight, 4, true));
    g.setIndex(new THREE.BufferAttribute(pkg.indices, 1));
    this.geometry = g;

    this.mesh = new THREE.SkinnedMesh(g, new THREE.MeshStandardMaterial({ color: 0xd7a48e, roughness: 0.55 }));
    this.mesh.name = 'body';
    this.mesh.frustumCulled = false;
    this.mesh.castShadow = true;
    this.mesh.receiveShadow = true;
    this.group.add(this.mesh);

    this.rebuild();
    this.mesh.bind(this.rig.skeleton, new THREE.Matrix4());

    this.caps = new Caps(pkg, this.pos);
    this.capsMesh = new THREE.SkinnedMesh(this.caps.geometry, new THREE.MeshStandardMaterial({ color: 0x23232b, roughness: 0.35, metalness: 0.2 }));
    this.capsMesh.name = 'caps';
    this.capsMesh.frustumCulled = false;
    this.capsMesh.castShadow = true;
    this.capsMesh.bind(this.rig.skeleton, new THREE.Matrix4());
    this.group.add(this.capsMesh);
    this.rig.resetPose();
  }

  onChange(fn) {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }

  /** Atualiza valores de Traits (parcial) e recalcula o Body. */
  setTraits(partial, changedId) {
    let v = { ...this.values, ...partial };
    if (Object.keys(partial).some((k) => k.startsWith('ancestry.'))) v = normalizeAncestry(v, changedId);
    this.values = v;
    this.rebuild();
    return this.values;
  }

  rebuild() {
    const P = this.morph.update(this.values);
    const { bindA, bindB, bindT } = this.pkg;
    const pos = this.pos;
    for (let k = 0; k < this.N; k++) {
      const a = bindA[k] * 3;
      const b = bindB[k] * 3;
      const t = bindT[k];
      if (t === 0) {
        pos[k * 3] = P[a];
        pos[k * 3 + 1] = P[a + 1];
        pos[k * 3 + 2] = P[a + 2];
      } else {
        const s = 1 - t;
        pos[k * 3] = P[a] * s + P[b] * t;
        pos[k * 3 + 1] = P[a + 1] * s + P[b + 1] * t;
        pos[k * 3 + 2] = P[a + 2] * s + P[b + 2] * t;
      }
    }
    this.computeNormals();
    this.rig.updateRest(P, pos);
    this.geometry.attributes.position.needsUpdate = true;
    this.geometry.attributes.normal.needsUpdate = true;
    if (this.caps) this.caps.update(pos, P);
    this.measureFloor();
    this.listeners.forEach((fn) => fn(this));
  }

  computeNormals() {
    const P = this.pos;
    const N = this.normals;
    N.fill(0);
    const I = this.pkg.indices;
    for (let t = 0; t < I.length; t += 3) {
      const a = I[t] * 3, b = I[t + 1] * 3, c = I[t + 2] * 3;
      const ux = P[b] - P[a], uy = P[b + 1] - P[a + 1], uz = P[b + 2] - P[a + 2];
      const vx = P[c] - P[a], vy = P[c + 1] - P[a + 1], vz = P[c + 2] - P[a + 2];
      const nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx;
      N[a] += nx; N[a + 1] += ny; N[a + 2] += nz;
      N[b] += nx; N[b + 1] += ny; N[b + 2] += nz;
      N[c] += nx; N[c + 1] += ny; N[c + 2] += nz;
    }
    for (let i = 0; i < N.length; i += 3) {
      const l = Math.hypot(N[i], N[i + 1], N[i + 2]) || 1;
      N[i] /= l; N[i + 1] /= l; N[i + 2] /= l;
    }
  }

  /** Ground Contact (pose de repouso): menor y do corpo. */
  measureFloor() {
    let min = Infinity;
    for (let i = 1; i < this.pos.length; i += 3) if (this.pos[i] < min) min = this.pos[i];
    this.floorY = min;
  }
}
