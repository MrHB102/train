// Recorte de malha de triângulos por um campo escalar por vértice (F <= 0 fica, F > 0 sai).
//
//  - "Snap": vértices a menos de `snap` do plano ficam exatamente em F=0 e entram na borda do corte
//    (evita triângulos-lasca; ver validate-model).
//  - Cada vértice novo nasce numa aresta (i, j, t): posição = lerp(P[i], P[j], t). Assim o corte
//    acompanha qualquer morph, pose ou Jiggle (ADR 0003) e as roupas (Shells) reutilizam o mecanismo.
//
// tris: array plano (Uint16/Uint32/Array) de índices; F: Float32Array/Float64Array por vértice (modificado
// pelo snap). Retorna triângulos em índices "estendidos": id >= n é o vértice novo (id - n) de clipVerts.
export function clipTriangles(tris, F, snap = 0) {
  const n = F.length;
  if (snap > 0) for (let v = 0; v < n; v++) if (Math.abs(F[v]) < snap) F[v] = 0;
  const edgeMap = new Map();
  const clipVerts = []; // [i, j, t]
  const edgeVert = (i, j) => {
    const key = i * n + j;
    let r = edgeMap.get(key);
    if (r === undefined) {
      r = n + clipVerts.length;
      clipVerts.push([i, j, F[i] / (F[i] - F[j])]);
      edgeMap.set(key, r);
    }
    return r;
  };
  const out = [];
  const srcTri = [];
  for (let t = 0; t < tris.length; t += 3) {
    const tri = [tris[t], tris[t + 1], tris[t + 2]];
    const poly = [];
    for (let i = 0; i < 3; i++) {
      const v = tri[i];
      const w = tri[(i + 1) % 3];
      const kv = F[v] <= 0;
      const kw = F[w] <= 0;
      if (kv) poly.push(v);
      if (kv && !kw && F[v] < 0) poly.push(edgeVert(v, w));
      if (!kv && kw && F[w] < 0) poly.push(edgeVert(w, v));
    }
    const clean = poly.filter((v, i) => v !== poly[(i + poly.length - 1) % poly.length]);
    if (clean.length < 3) continue;
    for (let i = 1; i < clean.length - 1; i++) {
      out.push(clean[0], clean[i], clean[i + 1]);
      srcTri.push(t / 3);
    }
  }
  return { tris: out, clipVerts, count: n, srcTri };
}

/** Compacta: retorna os vértices usados (originais e novos) e os triângulos reindexados. */
export function compactClip(res) {
  const { tris, clipVerts, count: n, srcTri } = res;
  const used = new Set(tris);
  const list = [...used].sort((a, b) => a - b);
  const remap = new Map(list.map((v, i) => [v, i]));
  return {
    vertices: list.map((v) => (v < n ? { a: v, b: v, t: 0 } : { a: clipVerts[v - n][0], b: clipVerts[v - n][1], t: clipVerts[v - n][2] })),
    tris: Uint32Array.from(tris, (v) => remap.get(v)),
    sourceIndex: list,
    srcTri: Uint32Array.from(srcTri),
  };
}
