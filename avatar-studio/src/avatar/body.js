// Body: malha (com Cut e Caps), Rig e motor de morph. Fonte da verdade da forma do Avatar.
import * as THREE from 'three';
import { MorphEngine } from './morph.js';
import { Rig } from './rig.js';
import { Caps } from './caps.js';
import { Cavity } from './cavity.js';
import { neutralValues, normalizeAncestry } from '../domain/traits.js';
import { neutralDials, effectiveValues } from '../domain/dials.js';

export class Body {
  constructor(pkg) {
    this.pkg = pkg;
    this.morph = new MorphEngine(pkg);
    this.rig = new Rig(pkg);
    this.values = neutralValues();
    this.dials = neutralDials();
    this.slack = 0; // folga do Extended Range para o repique elástico
    this.groundLift = 0; // espessura da sola dos sapatos (m)
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
    this.cavity = new Cavity(pkg.indices, this.N);
    this.cav = new Float32Array(this.N);
    g.setAttribute('aCav', new THREE.BufferAttribute(this.cav, 1).setUsage(THREE.DynamicDrawUsage));
    this.geometry = g;

    this.mesh = new THREE.SkinnedMesh(g, new THREE.MeshStandardMaterial({ color: 0xd7a48e, roughness: 0.55 }));
    this.mesh.name = 'body';
    this.mesh.frustumCulled = false;
    this.mesh.castShadow = true;
    this.mesh.receiveShadow = true;
    this.group.add(this.mesh);

    this.buildLegSides();
    this.buildSmoothing();
    this.rebuild();
    // estado de referência (Traits neutros): as roupas são cortadas e coladas sobre ele (ADR 0005)
    this.reference = {
      P: Float32Array.from(this.morph.positions),
      pos: Float32Array.from(this.pos),
      normals: Float32Array.from(this.normals),
      heads: this.rig.headWorld.map((v) => v.clone()),
      tails: this.rig.tailWorld.map((v) => v.clone()),
    };
    // coordenadas de referência para texturas procedurais ancoradas na pele
    g.setAttribute('aRest', new THREE.BufferAttribute(Float32Array.from(this.reference.pos), 3));
    this.mesh.bind(this.rig.skeleton, new THREE.Matrix4());
    this.buildBustSides(this.reference.pos);

    this.caps = new Caps(pkg, this.pos);
    this.capsMesh = new THREE.SkinnedMesh(
      this.caps.geometry,
      new THREE.MeshPhysicalMaterial({ color: 0xc9c3be, roughness: 0.5, metalness: 0, sheen: 0.4, sheenRoughness: 0.6, sheenColor: new THREE.Color(0xffffff), clearcoat: 0.15, clearcoatRoughness: 0.4 })
    );
    this.capsMesh.name = 'caps';
    this.capsMesh.frustumCulled = false;
    this.capsMesh.castShadow = true;
    this.capsMesh.bind(this.rig.skeleton, new THREE.Matrix4());
    this.group.add(this.capsMesh);
    this.rig.clearAll();
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

  /** Atualiza a posição de Dials (parcial) e recalcula o Body. */
  setDials(partial) {
    this.dials = { ...this.dials, ...partial };
    this.rebuild();
    return this.dials;
  }

  /** Troca Traits e Dials de uma vez (um único rebuild). */
  setState(traits, dials) {
    if (traits) {
      let v = { ...this.values, ...traits };
      if (Object.keys(traits).some((k) => k.startsWith('ancestry.'))) v = normalizeAncestry(v);
      this.values = v;
    }
    if (dials) this.dials = { ...this.dials, ...dials };
    this.rebuild();
  }

  /** Valores efetivos (Traits + Dials) que alimentam o motor de morph. */
  effective() {
    return effectiveValues(this.values, this.dials, this.slack);
  }

  rebuild() {
    const eff = this.effective();
    const P = this.morph.update(eff);
    const { stencilStart, stencilIdx, stencilW } = this.pkg;
    const pos = this.pos;
    // posição de cada vértice da malha subdividida/cortada = combinação linear dos vértices base
    for (let k = 0; k < this.N; k++) {
      let x = 0, y = 0, z = 0;
      for (let q = stencilStart[k], e = stencilStart[k + 1]; q < e; q++) {
        const j = stencilIdx[q] * 3;
        const w = stencilW[q];
        x += P[j] * w;
        y += P[j + 1] * w;
        z += P[j + 2] * w;
      }
      pos[k * 3] = x;
      pos[k * 3 + 1] = y;
      pos[k * 3 + 2] = z;
    }
    this.applyThighContact(pos, eff['thighs.contact'] || 0);
    this.applyBustContact(pos, eff['bust.contact'] ?? 1);
    this.applySmoothing(pos);
    this.computeNormals();
    this.cavity.update(pos, this.normals, this.cav);
    this.geometry.attributes.aCav.needsUpdate = true;
    this.rig.updateRest(P, pos);
    this.geometry.attributes.position.needsUpdate = true;
    this.geometry.attributes.normal.needsUpdate = true;
    if (this.caps) this.caps.update(pos);
    this.measureFloor();
    this.listeners.forEach((fn) => fn(this));
  }

  /** Lado da perna de cada vértice (+1 esquerda, -1 direita, 0 nenhum) a partir dos pesos de skinning. */
  buildLegSides() {
    const { skinIndex, skinWeight } = this.pkg;
    const names = this.rig.names;
    const side = (n) => (/^(upperleg0[12]|lowerleg0[12]|foot|toe\d-\d)\.L$/.test(n) ? 1 : /^(upperleg0[12]|lowerleg0[12]|foot|toe\d-\d)\.R$/.test(n) ? -1 : 0);
    const bs = names.map(side);
    this.legSide = new Int8Array(this.N);
    for (let v = 0; v < this.N; v++) {
      let l = 0, r = 0;
      for (let j = 0; j < 4; j++) {
        const w = skinWeight[v * 4 + j] / 255;
        const s = bs[skinIndex[v * 4 + j]];
        if (s > 0) l += w;
        else if (s < 0) r += w;
      }
      this.legSide[v] = l > 0.55 ? 1 : r > 0.55 ? -1 : 0;
    }
  }

  /** Contato entre as coxas: nenhuma perna atravessa a linha central (suave), formando a área de contato. */
  applyThighContact(pos, amount) {
    if (amount <= 0.001) return;
    const margin = 0.0012 + (1 - amount) * 0.03;
    const s = 0.006;
    for (let v = 0; v < this.N; v++) {
      const side = this.legSide[v];
      if (!side) continue;
      const x = pos[v * 3] * side; // distância à linha central, positiva do lado correto
      if (x < margin + s * 4) {
        // soft-max(x, margin): continua suave e nunca cruza a linha central
        const d = x - margin;
        const soft = d > s * 4 ? d : s * Math.log1p(Math.exp(d / s));
        const nx = margin + soft;
        pos[v * 3] = nx * side;
      }
    }
  }

  /**
   * Lado (+1 esquerda, -1 direita) e proximidade do mamilo de cada vértice da frente do tórax, a partir da
   * forma de referência. Serve ao contato entre os seios: nenhuma massa atravessa a linha central.
   */
  buildBustSides(refPos) {
    const rig = this.rig;
    const nip = ['L', 'R'].map((s) => rig.tailWorld[rig.index.get(`breast.${s}`)].clone());
    const yN = (nip[0].y + nip[1].y) / 2;
    this.bustSide = new Int8Array(this.N);
    this.bustWeight = new Float32Array(this.N);
    for (let v = 0; v < this.N; v++) {
      const x = refPos[v * 3], y = refPos[v * 3 + 1], z = refPos[v * 3 + 2];
      if (z < 0 || y < yN - 0.13 || y > yN + 0.15 || Math.abs(x) < 0.0015) continue;
      const n = x > 0 ? nip[0] : nip[1];
      const d = Math.hypot(x - n.x, y - n.y, z - n.z);
      const t = Math.min(1, Math.max(0, (d - 0.075) / (0.2 - 0.075)));
      const w = 1 - t * t * (3 - 2 * t);
      this.bustSide[v] = x > 0 ? 1 : -1;
      this.bustWeight[v] = w;
    }
  }

  /** Contato entre os seios: formam o sulco central sem se atravessar (mesmo método das coxas). */
  applyBustContact(pos, amount) {
    if (amount <= 0.001 || !this.bustSide) return;
    const s = 0.0035;
    for (let v = 0; v < this.N; v++) {
      const side = this.bustSide[v];
      if (!side) continue;
      const w = this.bustWeight[v];
      const margin = w * (0.0022 + (1 - amount) * 0.02);
      const x = pos[v * 3] * side;
      if (x < margin + s * 4) {
        const d = x - margin;
        const soft = d > s * 4 ? d : s * Math.log1p(Math.exp(d / s));
        pos[v * 3] = (margin + soft) * side;
      }
    }
  }

  /** Suavização "manequim" (mamilos e cruzamento): vizinhança dos vértices da zona. */
  buildSmoothing() {
    const zone = this.pkg.smoothZone;
    const I = this.pkg.indices;
    const nb = new Map();
    for (let v = 0; v < this.N; v++) if (zone[v]) nb.set(v, new Set());
    for (let t = 0; t < I.length; t += 3) {
      for (let e = 0; e < 3; e++) {
        const a = I[t + e];
        const s = nb.get(a);
        if (s) {
          s.add(I[t + ((e + 1) % 3)]);
          s.add(I[t + ((e + 2) % 3)]);
        }
      }
    }
    this.smoothList = [...nb.keys()];
    this.smoothNb = this.smoothList.map((v) => [...nb.get(v)]);
    this.smoothWeight = this.smoothList.map((v) => zone[v] / 255);
  }

  applySmoothing(pos, iterations = 24) {
    const list = this.smoothList;
    for (let it = 0; it < iterations; it++) {
      for (let i = 0; i < list.length; i++) {
        const v = list[i] * 3;
        const nb = this.smoothNb[i];
        let x = 0, y = 0, z = 0;
        for (const q of nb) {
          x += pos[q * 3]; y += pos[q * 3 + 1]; z += pos[q * 3 + 2];
        }
        const w = this.smoothWeight[i] * 0.6 / nb.length;
        pos[v] += x * w - pos[v] * 0.6 * this.smoothWeight[i];
        pos[v + 1] += y * w - pos[v + 1] * 0.6 * this.smoothWeight[i];
        pos[v + 2] += z * w - pos[v + 2] * 0.6 * this.smoothWeight[i];
      }
    }
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
    this.group.position.y = -min + this.groundLift; // os pés sempre apoiam no chão, qualquer que seja o comprimento das pernas
  }

  /** Espessura (m) da sola dos sapatos: o corpo sobe esse tanto para a sola, e não a pele, tocar o chão. */
  setGroundLift(m) {
    if (m === this.groundLift) return;
    this.groundLift = m;
    this.group.position.y = -this.floorY + m;
  }
}
