// Drape (ver GLOSSARY.md): tecido que pende livre sob física (PBD — Position Based Dynamics).
//  - grade rows × cols (cols pode fechar em anel: saia) com restrições de distância (estrutura, cisalhamento,
//    flexão), integração de Verlet, vento e colisão contra cápsulas do corpo;
//  - "shape matching": cada partícula é puxada para a posição que teria se o tecido fosse rígido junto do
//    osso de fixação (mais rígido perto da cintura, mais livre na barra) — o tecido balança e volta ao corte;
//  - malha de render suavizada (Catmull-Rom bicúbico) a partir da grade de simulação.
import * as THREE from 'three';

const clamp = (x, a, b) => Math.min(b, Math.max(a, x));

export class Cloth {
  /**
   * opts: { rows, cols, wrap, rest (Float32Array rows*cols*3, espaço do grupo), attach (índice do osso),
   *         pinRows (n de linhas fixas no topo), shape: [kTopo, kBarra], gravity, damping, subU, subV,
   *         hemLength (m), uv: (r,c)=>[u,v] }
   */
  constructor(body, opts) {
    this.body = body;
    this.rig = body.rig;
    this.rows = opts.rows;
    this.cols = opts.cols;
    this.wrap = !!opts.wrap;
    this.attach = opts.attach;
    this.n = this.rows * this.cols;
    this.rest = Float32Array.from(opts.rest);
    this.x = Float32Array.from(opts.rest);
    this.p = Float32Array.from(opts.rest);
    this.goal = new Float32Array(this.n * 3);
    this.local = new Float32Array(this.n * 3); // posição de repouso relativa à cabeça do osso de fixação
    this.w = new Float32Array(this.n).fill(1);
    this.k = new Float32Array(this.n);
    this.pinRows = opts.pinRows ?? 1;
    this.gravity = opts.gravity ?? 9.8;
    this.damping = opts.damping ?? 0.985;
    this.wind = 0;
    this.stiffness = 1; // multiplicador do shape matching
    this.iterations = opts.iterations ?? 5;
    const [kTop, kHem] = opts.shape ?? [0.55, 0.03];
    for (let r = 0; r < this.rows; r++) {
      const t = r / Math.max(1, this.rows - 1);
      for (let c = 0; c < this.cols; c++) {
        const i = r * this.cols + c;
        if (r < this.pinRows) this.w[i] = 0;
        this.k[i] = kTop + (kHem - kTop) * Math.pow(t, 0.65);
      }
    }
    this._m = new THREE.Matrix4();
    this._inv = new THREE.Matrix4();
    this._v = new THREE.Vector3();
    this.time = 0;
    this._buildConstraints();
    this._buildRender(opts);
    this.resetToRest();
  }

  _idx(r, c) {
    if (this.wrap) c = ((c % this.cols) + this.cols) % this.cols;
    else c = clamp(c, 0, this.cols - 1);
    return clamp(r, 0, this.rows - 1) * this.cols + c;
  }

  _buildConstraints() {
    const ci = [];
    const cj = [];
    const st = [];
    const add = (a, b, s) => {
      if (a === b) return;
      ci.push(a);
      cj.push(b);
      st.push(s);
    };
    const maxC = this.wrap ? this.cols : this.cols - 1;
    for (let r = 0; r < this.rows; r++) {
      for (let c = 0; c < maxC; c++) {
        add(this._idx(r, c), this._idx(r, c + 1), 1.0); // horizontal
        if (r < this.rows - 1) {
          add(this._idx(r, c), this._idx(r + 1, c), 1.0); // vertical
          add(this._idx(r, c), this._idx(r + 1, c + 1), 0.55); // cisalhamento
          add(this._idx(r, c + 1), this._idx(r + 1, c), 0.55);
        }
        if (c < maxC - 1 || this.wrap) add(this._idx(r, c), this._idx(r, c + 2), 0.12); // flexão horizontal
      }
      if (r < this.rows - 2) for (let c = 0; c < this.cols; c++) add(this._idx(r, c), this._idx(r + 2, c), 0.12);
    }
    this.ci = Int32Array.from(ci);
    this.cj = Int32Array.from(cj);
    this.cs = Float32Array.from(st);
    this.cl = new Float32Array(ci.length);
    for (let q = 0; q < ci.length; q++) {
      const a = ci[q] * 3;
      const b = cj[q] * 3;
      this.cl[q] = Math.hypot(this.rest[a] - this.rest[b], this.rest[a + 1] - this.rest[b + 1], this.rest[a + 2] - this.rest[b + 2]);
    }
  }

  /** Malha de render: grade fina interpolada (Catmull-Rom) com atributos para o FabricMaterial. */
  _buildRender(opts) {
    const subU = opts.subU ?? 3;
    const subV = opts.subV ?? 3;
    const maxC = this.wrap ? this.cols : this.cols - 1;
    this.fu = maxC * subU + 1; // no anel, a última coluna repete a primeira (costura do padrão fica na emenda)
    this.seamOffset = opts.seamOffset || 0; // coluna de simulação em que a malha de render começa
    this.fv = (this.rows - 1) * subV + 1;
    this.subU = subU;
    this.subV = subV;
    const M = this.fu * this.fv;
    this.pos = new Float32Array(M * 3);
    this.nrm = new Float32Array(M * 3);
    const uv = new Float32Array(M * 2);
    const edge = new Float32Array(M);
    const aRest = new Float32Array(M * 3);
    const ind = [];
    const hem = opts.hemLength ?? 0.4;
    // coordenadas de padrão em metros: u = arco, v = distância ao longo da peça
    for (let j = 0; j < this.fv; j++) {
      for (let i = 0; i < this.fu; i++) {
        const k = j * this.fu + i;
        const fc = i / subU;
        const fr = j / subV;
        const r0 = Math.min(this.rows - 1, Math.floor(fr));
        const c0 = Math.floor(fc) % this.cols;
        const u = opts.uv ? opts.uv(fr, fc) : [fc * 0.03, fr * 0.03];
        uv[k * 2] = u[0];
        uv[k * 2 + 1] = u[1];
        edge[k] = Math.max(0, hem * (1 - fr / (this.rows - 1)) * 0 + (this.rows - 1 - fr) * (hem / (this.rows - 1)));
        void r0;
        void c0;
      }
    }
    const lastI = this.fu - 1;
    for (let j = 0; j < this.fv - 1; j++) {
      for (let i = 0; i < lastI; i++) {
        const a = j * this.fu + i;
        const b = j * this.fu + i + 1;
        const c = (j + 1) * this.fu + i + 1;
        const d = (j + 1) * this.fu + i;
        // enrolamento: a normal aponta para fora da saia (anel visto de cima, sentido horário)
        ind.push(a, d, c, a, c, b);
      }
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(this.pos, 3).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute('normal', new THREE.BufferAttribute(this.nrm, 3).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
    g.setAttribute('aUv', new THREE.BufferAttribute(uv, 2));
    g.setAttribute('aEdge', new THREE.BufferAttribute(edge, 1));
    g.setAttribute('aRest', new THREE.BufferAttribute(aRest, 3).setUsage(THREE.DynamicDrawUsage));
    g.setIndex(new THREE.BufferAttribute(Uint32Array.from(ind), 1));
    this.geometry = g;
    this.indices = Uint32Array.from(ind);
  }

  /** Posição inicial: formato de repouso colado ao osso de fixação (na pose atual). */
  resetToRest() {
    const head = this.rig.headWorld[this.attach];
    for (let i = 0; i < this.n; i++) {
      this.local[i * 3] = this.rest[i * 3] - head.x;
      this.local[i * 3 + 1] = this.rest[i * 3 + 1] - head.y;
      this.local[i * 3 + 2] = this.rest[i * 3 + 2] - head.z;
    }
    this.updateGoals();
    this.x.set(this.goal);
    this.p.set(this.goal);
    this.updateRender();
  }

  /** Novo formato de repouso (o corpo mudou): recalcula comprimentos e recomeça. */
  setRest(rest) {
    this.rest.set(rest);
    this._buildConstraints();
    this.resetToRest();
  }

  /**
   * Novo formato de repouso SEM reiniciar a simulação (o corpo está mudando): as partículas continuam onde
   * estão e seguem o novo alvo; a colisão as mantém fora do corpo. Evita "saltos" durante o repique.
   */
  retarget(rest) {
    this.rest.set(rest);
    this._buildConstraints();
    const head = this.rig.headWorld[this.attach];
    for (let i = 0; i < this.n; i++) {
      this.local[i * 3] = this.rest[i * 3] - head.x;
      this.local[i * 3 + 1] = this.rest[i * 3 + 1] - head.y;
      this.local[i * 3 + 2] = this.rest[i * 3 + 2] - head.z;
    }
    this.updateGoals();
  }

  updateGoals() {
    const bone = this.rig.bones[this.attach];
    const group = this.body.group;
    this._inv.copy(group.matrixWorld).invert();
    this._m.multiplyMatrices(this._inv, bone.matrixWorld);
    const e = this._m.elements;
    const L = this.local;
    const G = this.goal;
    for (let i = 0; i < this.n; i++) {
      const x = L[i * 3], y = L[i * 3 + 1], z = L[i * 3 + 2];
      G[i * 3] = e[0] * x + e[4] * y + e[8] * z + e[12];
      G[i * 3 + 1] = e[1] * x + e[5] * y + e[9] * z + e[13];
      G[i * 3 + 2] = e[2] * x + e[6] * y + e[10] * z + e[14];
    }
  }

  step(dt, colliders, wind = 0) {
    if (dt <= 0) return;
    this.time += dt;
    this.updateGoals();
    const h0 = 1 / 120;
    const steps = Math.min(4, Math.max(1, Math.ceil(dt / h0)));
    const h = dt / steps;
    const { x, p, goal, w, k, n } = this;
    const g = this.gravity * h * h;
    const damp = Math.pow(this.damping, h * 60);
    const wd = wind * h * h;
    const sk = this.stiffness;
    for (let s = 0; s < steps; s++) {
      for (let i = 0; i < n; i++) {
        const o = i * 3;
        if (w[i] === 0) {
          x[o] = goal[o]; x[o + 1] = goal[o + 1]; x[o + 2] = goal[o + 2];
          p[o] = x[o]; p[o + 1] = x[o + 1]; p[o + 2] = x[o + 2];
          continue;
        }
        const vx = (x[o] - p[o]) * damp;
        const vy = (x[o + 1] - p[o + 1]) * damp;
        const vz = (x[o + 2] - p[o + 2]) * damp;
        p[o] = x[o]; p[o + 1] = x[o + 1]; p[o + 2] = x[o + 2];
        // vento com variação espacial/temporal leve
        const gust = wd * (0.6 + 0.4 * Math.sin(this.time * 1.7 + i * 0.37));
        const kk = 1 - Math.exp(-k[i] * sk * h * 60);
        x[o] += vx + (goal[o] - x[o]) * kk;
        x[o + 1] += vy - g + (goal[o + 1] - x[o + 1]) * kk;
        x[o + 2] += vz + gust + (goal[o + 2] - x[o + 2]) * kk;
      }
      const { ci, cj, cs, cl } = this;
      for (let it = 0; it < this.iterations; it++) {
        for (let q = 0; q < ci.length; q++) {
          const a = ci[q] * 3;
          const b = cj[q] * 3;
          const dx = x[b] - x[a], dy = x[b + 1] - x[a + 1], dz = x[b + 2] - x[a + 2];
          const d = Math.hypot(dx, dy, dz) || 1e-9;
          const wa = w[ci[q]], wb = w[cj[q]];
          const ws = wa + wb;
          if (ws === 0) continue;
          const corr = ((d - cl[q]) / d) * cs[q] / ws;
          x[a] += dx * corr * wa; x[a + 1] += dy * corr * wa; x[a + 2] += dz * corr * wa;
          x[b] -= dx * corr * wb; x[b + 1] -= dy * corr * wb; x[b + 2] -= dz * corr * wb;
        }
        this.collide(colliders);
      }
      for (let i = 0; i < n; i++) {
        if (w[i] === 0) {
          const o = i * 3;
          x[o] = goal[o]; x[o + 1] = goal[o + 1]; x[o + 2] = goal[o + 2];
        }
      }
    }
    this.updateRender();
  }

  /** Empurra partículas para fora de esferas/cápsulas (a, b, raio). */
  collide(colliders) {
    if (!colliders) return;
    const x = this.x;
    const w = this.w;
    for (const c of colliders) {
      const ax = c.a.x, ay = c.a.y, az = c.a.z;
      const bx = c.b.x - ax, by = c.b.y - ay, bz = c.b.z - az;
      const l2 = bx * bx + by * by + bz * bz;
      const rA = c.rA ?? c.r;
      const rB = c.rB ?? c.r;
      for (let i = 0; i < this.n; i++) {
        if (w[i] === 0) continue;
        const o = i * 3;
        let t = 0;
        if (l2 > 1e-10) t = clamp(((x[o] - ax) * bx + (x[o + 1] - ay) * by + (x[o + 2] - az) * bz) / l2, 0, 1);
        const r = rA + (rB - rA) * t + 0.004;
        const cx = ax + bx * t, cy = ay + by * t, cz = az + bz * t;
        const dx = x[o] - cx, dy = x[o + 1] - cy, dz = x[o + 2] - cz;
        const d2 = dx * dx + dy * dy + dz * dz;
        if (d2 < r * r) {
          const d = Math.sqrt(d2) || 1e-9;
          const s = (r - d) / d;
          x[o] += dx * s; x[o + 1] += dy * s; x[o + 2] += dz * s;
        }
      }
    }
  }

  /** Interpola a grade de simulação (Catmull-Rom) para a malha fina e recalcula normais. */
  updateRender() {
    const { fu, fv, subU, subV, x } = this;
    const P = this.pos;
    const cr = (t) => {
      const t2 = t * t, t3 = t2 * t;
      return [(-t3 + 2 * t2 - t) * 0.5, (3 * t3 - 5 * t2 + 2) * 0.5, (-3 * t3 + 4 * t2 + t) * 0.5, (t3 - t2) * 0.5];
    };
    const wu = [];
    for (let s = 0; s < subU; s++) wu.push(cr(s / subU));
    const wv = [];
    for (let s = 0; s < subV; s++) wv.push(cr(s / subV));
    const wu1 = cr(1);
    for (let j = 0; j < fv; j++) {
      const r0 = Math.min(this.rows - 2, Math.floor(j / subV));
      const sv = j - r0 * subV;
      const bv = sv === subV ? wv[0] : wv[sv];
      const rr = sv === subV ? r0 + 1 : r0;
      for (let i = 0; i < fu; i++) {
        const c0 = Math.floor(i / subU);
        const su = i - c0 * subU;
        const bu = wu[su] ?? wu1;
        let px = 0, py = 0, pz = 0;
        for (let a = 0; a < 4; a++) {
          const wr = bv[a];
          if (wr === 0) continue;
          const row = rr + a - 1;
          for (let b = 0; b < 4; b++) {
            const wc = bu[b];
            const q = this._idx(row, c0 + b - 1 + this.seamOffset) * 3;
            const ww = wr * wc;
            px += x[q] * ww; py += x[q + 1] * ww; pz += x[q + 2] * ww;
          }
        }
        const k = (j * fu + i) * 3;
        P[k] = px; P[k + 1] = py; P[k + 2] = pz;
      }
    }
    // normais
    const N = this.nrm;
    N.fill(0);
    const I = this.indices;
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
    // aRest acompanha a posição (texturas procedurais seguem o tecido)
    this.geometry.attributes.aRest.array.set(P);
    this.geometry.attributes.position.needsUpdate = true;
    this.geometry.attributes.normal.needsUpdate = true;
    this.geometry.attributes.aRest.needsUpdate = true;
  }
}
