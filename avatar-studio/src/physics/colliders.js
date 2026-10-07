// Colisores do corpo para o Drape: cápsulas com raio variável ajustadas às medidas do Body atual
// (circunferências das réguas: coxa, joelho, panturrilha, tornozelo, quadril) + esferas dos glúteos/barriga.
import * as THREE from 'three';

function perimeter(P, idxs) {
  let s = 0;
  for (let i = 0; i < idxs.length - 1; i++) {
    const a = idxs[i] * 3;
    const b = idxs[i + 1] * 3;
    s += Math.hypot(P[a] - P[b], P[a + 1] - P[b + 1], P[a + 2] - P[b + 2]);
  }
  return s;
}

export class BodyColliders {
  constructor(body) {
    this.body = body;
    this.rig = body.rig;
    this.list = [];
    this.def = [];
    const R = this.rig.index;
    const seg = (a, b, key) => ({ a: R.get(a), b: R.get(b), key });
    for (const s of ['L', 'R']) {
      this.def.push({ ...seg(`upperleg01.${s}`, `lowerleg01.${s}`, 'thigh'), kind: 'capsule' });
      this.def.push({ ...seg(`lowerleg01.${s}`, `foot.${s}`, 'shin'), kind: 'capsule' });
      this.def.push({ a: R.get(`glute.${s}`), b: R.get(`glute.${s}`), key: 'glute', kind: 'sphere' });
      this.def.push({ a: R.get(`upperleg01.${s}`), b: R.get(`upperleg01.${s}`), key: 'hip', kind: 'sphere' });
    }
    this.def.push({ a: R.get('belly'), b: R.get('belly'), key: 'belly', kind: 'sphere' });
    for (const d of this.def) this.list.push({ a: new THREE.Vector3(), b: new THREE.Vector3(), rA: 0.05, rB: 0.05 });
    this.fit();
    body.onChange(() => this.fit());
  }

  /** Raios a partir das medidas do corpo atual. */
  fit() {
    const P = this.body.morph.positions;
    const rl = this.body.pkg.meta.rulers;
    const rad = (name) => perimeter(P, rl[name]) / (2 * Math.PI);
    const r = { thigh: rad('thigh'), knee: rad('knee'), calf: rad('calf'), ankle: rad('ankle'), hips: rad('hips'), waist: rad('waist') };
    this.radii = r;
    this.def.forEach((d, i) => {
      const c = this.list[i];
      if (d.key === 'thigh') {
        c.rA = r.thigh * 1.22;
        c.rB = r.knee * 1.02;
      } else if (d.key === 'shin') {
        c.rA = r.knee * 1.0;
        c.rB = r.ankle * 1.3;
      } else if (d.key === 'glute') c.rA = c.rB = r.hips * 0.50;
      else if (d.key === 'hip') c.rA = c.rB = r.thigh * 1.05;
      else c.rA = c.rB = r.waist * 0.62;
    });
  }

  /** Atualiza extremos a partir da pose atual (espaço do grupo do avatar). */
  update() {
    const group = this.body.group;
    const tmp = new THREE.Vector3();
    this.def.forEach((d, i) => {
      const c = this.list[i];
      tmp.setFromMatrixPosition(this.rig.bones[d.a].matrixWorld);
      group.worldToLocal(tmp);
      c.a.copy(tmp);
      if (d.a === d.b) c.b.copy(tmp);
      else {
        tmp.setFromMatrixPosition(this.rig.bones[d.b].matrixWorld);
        group.worldToLocal(tmp);
        c.b.copy(tmp);
      }
    });
    return this.list;
  }
}
