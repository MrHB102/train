// Elastic (recoil): o valor exibido de cada Trait/Dial segue o alvo por uma mola subamortecida. Ao arrastar um
// slider o corpo cresce passando do ponto e volta (overshoot), como num criador de personagem de jogo, e a
// variação de forma dá um impulso no Jiggle (a carne "atrasa" e balança). Tudo configurável em Dinâmica.
//
//   x'' = -ω² (x - alvo) - 2ζω x'          ω = 2π f
//
// Cada Region tem frequência e amortecimento próprios: o busto é leve e balança mais; coxas e quadril são
// mais pesados. `amount` (0..2.5) escala o repique: 0 = sem overshoot (criticamente amortecido).
import * as THREE from 'three';
import { TRAIT_BY_ID, TRAITS } from '../domain/traits.js';
import { DIAL_BY_ID, DIALS } from '../domain/dials.js';

const SPRING = {
  bust: { f: 3.3, z: 0.24 },
  glutes: { f: 2.8, z: 0.29 },
  thighs: { f: 2.5, z: 0.35 },
  hips: { f: 2.3, z: 0.38 },
  waist: { f: 2.5, z: 0.4 },
  belly: { f: 2.5, z: 0.38 },
  torso: { f: 2.6, z: 0.5 },
  shoulders: { f: 2.6, z: 0.5 },
  neck: { f: 2.6, z: 0.55 },
  knees: { f: 2.8, z: 0.55 },
  calves: { f: 2.8, z: 0.5 },
  ankles: { f: 2.8, z: 0.55 },
  feet: { f: 2.8, z: 0.55 },
  silhouette: { f: 2.4, z: 0.45 },
  general: { f: 2.0, z: 0.7 },
};
const DIAL_REGION = { curves: 'hips', bombshell: 'bust', thickness: 'thighs', anime: 'hips', tone: 'general', bustSize: 'bust' };

// impulso no Jiggle por unidade de variação normalizada (m/s): [y, z]
const KICK = { bust: [5.6, 1.8], glutes: [4.2, -1.0], thighs: [2.6, 0.4], belly: [3.2, 1.2] };
// quanto cada Region alimenta o impulso de cada massa de Jiggle
const KICK_REGION = {
  bust: { bust: 1 },
  glutes: { glutes: 1 },
  hips: { glutes: 0.5, thighs: 0.3 },
  thighs: { thighs: 1 },
  waist: { belly: 0.5 },
  belly: { belly: 1 },
  general: { belly: 0.25, glutes: 0.2, thighs: 0.2, bust: 0.25 },
};

export class Elastic {
  constructor(body, jiggle) {
    this.body = body;
    this.jiggle = jiggle;
    this.enabled = true;
    this.amount = 1;
    this.keys = new Map(); // 'trait:id' | 'dial:id' -> { kind, id, x, v, t, w, z, span, applied, instant }
    for (const t of TRAITS) this._add('trait', t.id, body.values[t.id] ?? t.neutral);
    for (const d of DIALS) this._add('dial', d.id, body.dials[d.id] ?? d.neutral);
    this.prev = { ...body.effective() };
    this.tmp = new THREE.Vector3();
  }

  _add(kind, id, value) {
    const def = kind === 'trait' ? TRAIT_BY_ID[id] : DIAL_BY_ID[id];
    const region = kind === 'trait' ? (def.region || (def.group === 'silhouette' ? 'silhouette' : 'general')) : DIAL_REGION[id] || 'general';
    const sp = SPRING[region] || SPRING.general;
    const instant = id.startsWith('ancestry.') || def.runtime;
    const span = def.extended[1] - def.extended[0];
    this.keys.set(`${kind}:${id}`, { kind, id, x: value, v: 0, t: value, f: sp.f, z: sp.z, span, applied: value, instant });
  }

  /** Define alvos (parcial). Com `snap`, o corpo vai direto ao valor, sem animação. */
  set({ traits, dials } = {}, { snap = false } = {}) {
    for (const [id, v] of Object.entries(traits || {})) this._target(`trait:${id}`, v, snap);
    for (const [id, v] of Object.entries(dials || {})) this._target(`dial:${id}`, v, snap);
    this._dirty = true;
  }

  _target(key, value, snap) {
    const k = this.keys.get(key);
    if (!k) return;
    k.t = value;
    if (snap || !this.enabled || k.instant) {
      k.x = value;
      k.v = 0;
    }
  }

  /** Valor alvo atual (o que a UI mostra, sem o overshoot). */
  target(kind, id) {
    return this.keys.get(`${kind}:${id}`)?.t;
  }

  /** Vai direto aos alvos. */
  snap() {
    for (const k of this.keys.values()) {
      k.x = k.t;
      k.v = 0;
    }
    this._dirty = true;
    this._apply();
  }

  get moving() {
    for (const k of this.keys.values()) if (Math.abs(k.x - k.t) > 1e-5 || Math.abs(k.v) > 1e-4) return true;
    return false;
  }

  update(dt) {
    if (dt <= 0) return;
    const amt = Math.max(0, this.amount);
    this.body.slack = this.enabled ? Math.min(0.5, 0.18 * amt) : 0;
    let changed = this._dirty;
    this._dirty = false;
    const steps = Math.min(8, Math.max(1, Math.ceil(dt * 240)));
    const hh = dt / steps;
    for (const k of this.keys.values()) {
      if (k.instant || !this.enabled) {
        if (k.x !== k.t) {
          k.x = k.t;
          k.v = 0;
        }
      } else if (Math.abs(k.x - k.t) > 1e-5 || Math.abs(k.v) > 1e-4) {
        const z = Math.min(1, Math.max(0.08, 1 - (1 - k.z) * amt));
        const w = Math.PI * 2 * k.f * (amt < 0.02 ? 2.2 : 1);
        for (let s = 0; s < steps; s++) {
          k.v += (-w * w * (k.x - k.t) - 2 * z * w * k.v) * hh;
          k.x += k.v * hh;
        }
        if (Math.abs(k.x - k.t) < 1e-5 && Math.abs(k.v) < 1e-4) {
          k.x = k.t;
          k.v = 0;
        }
      }
      if (k.x !== k.applied) changed = true;
    }
    if (changed) this._apply();
  }

  _apply() {
    const traits = {};
    const dials = {};
    for (const k of this.keys.values()) {
      if (k.x === k.applied) continue;
      (k.kind === 'trait' ? traits : dials)[k.id] = k.x;
      k.applied = k.x;
    }
    if (!Object.keys(traits).length && !Object.keys(dials).length) return;
    this.body.setState(traits, dials);
    this._kick();
  }

  /** Impulso no Jiggle pela variação dos valores efetivos (Traits + Dials) desde o último quadro. */
  _kick() {
    if (!this.jiggle || !this.enabled) {
      this.prev = { ...this.body.effective() };
      return;
    }
    const eff = this.body.effective();
    const acc = { bust: 0, glutes: 0, thighs: 0, belly: 0 };
    for (const t of TRAITS) {
      const d = eff[t.id] - (this.prev[t.id] ?? eff[t.id]);
      if (!d) continue;
      const map = KICK_REGION[t.region || (t.id === 'weight' || t.id === 'muscle' ? 'general' : '')];
      if (!map) continue;
      const span = t.extended[1] - t.extended[0];
      for (const [r, w] of Object.entries(map)) acc[r] += (d / span) * w;
    }
    this.prev = { ...eff };
    const g = Math.min(2.5, this.amount);
    for (const [r, a] of Object.entries(acc)) {
      if (Math.abs(a) < 1e-7) continue;
      const [ky, kz] = KICK[r];
      // crescer: a carne atrasa (desce e vai para a frente); encolher: o contrário
      this.jiggle.kickRegion(r, this.tmp.set(0, -a * ky * g, a * kz * g));
    }
  }
}
