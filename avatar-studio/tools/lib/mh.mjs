// Parsers para os formatos do MakeHuman (CC0): .obj, .target, .mhskel, .mhw, .mhclo
import fs from 'node:fs';

export function parseObj(file) {
  const lines = fs.readFileSync(file, 'utf8').split('\n');
  const pos = [];
  const uv = [];
  const groups = new Map();
  let cur = '__none__';
  groups.set(cur, []);
  for (const raw of lines) {
    if (raw.startsWith('v ')) {
      const p = raw.trim().split(/\s+/);
      pos.push(+p[1], +p[2], +p[3]);
    } else if (raw.startsWith('vt ')) {
      const p = raw.trim().split(/\s+/);
      uv.push(+p[1], +p[2]);
    } else if (raw.startsWith('g ') || raw.startsWith('o ')) {
      cur = raw.slice(2).trim();
      if (!groups.has(cur)) groups.set(cur, []);
    } else if (raw.startsWith('f ')) {
      const parts = raw.trim().split(/\s+/).slice(1);
      const v = [];
      const t = [];
      for (const s of parts) {
        const q = s.split('/');
        v.push(parseInt(q[0], 10) - 1);
        t.push(q.length > 1 && q[1] !== '' ? parseInt(q[1], 10) - 1 : -1);
      }
      groups.get(cur).push({ v, t });
    }
  }
  return { pos: Float64Array.from(pos), uv: Float64Array.from(uv), groups };
}

export function parseTarget(file) {
  const txt = fs.readFileSync(file, 'utf8');
  const idx = [];
  const d = [];
  for (const raw of txt.split('\n')) {
    if (!raw || raw.charCodeAt(0) === 35) continue; // '#'
    const p = raw.trim().split(/\s+/);
    if (p.length < 4) continue;
    idx.push(parseInt(p[0], 10));
    d.push(+p[1], +p[2], +p[3]);
  }
  return { idx: Int32Array.from(idx), d: Float64Array.from(d) };
}

export function parseSkeleton(file) {
  const j = JSON.parse(fs.readFileSync(file, 'utf8'));
  return j; // {bones:{name:{head,tail,parent,...}}, joints:{name:[verts]}, planes}
}

export function parseWeights(file) {
  const j = JSON.parse(fs.readFileSync(file, 'utf8'));
  return j.weights; // {bone:[[vert,w],...]}
}

// .mhclo (clothes/hair/eyebrows...): referências de vértices do corpo + offsets
export function parseMhclo(file) {
  const lines = fs.readFileSync(file, 'utf8').split('\n');
  const out = { scale: [null, null, null], verts: [], objFile: null, material: null, name: null, zDepth: 0, delete: [] };
  let inVerts = false;
  for (const raw of lines) {
    const line = raw.trim();
    if (!line || line.startsWith('#')) continue;
    const w = line.split(/\s+/);
    if (!inVerts) {
      switch (w[0]) {
        case 'name': out.name = w.slice(1).join(' '); break;
        case 'obj_file': out.objFile = w[1]; break;
        case 'material': out.material = w[1]; break;
        case 'x_scale': out.scale[0] = [+w[1], +w[2], +w[3]]; break;
        case 'y_scale': out.scale[1] = [+w[1], +w[2], +w[3]]; break;
        case 'z_scale': out.scale[2] = [+w[1], +w[2], +w[3]]; break;
        case 'z_depth': out.zDepth = +w[1]; break;
        case 'verts': inVerts = true; break;
        default: break;
      }
    } else if (w[0] === 'delete_verts' || w[0] === 'delete' || /^[a-z_]/i.test(w[0])) {
      inVerts = false;
    } else if (w.length >= 9) {
      out.verts.push({ v: [+w[0], +w[1], +w[2]], w: [+w[3], +w[4], +w[5]], o: [+w[6], +w[7], +w[8]] });
    } else if (w.length >= 6) {
      out.verts.push({ v: [+w[0], +w[1], +w[2]], w: [+w[3], +w[4], +w[5]], o: [0, 0, 0] });
    } else if (w.length === 1) {
      out.verts.push({ v: [+w[0], 0, 1], w: [1, 0, 0], o: [0, 0, 0] });
    }
  }
  return out;
}
