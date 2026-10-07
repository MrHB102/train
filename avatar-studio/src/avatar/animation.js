// Animação procedural do Rig (sem arquivos de clipe): Poses estáticas e Motions em loop.
// Convenções: y para cima, frente +Z, esquerda do corpo +X; rotações em eixos globais (o Rig não tem
// rotação de repouso). Quadril/coluna por rotações; pernas por IK de dois ossos com os pés plantados
// (Ground Contact); salto alto (Heel Height) pelo mesmo mecanismo de rolamento do pé sobre a bola.
import * as THREE from 'three';

const DEG = Math.PI / 180;
const V = (x = 0, y = 0, z = 0) => new THREE.Vector3(x, y, z);
const E = (x, y, z) => new THREE.Quaternion().setFromEuler(new THREE.Euler(x, y, z, 'YXZ'));
const smooth = (t) => t * t * (3 - 2 * t);
const lerp = (a, b, t) => a + (b - a) * t;
const TAU = Math.PI * 2;

/** Poses: ajustes estáticos. Ângulos em graus, distâncias em metros. */
export const POSES = {
  // stance = deslocamento lateral dos tornozelos em relação à pose de repouso (A-pose, tornozelos a ±0.163 m)
  stand: { pt: 'Em pé (pés e coxas juntos)', en: 'Standing (feet and thighs together)', stance: -0.116 },
  relaxed: { pt: 'Em pé (relaxada)', en: 'Standing (relaxed)', stance: -0.063 },
  apart: { pt: 'Em pé (afastada)', en: 'Standing (apart)', stance: 0.0 },
  contrapposto: { pt: 'Contrapeso', en: 'Contrapposto', hipRoll: 5, hipShift: -0.022, spineRoll: -4, spineTwist: 4, feet: [[0, 0.0], [0, 0.07]], stance: -0.02 },
  hip: { pt: 'Quadril de lado', en: 'Hip pop', hipRoll: 9, hipShift: -0.04, spineRoll: -8, spineTwist: 8, feet: [[0, 0.0], [0, 0.1]], stance: 0.0 },
  runway: { pt: 'Passarela (pé cruzado)', en: 'Runway stance', hipRoll: 4, hipShift: -0.02, spineRoll: -3, spineTwist: -6, feet: [[0.07, 0.12], [-0.01, -0.02]], stance: -0.05 },
  wide: { pt: 'Pernas afastadas', en: 'Wide stance', stance: 0.09 },
  squat: { pt: 'Agachada', en: 'Squat', stance: 0.06, squat: 0.3, spineBend: 12, pelvisPitch: 6 },
  lean: { pt: 'Inclinada para trás', en: 'Lean back', spineBend: -9, pelvisPitch: -5, feet: [[0, 0.06], [0, -0.03]] },
};

/** Motions: ciclos procedurais. */
export const MOTIONS = {
  none: { pt: 'Parada', en: 'Still' },
  idle: { pt: 'Respirar', en: 'Idle breathing' },
  walk: { pt: 'Caminhar', en: 'Walk' },
  strut: { pt: 'Desfile (passarela)', en: 'Runway strut' },
  dance: { pt: 'Dançar (quadril)', en: 'Hip dance' },
  bounce: { pt: 'Saltitar', en: 'Bounce' },
  twirl: { pt: 'Girar', en: 'Twirl' },
};

export class Animator {
  constructor(body) {
    this.body = body;
    this.rig = body.rig;
    this.pose = 'stand';
    this.motion = 'idle';
    this.speed = 1;
    this.time = 0;
    this.heelMeters = 0; // Heel Height
    this.twirl = 0; // ângulo acumulado (rad) aplicado à plataforma
    this.airborne = 0;
    this.idx = {};
    for (const n of this.rig.names) this.idx[n] = this.rig.index.get(n);
    this._q = [new THREE.Quaternion(), new THREE.Quaternion(), new THREE.Quaternion(), new THREE.Quaternion()];
    this.enabled = true;
  }

  setPose(id) {
    if (POSES[id]) this.pose = id;
  }
  setMotion(id) {
    if (MOTIONS[id]) this.motion = id;
  }
  bone(name) {
    return this.rig.bones[this.idx[name]];
  }

  /** Medidas do pé no corpo atual: altura do tornozelo, distância até a bola e comprimento. */
  footMetrics(s) {
    const r = this.rig;
    const ankle = r.headWorld[this.idx[`foot.${s}`]];
    const toe = r.headWorld[this.idx[`toe1-1.${s}`]];
    const ankleH = Math.max(0.05, ankle.y - this.body.floorY);
    const ball = Math.max(0.08, toe.z - ankle.z);
    return { ankleH, ball, heel: 0.055, len: ball + 0.055 };
  }

  /** Deslocamento do tornozelo ao girar o pé `pitch` (rad; + = ponta para baixo) em torno da bola/calcanhar. */
  roll(pitch, m) {
    if (pitch >= 0) {
      // gira em torno da bola do pé (calcanhar sobe)
      const y = m.ankleH * Math.cos(pitch) + m.ball * Math.sin(pitch);
      const z = m.ankleH * Math.sin(pitch) - m.ball * Math.cos(pitch);
      return { dy: y - m.ankleH, dz: z + m.ball };
    }
    // gira em torno do calcanhar (ponta sobe)
    const y = m.ankleH * Math.cos(pitch) - m.heel * Math.sin(pitch);
    const z = m.ankleH * Math.sin(pitch) + m.heel * Math.cos(pitch);
    return { dy: y - m.ankleH, dz: z - m.heel };
  }

  solve(t, dt) {
    const pose = POSES[this.pose] || POSES.stand;
    const o = {
      rootPos: V(pose.hipShift || 0, 0, 0),
      pitch: (pose.pelvisPitch || 0) * DEG,
      yaw: 0,
      roll: (pose.hipRoll || 0) * DEG,
      spineTwist: (pose.spineTwist || 0) * DEG,
      spineBend: (pose.spineBend || 0) * DEG,
      spineRoll: (pose.spineRoll || 0) * DEG,
      stance: pose.stance || 0,
      squat: pose.squat || 0,
      feet: [{ x: 0, z: 0, lift: 0, pitch: 0 }, { x: 0, z: 0, lift: 0, pitch: 0 }],
    };
    if (pose.feet) pose.feet.forEach((f, i) => ((o.feet[i].x = f[0]), (o.feet[i].z = f[1])));
    this.airborne = 0;
    const m = this.motion;
    if (m === 'idle') {
      const br = Math.sin(t * TAU * 0.24);
      o.spineBend += br * 1.2 * DEG;
      o.rootPos.y += br * 0.0012;
      o.roll += Math.sin(t * TAU * 0.11) * 0.8 * DEG;
      o.rootPos.x += Math.sin(t * TAU * 0.11) * 0.004;
      o.spineTwist += Math.sin(t * TAU * 0.07 + 1) * 1.2 * DEG;
    } else if (m === 'dance') {
      const f = 0.8;
      const a = Math.sin(t * TAU * f);
      const b = Math.sin(t * TAU * f + Math.PI / 2);
      o.rootPos.x += a * 0.05;
      o.roll += a * 9 * DEG;
      o.yaw += b * 14 * DEG;
      o.rootPos.y += -Math.abs(a) * 0.028 + 0.01;
      o.rootPos.z += b * 0.014;
      o.spineTwist += -b * 11 * DEG;
      o.spineRoll += -a * 4 * DEG;
      o.stance += 0.05;
      o.squat += 0.035 + 0.025 * Math.sin(t * TAU * f * 2);
    } else if (m === 'bounce') {
      const f = 1.45;
      const ph = (t * f) % 1;
      let y = 0;
      let lift = 0;
      if (ph < 0.2) y = -Math.sin((ph / 0.2) * Math.PI * 0.5) * 0.05; // agacha
      else if (ph < 0.7) {
        const u = (ph - 0.2) / 0.5;
        y = -0.05 + Math.sin(u * Math.PI) * 0.21;
        lift = Math.max(0, y + 0.05) * 0.95;
      } else y = -Math.sin(((1 - ph) / 0.3) * Math.PI * 0.5) * 0.05; // amortece
      o.rootPos.y += y;
      o.feet[0].lift = lift;
      o.feet[1].lift = lift * 0.9;
      o.spineBend += (ph < 0.2 ? 5 : ph < 0.7 ? -1 : 4) * DEG;
      o.stance += 0.03;
      this.airborne = lift;
    } else if (m === 'twirl') {
      this.twirl += dt * this.speed * 2.4;
      o.roll += Math.sin(t * 2) * 1.5 * DEG;
    } else if (m === 'walk' || m === 'strut') {
      const g = m === 'strut' ? { f: 0.92, stride: 0.34, lift: 0.075, sway: 0.03, yaw: 11, roll: 5.5, cross: 0.06, bob: 0.011, st: 0.0 } : { f: 1.0, stride: 0.26, lift: 0.055, sway: 0.016, yaw: 6, roll: 3, cross: 0, bob: 0.014, st: 0.012 };
      const ph = (t * g.f) % 1;
      for (let s = 0; s < 2; s++) {
        const p = (ph + s * 0.5) % 1;
        const f = o.feet[s];
        if (p < 0.6) {
          const u = p / 0.6; // apoio: o pé desliza para trás no chão
          f.z += g.stride * (0.5 - u);
          f.pitch = lerp(-9, 24, smooth(Math.max(0, (u - 0.45) / 0.55))) * DEG * (u < 0.4 ? lerp(-1, 0, smooth(u / 0.4)) : 1);
          if (u < 0.4) f.pitch = lerp(-9, 0, smooth(u / 0.4)) * DEG;
        } else {
          const u = (p - 0.6) / 0.4; // balanço: o pé volta para frente, no ar
          f.z += g.stride * (-0.5 + smooth(u));
          f.lift += Math.sin(u * Math.PI) * g.lift;
          f.pitch = lerp(24, -9, smooth(u)) * DEG;
        }
        f.x += (s === 0 ? -1 : 1) * g.cross * -1 + (s === 0 ? 1 : -1) * 0 + g.st * (s === 0 ? 1 : -1) * 0;
      }
      o.stance = (m === 'strut' ? -0.1 : -0.06) + g.st; // a marcha usa a própria largura de passo
      const a = Math.sin(ph * TAU);
      o.rootPos.x += -a * g.sway;
      o.roll += a * g.roll * DEG;
      o.yaw += -a * g.yaw * DEG;
      o.rootPos.y += -Math.abs(Math.cos(ph * TAU)) * g.bob;
      o.spineTwist += a * g.yaw * 0.9 * DEG;
      o.spineRoll += -a * 2 * DEG;
    }
    return o;
  }

  update(dt) {
    if (!this.enabled) return;
    this.time += dt * this.speed;
    const rig = this.rig;
    const o = this.solve(this.time, dt);
    rig.resetPose(); // zera rotações e deslocamentos que não são de Jiggle
    // quadril
    const ri = this.idx.root;
    rig.offset[ri].copy(o.rootPos);
    rig.offset[ri].y -= o.squat;
    rig.offset[ri].z -= o.squat * 0.2;
    this.bone('root').quaternion.copy(E(o.pitch, o.yaw, o.roll));
    // coluna: distribui flexão, torção e inclinação lateral
    for (const [name, k] of [['spine05', 0.2], ['spine04', 0.22], ['spine03', 0.22], ['spine02', 0.2], ['spine01', 0.16]]) {
      this.bone(name).quaternion.copy(E(o.spineBend * k, o.spineTwist * k, o.spineRoll * k));
    }
    rig.applyOffsets();
    this.body.group.updateMatrixWorld(true);
    this.legs(o);
  }

  legs(o) {
    const rig = this.rig;
    const group = this.body.group;
    const inv = new THREE.Quaternion();
    const toLocalQuat = (bone, out) => {
      bone.getWorldQuaternion(out);
      group.getWorldQuaternion(inv).invert();
      return out.premultiply(inv);
    };
    ['L', 'R'].forEach((s, si) => {
      const sx = s === 'L' ? 1 : -1;
      const hipBone = this.bone(`upperleg01.${s}`);
      const kneeBone = this.bone(`lowerleg01.${s}`);
      const footBone = this.bone(`foot.${s}`);
      const hipRest = rig.headWorld[this.idx[`upperleg01.${s}`]];
      const kneeRest = rig.headWorld[this.idx[`lowerleg01.${s}`]];
      const ankleRest = rig.headWorld[this.idx[`foot.${s}`]];
      const L1 = kneeRest.distanceTo(hipRest);
      const L2 = ankleRest.distanceTo(kneeRest);
      const fm = this.footMetrics(s);
      const f = o.feet[si];

      // pitch total: marcha/pose + salto alto (peso na ponta)
      const heelPitch = Math.min(1.0, Math.asin(Math.min(0.95, this.heelMeters / fm.len)));
      let pitch = f.pitch * (1 - Math.min(1, heelPitch * 1.6)) + heelPitch;
      if (f.lift > 0.01) pitch = Math.max(pitch, f.lift * 3); // no ar a ponta cai
      const r = this.roll(pitch, fm);

      const H = group.worldToLocal(new THREE.Vector3().setFromMatrixPosition(hipBone.matrixWorld));
      const target = new THREE.Vector3(ankleRest.x + sx * (o.stance + f.x * 0) + f.x * (s === 'L' ? 1 : 1), ankleRest.y + f.lift + r.dy, ankleRest.z + f.z + r.dz);
      const d = target.clone().sub(H);
      const dist = d.length();
      const clamped = Math.min((L1 + L2) * 0.9995, Math.max(Math.abs(L1 - L2) * 1.02 + 0.08, dist));
      const dir = d.clone().normalize();
      const a = (L1 * L1 - L2 * L2 + clamped * clamped) / (2 * clamped);
      const h = Math.sqrt(Math.max(L1 * L1 - a * a, 0));
      const pole = new THREE.Vector3(sx * 0.15, 0, 1).normalize();
      pole.addScaledVector(dir, -pole.dot(dir)).normalize();
      const K = H.clone().addScaledVector(dir, a).addScaledVector(pole, h);
      const A = H.clone().addScaledVector(dir, clamped);

      const u1 = kneeRest.clone().sub(hipRest).normalize();
      const Q1 = new THREE.Quaternion().setFromUnitVectors(u1, K.clone().sub(H).normalize());
      const parentQ = toLocalQuat(hipBone.parent, new THREE.Quaternion());
      hipBone.quaternion.copy(parentQ.invert().multiply(Q1));

      const u2 = ankleRest.clone().sub(kneeRest).normalize().applyQuaternion(Q1);
      const Q2 = new THREE.Quaternion().setFromUnitVectors(u2, A.clone().sub(K).normalize()).multiply(Q1);
      kneeBone.quaternion.copy(Q1.clone().invert().multiply(Q2));

      const toeOut = sx * 5 * DEG;
      const Qf = E(pitch, toeOut, 0);
      footBone.quaternion.copy(Q2.clone().invert().multiply(Qf));

      // dedos: com o salto alto ficam dobrados; na marcha dobram quando o calcanhar sobe
      const toe = Math.max(0, pitch - heelPitch) * 0.9 + (this.heelMeters > 0.01 ? 0 : 0);
      for (const n of rig.names) if (n.startsWith('toe') && n.endsWith('.' + s)) this.bone(n).quaternion.copy(E(-toe, 0, 0));
    });
    group.updateMatrixWorld(true); // pose final disponível para o Jiggle e para as roupas
  }
}
