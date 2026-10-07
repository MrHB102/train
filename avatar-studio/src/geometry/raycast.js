// Raycast contra a malha de referência do Body (estado neutro), com grade espacial em (x, y).
// Serve para traçar caminhos sobre a superfície (cordões, alças, costuras) e prendê-los ao corpo.
const CELL = 0.02;

export class SurfaceIndex {
  constructor(pos, indices) {
    this.pos = pos;
    this.indices = indices;
    this.cells = new Map();
    const T = indices.length / 3;
    for (let t = 0; t < T; t++) {
      let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9;
      for (let k = 0; k < 3; k++) {
        const v = indices[t * 3 + k] * 3;
        x0 = Math.min(x0, pos[v]); x1 = Math.max(x1, pos[v]);
        y0 = Math.min(y0, pos[v + 1]); y1 = Math.max(y1, pos[v + 1]);
      }
      for (let cx = Math.floor(x0 / CELL); cx <= Math.floor(x1 / CELL); cx++) {
        for (let cy = Math.floor(y0 / CELL); cy <= Math.floor(y1 / CELL); cy++) {
          const key = cx * 4096 + cy;
          let list = this.cells.get(key);
          if (!list) this.cells.set(key, (list = []));
          list.push(t);
        }
      }
    }
  }

  /** Triângulos candidatos ao longo da projeção do raio em (x, y) entre os parâmetros 0..tMax. */
  candidates(ox, oy, dx, dy, tMax) {
    const seen = new Set();
    const len = Math.hypot(dx, dy) * tMax;
    const steps = Math.max(1, Math.ceil(len / (CELL * 0.5)));
    for (let i = 0; i <= steps; i++) {
      const t = (i / steps) * tMax;
      const x = ox + dx * t;
      const y = oy + dy * t;
      const list = this.cells.get(Math.floor(x / CELL) * 4096 + Math.floor(y / CELL));
      if (list) for (const id of list) seen.add(id);
    }
    return seen;
  }

  /** Primeiro acerto do raio origem + t·dir (t em [0, tMax]) ou null. Devolve { t, tri, u, v, point }. */
  cast(origin, dir, tMax = 1.5) {
    const { pos, indices } = this;
    const [ox, oy, oz] = origin;
    const [dx, dy, dz] = dir;
    let best = null;
    for (const t of this.candidates(ox, oy, dx, dy, tMax)) {
      const a = indices[t * 3] * 3, b = indices[t * 3 + 1] * 3, c = indices[t * 3 + 2] * 3;
      const e1x = pos[b] - pos[a], e1y = pos[b + 1] - pos[a + 1], e1z = pos[b + 2] - pos[a + 2];
      const e2x = pos[c] - pos[a], e2y = pos[c + 1] - pos[a + 1], e2z = pos[c + 2] - pos[a + 2];
      const px = dy * e2z - dz * e2y, py = dz * e2x - dx * e2z, pz = dx * e2y - dy * e2x;
      const det = e1x * px + e1y * py + e1z * pz;
      if (Math.abs(det) < 1e-12) continue;
      const inv = 1 / det;
      const sx = ox - pos[a], sy = oy - pos[a + 1], sz = oz - pos[a + 2];
      const u = (sx * px + sy * py + sz * pz) * inv;
      if (u < -1e-6 || u > 1 + 1e-6) continue;
      const qx = sy * e1z - sz * e1y, qy = sz * e1x - sx * e1z, qz = sx * e1y - sy * e1x;
      const v = (dx * qx + dy * qy + dz * qz) * inv;
      if (v < -1e-6 || u + v > 1 + 1e-6) continue;
      const tt = (e2x * qx + e2y * qy + e2z * qz) * inv;
      if (tt < 0 || tt > tMax) continue;
      if (!best || tt < best.t) best = { t: tt, tri: t, u, v };
    }
    if (best) {
      const w0 = 1 - best.u - best.v;
      const a = indices[best.tri * 3], b = indices[best.tri * 3 + 1], c = indices[best.tri * 3 + 2];
      best.verts = [a, b, c];
      best.bary = [w0, best.u, best.v];
      best.point = [0, 1, 2].map((k) => pos[a * 3 + k] * w0 + pos[b * 3 + k] * best.u + pos[c * 3 + k] * best.v);
    }
    return best;
  }
}
