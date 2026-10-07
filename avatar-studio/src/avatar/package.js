// Carrega o pacote binário gerado por tools/build-assets.mjs
const TYPES = { Float32Array, Uint16Array, Uint8Array, Int16Array, Int32Array, Uint32Array };

async function fetchBinary(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url}: HTTP ${res.status}`);
  let buf = await res.arrayBuffer();
  const b = new Uint8Array(buf);
  if (b.length > 2 && b[0] === 0x1f && b[1] === 0x8b) {
    const stream = new Blob([buf]).stream().pipeThrough(new DecompressionStream('gzip'));
    buf = await new Response(stream).arrayBuffer();
  }
  return buf;
}

async function fetchJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url}: HTTP ${res.status}`);
  return res.json();
}

function readSections(meta, buf) {
  const out = {};
  for (const [name, m] of Object.entries(meta)) out[name] = new TYPES[m.t](buf, m.o, m.n);
  return out;
}

/** Monta o pacote a partir dos JSON/binários já lidos (usado no navegador e nas ferramentas Node). */
export function parsePackage(body, targets, bodyBuf, targetBuf) {
  const b = readSections(body.sections, bodyBuf);
  const t = readSections(targets.sections, targetBuf);
  return {
    meta: body,
    ...b,
    targets: {
      names: targets.targets.map((x) => x[0]),
      offset: Uint32Array.from(targets.targets.map((x) => x[1])),
      count: Uint32Array.from(targets.targets.map((x) => x[2])),
      scale: Float32Array.from(targets.targets.map((x) => x[3])),
      idx: t.idx,
      delta: t.delta,
    },
  };
}

export async function loadBodyPackage(base = './data/') {
  const [body, targets, bodyBuf, targetBuf] = await Promise.all([
    fetchJson(base + 'body.json'),
    fetchJson(base + 'targets.json'),
    fetchBinary(base + 'body.bin.gz'),
    fetchBinary(base + 'targets.bin.gz'),
  ]);
  return parsePackage(body, targets, bodyBuf, targetBuf);
}
