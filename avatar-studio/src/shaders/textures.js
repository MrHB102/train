// Texturas procedurais geradas na inicialização (sem arquivos externos):
//  - ruído 3D tileável (poros, mosqueado, veias);
//  - LUT de pele pré-integrada (espalhamento subsuperficial: N·L × curvatura -> difusão RGB).
import * as THREE from 'three';

// ---- ruído de valor tileável ------------------------------------------------------------------
function hash3(x, y, z, seed) {
  let h = (x * 374761393 + y * 668265263 + z * 2147483647 + seed * 1274126177) | 0;
  h = (h ^ (h >>> 13)) * 1274126177;
  h = (h ^ (h >>> 16)) | 0;
  return (h >>> 0) / 4294967295;
}
const fade = (t) => t * t * t * (t * (t * 6 - 15) + 10);

function valueNoise(x, y, z, period, seed) {
  const xi = Math.floor(x), yi = Math.floor(y), zi = Math.floor(z);
  const xf = fade(x - xi), yf = fade(y - yi), zf = fade(z - zi);
  const w = (n) => ((n % period) + period) % period;
  const v = (dx, dy, dz) => hash3(w(xi + dx), w(yi + dy), w(zi + dz), seed);
  const l = (a, b, t) => a + (b - a) * t;
  return l(
    l(l(v(0, 0, 0), v(1, 0, 0), xf), l(v(0, 1, 0), v(1, 1, 0), xf), yf),
    l(l(v(0, 0, 1), v(1, 0, 1), xf), l(v(0, 1, 1), v(1, 1, 1), xf), yf),
    zf
  );
}

/** Ruído 3D RGBA 64³: R = fBm fino, G = fBm médio, B = ridged (veias/rugas), A = fBm largo. */
export function createNoise3D(size = 64) {
  const data = new Uint8Array(size * size * size * 4);
  let o = 0;
  for (let z = 0; z < size; z++) {
    for (let y = 0; y < size; y++) {
      for (let x = 0; x < size; x++) {
        const f = (p, per, seed) => valueNoise((x / size) * per, (y / size) * per, (z / size) * per, per, seed);
        const r = 0.5 * f(0, 16, 1) + 0.3 * f(0, 32, 2) + 0.2 * f(0, 64, 3);
        const g = 0.6 * f(0, 8, 4) + 0.4 * f(0, 16, 5);
        const rid = 1 - Math.abs(f(0, 8, 6) * 2 - 1);
        const b = rid * rid;
        const a = 0.6 * f(0, 4, 7) + 0.4 * f(0, 8, 8);
        data[o++] = Math.round(r * 255);
        data[o++] = Math.round(g * 255);
        data[o++] = Math.round(b * 255);
        data[o++] = Math.round(a * 255);
      }
    }
  }
  const t = new THREE.Data3DTexture(data, size, size, size);
  t.format = THREE.RGBAFormat;
  t.type = THREE.UnsignedByteType;
  t.minFilter = THREE.LinearFilter;
  t.magFilter = THREE.LinearFilter;
  t.wrapS = t.wrapT = t.wrapR = THREE.RepeatWrapping;
  t.unpackAlignment = 1;
  t.needsUpdate = true;
  return t;
}

// ---- LUT de pele pré-integrada (Penner 2011; perfil de 6 Gaussianas de d'Eon & Luebke) ----------
const PROFILE = [
  { v: 0.0064, w: [0.233, 0.455, 0.649] },
  { v: 0.0484, w: [0.1, 0.336, 0.344] },
  { v: 0.187, w: [0.118, 0.198, 0.0] },
  { v: 0.567, w: [0.113, 0.007, 0.007] },
  { v: 1.99, w: [0.358, 0.004, 0.0] },
  { v: 7.41, w: [0.078, 0.0, 0.0] },
];
function profile(rMm, ch) {
  let s = 0;
  for (const p of PROFILE) s += p.w[ch] * Math.exp((-rMm * rMm) / (2 * p.v)) / (2 * Math.PI * p.v);
  return s;
}

/**
 * LUT 256 × 64. x = N·L * 0.5 + 0.5; y = log(curvatura) normalizada, curvatura = 1/raio (1/mm)
 * entre 1/300 mm (coxa/torso) e 1/3 mm (dedos). Saída RGB = difusão pré-integrada (≈ max(N·L,0) com
 * penumbra avermelhada macia).
 */
export const LUT_CURV_MIN = 1 / 300;
export const LUT_CURV_MAX = 1 / 3;
export function createSkinLUT(w = 256, h = 64) {
  const data = new Uint8Array(w * h * 4);
  const steps = 96;
  for (let j = 0; j < h; j++) {
    const c = Math.exp(Math.log(LUT_CURV_MIN) + (j / (h - 1)) * (Math.log(LUT_CURV_MAX) - Math.log(LUT_CURV_MIN)));
    const radius = 1 / c; // mm
    for (let i = 0; i < w; i++) {
      const theta = Math.acos(Math.min(1, Math.max(-1, (i / (w - 1)) * 2 - 1)));
      const num = [0, 0, 0];
      const den = [0, 0, 0];
      for (let s = 0; s < steps; s++) {
        const x = -Math.PI + ((s + 0.5) / steps) * 2 * Math.PI;
        const dist = 2 * radius * Math.abs(Math.sin(x / 2));
        const lam = Math.max(0, Math.cos(theta + x));
        for (let ch = 0; ch < 3; ch++) {
          const wgt = profile(dist, ch);
          num[ch] += lam * wgt;
          den[ch] += wgt;
        }
      }
      const o = (j * w + i) * 4;
      for (let ch = 0; ch < 3; ch++) data[o + ch] = Math.round(255 * Math.min(1, num[ch] / (den[ch] || 1)));
      data[o + 3] = 255;
    }
  }
  const t = new THREE.DataTexture(data, w, h, THREE.RGBAFormat);
  t.minFilter = THREE.LinearFilter;
  t.magFilter = THREE.LinearFilter;
  t.wrapS = t.wrapT = THREE.ClampToEdgeWrapping;
  t.colorSpace = THREE.NoColorSpace;
  t.needsUpdate = true;
  return t;
}
