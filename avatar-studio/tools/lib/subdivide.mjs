// Catmull–Clark (1 nível) sobre uma malha de quads, expressa como "stencils":
// cada vértice novo é uma combinação linear (esparsa) dos vértices originais. Como a subdivisão é
// linear, o runtime só precisa aplicar os stencils sobre as posições base já morfadas — todo morph
// target ganha, de graça, a suavização exata da superfície subdividida (pele lisa, silhueta sem facetas).
//
// Regras: ponto de face = média; ponto de aresta = (v1+v2+f1+f2)/4 (borda: (v1+v2)/2);
// ponto de vértice interno = (Q + 2R + (n-3)P)/n; vértice de borda = (b1 + 6P + b2)/8.
export function catmullClark(quads, nv) {
  const ekey = (a, b) => (a < b ? a * nv + b : b * nv + a);
  const edgeIndex = new Map();
  const edges = [];
  quads.forEach((q, fi) => {
    if (q.length !== 4) throw new Error('catmullClark: só quads');
    for (let i = 0; i < 4; i++) {
      const a = q[i];
      const b = q[(i + 1) % 4];
      const k = ekey(a, b);
      let e = edgeIndex.get(k);
      if (e === undefined) {
        e = edges.length;
        edgeIndex.set(k, e);
        edges.push({ a: Math.min(a, b), b: Math.max(a, b), faces: [] });
      }
      edges[e].faces.push(fi);
    }
  });
  const nf = quads.length;
  const ne = edges.length;
  const vEdges = Array.from({ length: nv }, () => []);
  const vFaces = Array.from({ length: nv }, () => []);
  edges.forEach((e, i) => {
    vEdges[e.a].push(i);
    vEdges[e.b].push(i);
  });
  quads.forEach((q, fi) => q.forEach((v) => vFaces[v].push(fi)));

  const rows = new Array(nv + ne + nf);
  const addRow = (m, row, w) => {
    for (const [k, v] of row) m.set(k, (m.get(k) || 0) + v * w);
  };
  // pontos de face
  const fp = quads.map((q) => new Map(q.map((v) => [v, 0.25])));
  fp.forEach((r, fi) => (rows[nv + ne + fi] = r));
  // pontos de aresta
  edges.forEach((e, ei) => {
    const m = new Map();
    if (e.faces.length === 2) {
      m.set(e.a, 0.25);
      m.set(e.b, 0.25);
      addRow(m, fp[e.faces[0]], 0.25);
      addRow(m, fp[e.faces[1]], 0.25);
    } else {
      m.set(e.a, 0.5);
      m.set(e.b, 0.5);
    }
    rows[nv + ei] = m;
  });
  // pontos de vértice
  for (let v = 0; v < nv; v++) {
    if (vFaces[v].length === 0) {
      rows[v] = new Map([[v, 1]]);
      continue;
    }
    const boundary = vEdges[v].filter((ei) => edges[ei].faces.length === 1);
    const m = new Map();
    if (boundary.length === 0) {
      const n = vEdges[v].length;
      for (const fi of vFaces[v]) addRow(m, fp[fi], 1 / (n * vFaces[v].length));
      for (const ei of vEdges[v]) {
        const o = edges[ei].a === v ? edges[ei].b : edges[ei].a;
        m.set(v, (m.get(v) || 0) + (2 / n / n) * 0.5);
        m.set(o, (m.get(o) || 0) + (2 / n / n) * 0.5);
      }
      m.set(v, (m.get(v) || 0) + (n - 3) / n);
    } else if (boundary.length === 2) {
      m.set(v, 6 / 8);
      for (const ei of boundary) {
        const o = edges[ei].a === v ? edges[ei].b : edges[ei].a;
        m.set(o, (m.get(o) || 0) + 1 / 8);
      }
    } else {
      m.set(v, 1);
    }
    rows[v] = m;
  }
  // quads novos (a ordem de enrolamento é preservada)
  const out = [];
  quads.forEach((q, fi) => {
    const f = nv + ne + fi;
    const ep = [0, 1, 2, 3].map((i) => nv + edgeIndex.get(ekey(q[i], q[(i + 1) % 4])));
    for (let i = 0; i < 4; i++) out.push([q[i], ep[i], f, ep[(i + 3) % 4]]);
  });
  return { rows, quads: out, counts: { vertices: nv, edges: ne, faces: nf } };
}

/** Combinação linear (1-t)*A + t*B de duas linhas de stencil. */
export function lerpRows(a, b, t) {
  const m = new Map();
  for (const [k, v] of a) m.set(k, v * (1 - t));
  for (const [k, v] of b) m.set(k, (m.get(k) || 0) + v * t);
  return m;
}
