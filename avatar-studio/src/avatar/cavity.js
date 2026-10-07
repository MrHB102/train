// Cavidade por vértice: quanto o vértice está abaixo da média dos vizinhos (> 0 = côncavo, < 0 = convexo).
// Alimenta o shader da pele (sombra suave em dobras, vãos e cavidades, realce em cristas), sem custo de textura.
export class Cavity {
  constructor(indices, N) {
    this.N = N;
    const deg = new Uint16Array(N);
    for (let i = 0; i < indices.length; i++) deg[indices[i]] += 2;
    this.start = new Uint32Array(N + 1);
    for (let v = 0; v < N; v++) this.start[v + 1] = this.start[v] + deg[v];
    this.nb = new Uint32Array(this.start[N]);
    const fill = new Uint32Array(N);
    const add = (a, b) => {
      const o = this.start[a] + fill[a]++;
      this.nb[o] = b;
    };
    for (let t = 0; t < indices.length; t += 3) {
      const a = indices[t], b = indices[t + 1], c = indices[t + 2];
      add(a, b); add(a, c); add(b, a); add(b, c); add(c, a); add(c, b);
    }
    this.raw = new Float32Array(N);
  }

  /** out[v] em metros (positivo = côncavo). Duas passadas de suavização removem o ruído da malha. */
  update(pos, nrm, out) {
    const { N, start, nb, raw } = this;
    for (let v = 0; v < N; v++) {
      let sx = 0, sy = 0, sz = 0;
      const s = start[v], e = start[v + 1];
      for (let k = s; k < e; k++) {
        const q = nb[k] * 3;
        sx += pos[q]; sy += pos[q + 1]; sz += pos[q + 2];
      }
      const inv = 1 / (e - s || 1);
      const i = v * 3;
      raw[v] = (sx * inv - pos[i]) * nrm[i] + (sy * inv - pos[i + 1]) * nrm[i + 1] + (sz * inv - pos[i + 2]) * nrm[i + 2];
    }
    for (let v = 0; v < N; v++) {
      let a = raw[v] * 2;
      const s = start[v], e = start[v + 1];
      for (let k = s; k < e; k++) a += raw[nb[k]];
      out[v] = a / (e - s + 2);
    }
  }
}
