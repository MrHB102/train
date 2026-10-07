// Jiggle (ver GLOSSARY.md): movimento secundário do Soft Tissue por molas amortecidas nas juntas virtuais.
// Cada junta (busto, glúteos, coxas, barriga) é uma partícula presa ao seu osso-pai por uma mola 3D:
//     d'' = -ω² d - 2ζω d' - ganho · a_âncora
// onde a_âncora é a aceleração da âncora (junta de repouso levada pela pose). O deslocamento d, no espaço
// do avatar, vira o `offset` da junta no referencial do pai; o skinning faz o resto (ADR 0004), e as
// roupas (Shells) acompanham a carne sem nenhum custo extra.
import * as THREE from 'three';

/** Parâmetros base por Region (Softness = ganho; Firmness = rigidez/amortecimento). */
const BASE = {
  bust: { freq: 3.3, zeta: 0.17, gain: 2.1, axis: [1.0, 1.45, 1.0], max: 0.055 },
  glutes: { freq: 2.7, zeta: 0.22, gain: 1.7, axis: [0.9, 1.25, 1.0], max: 0.05 },
  thighs: { freq: 3.0, zeta: 0.26, gain: 1.35, axis: [1.0, 1.0, 1.0], max: 0.035 },
  belly: { freq: 2.5, zeta: 0.27, gain: 1.3, axis: [0.9, 1.15, 1.0], max: 0.035 },
};

const JOINT_REGION = { 'breast.L': 'bust', 'breast.R': 'bust', 'glute.L': 'glutes', 'glute.R': 'glutes', 'thigh.L': 'thighs', 'thigh.R': 'thighs', belly: 'belly' };

export function defaultDynamics() {
  return { enabled: true, bust: 1, glutes: 1, thighs: 1, belly: 1, damping: 1, stiffnessScale: 1 };
}

export class Jiggle {
  constructor(body) {
    this.body = body;
    this.rig = body.rig;
    this.dyn = defaultDynamics();
    this.items = [];
    for (const [name, region] of Object.entries(JOINT_REGION)) {
      const i = this.rig.index.get(name);
      if (i === undefined) continue;
      this.items.push({
        i,
        name,
        region,
        parent: this.rig.parent[i],
        d: new THREE.Vector3(),
        v: new THREE.Vector3(),
        a1: new THREE.Vector3(),
        v1: new THREE.Vector3(),
        af: new THREE.Vector3(),
        have: 0,
      });
    }
    this._tmp = { a: new THREE.Vector3(), q: new THREE.Quaternion(), qi: new THREE.Quaternion(), m: new THREE.Matrix4() };
    body.onChange(() => this.resync());
  }

  setDynamics(patch) {
    Object.assign(this.dyn, patch);
  }

  /** Evita "chutes" fantasmas quando o corpo muda de forma (a âncora salta de uma vez). */
  resync() {
    for (const it of this.items) it.have = 0;
  }

  kick(vec) {
    for (const it of this.items) it.v.add(vec);
  }

  /** Quanto o Soft Tissue "pesa": cresce com o tamanho (Traits) e reduz a frequência. */
  bigness(region, vals) {
    if (region === 'bust') return Math.max(0, (vals['bust.size'] - 0.3) / 0.7) + Math.max(0, vals['bust.extraVolume']) * 0.65;
    if (region === 'glutes') return Math.max(0, vals['glutes.volume']) * 0.7 + Math.max(0, vals['glutes.extraVolume']) * 0.65;
    if (region === 'thighs') return Math.max(0, vals['thighs.fullness']) * 0.6 + Math.max(0, vals['thighs.extraVolume']) * 0.6 + Math.max(0, vals['thighs.upperVolume']) * 0.4;
    return Math.max(0, vals['belly.volume']) * 0.9;
  }

  update(dt) {
    const dyn = this.dyn;
    const rig = this.rig;
    const group = this.body.group;
    if (!dyn.enabled || dt <= 0) {
      for (const it of this.items) {
        it.d.set(0, 0, 0);
        it.v.set(0, 0, 0);
        rig.offset[it.i].set(0, 0, 0);
      }
      rig.applyOffsets();
      return;
    }
    const vals = this.body.effective();
    const { a, q, qi } = this._tmp;
    const h = 1 / 240;
    const steps = Math.min(8, Math.max(1, Math.ceil(dt / h)));
    const hh = dt / steps;
    for (const it of this.items) {
      const base = BASE[it.region];
      const strength = dyn[it.region] ?? 1;
      const big = this.bigness(it.region, vals);
      const firm = it.region === 'bust' ? 0.55 + 0.9 * (vals['bust.firmness'] ?? 0.5) : 1;
      // mais volume = mais massa = frequência menor e mais deslocamento; mais firmeza = mola mais dura
      const freq = (base.freq / Math.sqrt(1 + 0.55 * big)) * Math.sqrt(firm) * Math.sqrt(dyn.stiffnessScale);
      const w = freq * Math.PI * 2;
      const zeta = base.zeta * dyn.damping * (it.region === 'bust' ? 0.85 + 0.3 * (vals['bust.firmness'] ?? 0.5) : 1);
      const gain = base.gain * strength * (1 + 0.35 * big);

      // âncora: posição de repouso da junta levada pelo osso-pai (sem o próprio deslocamento)
      const parent = rig.bones[it.parent];
      a.copy(rig.restLocal[it.i]).applyMatrix4(parent.matrixWorld);
      group.worldToLocal(a);
      if (!it.have) {
        it.a1.copy(a);
        it.v1.set(0, 0, 0);
        it.af.set(0, 0, 0);
        it.have = 1;
      } else {
        const vel = a.clone().sub(it.a1).divideScalar(dt);
        const acc = vel.clone().sub(it.v1).divideScalar(dt);
        // acelerações absurdas (teleporte, troca de pose) são limitadas
        const l = acc.length();
        if (l > 90) acc.multiplyScalar(90 / l);
        it.af.lerp(acc, Math.min(1, dt * 40));
        it.a1.copy(a);
        it.v1.copy(vel);
      }
      for (let s = 0; s < steps; s++) {
        const ax = it.af.x * base.axis[0] * gain;
        const ay = it.af.y * base.axis[1] * gain;
        const az = it.af.z * base.axis[2] * gain;
        it.v.x += (-w * w * it.d.x - 2 * zeta * w * it.v.x - ax) * hh;
        it.v.y += (-w * w * it.d.y - 2 * zeta * w * it.v.y - ay) * hh;
        it.v.z += (-w * w * it.d.z - 2 * zeta * w * it.v.z - az) * hh;
        it.d.addScaledVector(it.v, hh);
      }
      // limite suave do deslocamento (tanh): o tecido tem curso máximo
      const maxD = base.max * (1 + 0.25 * big);
      const len = it.d.length();
      if (len > 1e-6) {
        const soft = maxD * Math.tanh(len / maxD);
        if (soft < len) {
          it.d.multiplyScalar(soft / len);
          it.v.multiplyScalar(0.9);
        }
      }
      // do espaço do avatar para o referencial do osso-pai
      parent.getWorldQuaternion(q);
      group.getWorldQuaternion(qi).invert();
      q.premultiply(qi).invert();
      rig.offset[it.i].copy(it.d).applyQuaternion(q);
    }
    rig.applyOffsets();
  }
}
