// Material de tecidos: MeshPhysicalMaterial + patches. Funciona sobre Shells (colados ao corpo) e Drapes
// (saia, avental...). Coordenadas de padrão em METROS (aUv), então a densidade do padrão é constante em
// qualquer corpo/morph (princípio de "texel density" consistente).
//
// Atributos da geometria: aUv (m), aEdge (m, distância até a borda do tecido), aRest (posição de referência).
import * as THREE from 'three';

export const FABRICS = {
  cotton: { pt: 'Algodão', en: 'Cotton', rough: 0.88, sheen: 0.45, sheenRough: 0.8, bump: 'WEAVE' },
  knit: { pt: 'Malha canelada', en: 'Ribbed knit', rough: 0.9, sheen: 0.5, sheenRough: 0.85, bump: 'RIB' },
  satin: { pt: 'Cetim', en: 'Satin', rough: 0.44, sheen: 1.0, sheenRough: 0.4, clearcoat: 0.05, ccRough: 0.35, bump: 'WEAVE_FINE' },
  latex: { pt: 'Látex / vinil', en: 'Latex / vinyl', rough: 0.14, clearcoat: 1.0, ccRough: 0.04, bump: 'NONE' },
  denim: { pt: 'Jeans', en: 'Denim', rough: 0.92, sheen: 0.15, sheenRough: 0.9, bump: 'TWILL' },
  velvet: { pt: 'Veludo', en: 'Velvet', rough: 0.96, sheen: 1.0, sheenRough: 0.5, bump: 'WEAVE', sheenBoost: 1.0, sheenMix: 0.12 },
  leather: { pt: 'Couro', en: 'Leather', rough: 0.4, clearcoat: 0.35, ccRough: 0.3, bump: 'GRAIN' },
  sheer: { pt: 'Meia fina (transparente)', en: 'Sheer hosiery', rough: 0.6, sheen: 0.7, sheenRough: 0.6, bump: 'WEAVE_FINE', transparent: true },
  fishnet: { pt: 'Meia arrastão', en: 'Fishnet', rough: 0.5, sheen: 0.4, sheenRough: 0.6, bump: 'NONE', cutout: true },
  lace: { pt: 'Renda', en: 'Lace', rough: 0.7, sheen: 0.5, sheenRough: 0.7, bump: 'NONE', cutout: true },
};

export const PATTERNS = [
  { id: 'none', pt: 'Liso', en: 'Plain' },
  { id: 'stripes', pt: 'Listras', en: 'Stripes' },
  { id: 'pinstripe', pt: 'Risca de giz', en: 'Pinstripe' },
  { id: 'checks', pt: 'Xadrez (vichy)', en: 'Gingham' },
  { id: 'polka', pt: 'Bolinhas', en: 'Polka dots' },
  { id: 'plaid', pt: 'Tartan', en: 'Plaid' },
];
export const TRIMS = [
  { id: 'none', pt: 'Sem acabamento', en: 'No trim' },
  { id: 'band', pt: 'Faixa', en: 'Band' },
  { id: 'piping', pt: 'Debrum', en: 'Piping' },
  { id: 'scallop', pt: 'Barra de renda ondulada', en: 'Scalloped lace edge' },
];

const DECL = /* glsl */ `
uniform vec3 uFabColor;
uniform vec3 uFabColor2;
uniform vec3 uTrimColor;
uniform vec3 uSeamColor;
uniform float uTrimW, uFabScale, uFabOpacity, uThread, uCell, uSeams, uBumpAmt;
uniform highp sampler3D uNoise;
varying vec2 vFabUv;
varying float vEdge;
varying vec3 vRest;
vec3 fabBump(vec3 pos, vec3 N, float h) {
  vec3 dpdx = dFdx(pos);
  vec3 dpdy = dFdy(pos);
  float dhdx = dFdx(h);
  float dhdy = dFdy(h);
  vec3 r1 = cross(dpdy, N);
  vec3 r2 = cross(N, dpdx);
  float det = dot(dpdx, r1);
  vec3 grad = sign(det) * (dhdx * r1 + dhdy * r2);
  return normalize(abs(det) * N - grad);
}
float fabLod(vec2 fuvv, float period) {
  vec2 f = fwidth(fuvv);
  return 1.0 - smoothstep(0.15, 0.42, max(f.x, f.y) / period);
}
float fabHash(vec2 p) {
  vec3 p3 = fract(vec3(p.xyx) * 0.1031);
  p3 += dot(p3, p3.yzx + 33.33);
  return fract((p3.x + p3.y) * p3.z);
}
`;

const ALBEDO = /* glsl */ `
vec2 fuv = vFabUv * uFabScale;
vec3 fabCol = uFabColor;
float fabA = 1.0;
float fabH = 0.0;
float fabKnit = 0.0;
#ifdef PAT_STRIPES
  fabCol = mix(fabCol, uFabColor2, step(0.5, fract(fuv.y / 0.026)));
#endif
#ifdef PAT_PINSTRIPE
  float pl = abs(fract(fuv.x / 0.011 + 0.5) - 0.5) * 0.011;
  fabCol = mix(fabCol, uFabColor2, (1.0 - smoothstep(0.0004, 0.0011, pl)) * 0.9);
#endif
#ifdef PAT_CHECKS
  float gx = step(0.5, fract(fuv.x / 0.022));
  float gy = step(0.5, fract(fuv.y / 0.022));
  fabCol = mix(fabCol, uFabColor2, 0.5 * (gx + gy) * 0.8);
#endif
#ifdef PAT_POLKA
  vec2 pg = fuv / 0.02;
  pg.x += 0.5 * mod(floor(pg.y), 2.0);
  float pd = length(fract(pg) - 0.5) * 0.02;
  fabCol = mix(fabCol, uFabColor2, 1.0 - smoothstep(0.0034, 0.0041, pd));
#endif
#ifdef PAT_PLAID
  float bx = 1.0 - smoothstep(0.0, 0.0035, abs(fract(fuv.x / 0.05) - 0.5) * 0.05 - 0.0125);
  float by = 1.0 - smoothstep(0.0, 0.0035, abs(fract(fuv.y / 0.05) - 0.5) * 0.05 - 0.0125);
  fabCol = mix(fabCol, uFabColor2, max(bx, by) * 0.55);
  fabCol *= 1.0 - 0.45 * bx * by;
#endif
#ifdef BUMP_RIB
  float lodRib = fabLod(fuv, 0.0036);
  float rb = sin(fuv.x * 6.2832 / 0.0036);
  fabH += rb * 0.00026 * uBumpAmt * lodRib;
  fabCol *= 1.0 - 0.07 * lodRib + 0.07 * lodRib * (0.5 + 0.5 * rb) * 2.0 * 0.5;
#endif
#ifdef BUMP_WEAVE
  fabH += sin(fuv.x * 6.2832 / 0.0014) * sin(fuv.y * 6.2832 / 0.0014) * 0.00008 * uBumpAmt * fabLod(fuv, 0.0014);
#endif
#ifdef BUMP_WEAVE_FINE
  fabH += sin(fuv.x * 6.2832 / 0.0008) * sin(fuv.y * 6.2832 / 0.0008) * 0.00004 * uBumpAmt * fabLod(fuv, 0.0008);
#endif
#ifdef BUMP_TWILL
  float lodTw = fabLod(fuv, 0.0024);
  float tw = sin((fuv.x + fuv.y) * 6.2832 / 0.0024) * lodTw;
  fabH += tw * 0.00013 * uBumpAmt;
  fabCol *= 0.94 + 0.06 * tw;
  fabCol *= 0.92 + 0.16 * texture(uNoise, vRest * 9.0).g;
#endif
#ifdef BUMP_GRAIN
  vec4 gn = texture(uNoise, vRest * 36.0);
  float lodGr = 1.0 - smoothstep(0.004, 0.014, length(fwidth(vRest * 36.0)));
  fabH += ((gn.r - 0.5) * 0.00026 - (1.0 - smoothstep(0.25, 0.4, gn.r)) * 0.0001) * uBumpAmt * lodGr;
  fabCol *= 0.9 + 0.2 * texture(uNoise, vRest * 5.0).a;
#endif
#ifdef SEAMS
  float sl = abs(fract(vRest.x / 0.052 + 0.5) - 0.5) * 0.052;
  float sm = 1.0 - smoothstep(0.0007, 0.0019, sl);
  fabCol = mix(fabCol, uSeamColor, sm * uSeams);
  fabH -= sm * 0.0004 * uSeams;
#endif
#ifdef TRIM_BAND
  fabCol = mix(fabCol, uTrimColor, 1.0 - smoothstep(uTrimW * 0.92, uTrimW, vEdge));
#endif
#ifdef TRIM_PIPING
  fabCol = mix(fabCol, uTrimColor, 1.0 - smoothstep(0.0009, 0.0016, abs(vEdge - uTrimW)));
  fabH += (1.0 - smoothstep(0.0009, 0.0016, abs(vEdge - uTrimW))) * 0.00035;
#endif
#ifdef TRIM_SCALLOP
  float sc = fract(fuv.x / 0.018) * 2.0 - 1.0;
  float cutD = uTrimW * 0.62 * sqrt(max(0.0, 1.0 - sc * sc));
  fabA *= smoothstep(cutD, cutD + 0.0007, vEdge);
  fabCol = mix(fabCol, uTrimColor, 1.0 - smoothstep(uTrimW * 0.9, uTrimW, vEdge));
#endif
#ifdef FAB_SHEER
  float ndv = abs(dot(normalize(vNormal), normalize(vViewPosition)));
  fabA = mix(uFabOpacity, min(1.0, uFabOpacity * 2.2 + 0.18), pow(1.0 - ndv, 2.2));
  fabKnit = sin(fuv.x * 6.2832 / 0.0012) * sin(fuv.y * 6.2832 / 0.0012) * fabLod(fuv, 0.0012);
  fabA *= 0.93 + 0.07 * fabKnit;
  fabCol *= 0.97 + 0.03 * fabKnit;
#endif
#ifdef FAB_FISHNET
  vec2 fq = vec2(fuv.x + fuv.y, fuv.x - fuv.y) / (uCell * 1.4142);
  float fd = min(abs(fract(fq.x + 0.5) - 0.5), abs(fract(fq.y + 0.5) - 0.5));
  float thread = 1.0 - smoothstep(uThread * 0.5, uThread * 0.5 + 0.06, fd);
  vec2 fqw = fwidth(fq);
  float lodF = smoothstep(0.16, 0.5, max(fqw.x, fqw.y));
  thread = mix(thread, 1.0 - pow(1.0 - uThread, 2.0), lodF); // longe: cobertura média
  fabA = thread;
  fabCol *= 0.85 + 0.15 * thread;
#endif
#ifdef FAB_LACE
  vec2 lg = fuv / uCell;
  vec2 li = floor(lg);
  vec2 lf = fract(lg) - 0.5;
  float la = atan(lf.y, lf.x);
  float lr = length(lf);
  float petals = 0.17 + 0.13 * abs(cos(2.5 * la));
  float flower = 1.0 - smoothstep(petals - 0.025, petals + 0.025, lr);
  float eye = 1.0 - smoothstep(0.035, 0.06, lr);
  float vine = 1.0 - smoothstep(0.012, 0.03, abs(lr - 0.44));
  vec2 ng = abs(fract(lg * 2.0 + 0.25) - 0.5);
  float net = 1.0 - smoothstep(0.04, 0.085, min(ng.x, ng.y));
  fabA = clamp(max(max(flower * (1.0 - 0.7 * eye), vine * 0.9), net * 0.42), 0.0, 1.0);
  vec2 lgw = fwidth(lg);
  fabA = mix(fabA, 0.55, smoothstep(0.12, 0.4, max(lgw.x, lgw.y)));
  fabCol *= 0.9 + 0.1 * fabHash(li);
#endif
diffuseColor.rgb = fabCol;
diffuseColor.a *= fabA;
`;

const NORMAL = /* glsl */ `
normal = fabBump(-vViewPosition, normal, fabH);
`;

export class FabricMaterial extends THREE.MeshPhysicalMaterial {
  constructor({ noise, ...opts } = {}) {
    super({ color: 0xffffff, roughness: 0.8, metalness: 0, sheen: 0.3, sheenRoughness: 0.8, ior: 1.45 });
    this.u = {
      uNoise: { value: noise },
      uFabColor: { value: new THREE.Color('#222') },
      uFabColor2: { value: new THREE.Color('#fff') },
      uTrimColor: { value: new THREE.Color('#fff') },
      uSeamColor: { value: new THREE.Color('#000') },
      uTrimW: { value: 0.012 },
      uFabScale: { value: 1 },
      uFabOpacity: { value: 0.3 },
      uThread: { value: 0.22 },
      uCell: { value: 0.0042 },
      uSeams: { value: 0 },
      uBumpAmt: { value: 1 },
    };
    this.params = {};
    this.setParams({ fabric: 'cotton', color: '#d9d4d2', color2: '#ffffff', pattern: 'none', trim: 'none', trimColor: '#ffffff', trimWidth: 0.012, seams: 0, seamColor: '#000000', scale: 1, denier: 0.3, cell: 0.0042, thread: 0.22, ...opts });
  }

  customProgramCacheKey() {
    return 'fabric-' + JSON.stringify(this.defines);
  }

  onBeforeCompile(shader) {
    Object.assign(shader.uniforms, this.u);
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\nattribute vec2 aUv;\nattribute float aEdge;\nattribute vec3 aRest;\nvarying vec2 vFabUv;\nvarying float vEdge;\nvarying vec3 vRest;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvFabUv = aUv;\nvEdge = aEdge;\nvRest = aRest;');
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', '#include <common>\n' + DECL)
      .replace('#include <map_fragment>', '#include <map_fragment>\n' + ALBEDO)
      .replace('#include <normal_fragment_maps>', '#include <normal_fragment_maps>\n' + NORMAL);
  }

  /** p: { fabric, color, color2, pattern, trim, trimColor, trimWidth, seams, seamColor, scale, denier, cell, thread } */
  setParams(patch) {
    const p = (this.params = { ...this.params, ...patch });
    const f = FABRICS[p.fabric] || FABRICS.cotton;
    const u = this.u;
    u.uFabColor.value.set(p.color);
    u.uFabColor2.value.set(p.color2);
    u.uTrimColor.value.set(p.trimColor);
    u.uSeamColor.value.set(p.seamColor);
    u.uTrimW.value = p.trimWidth;
    u.uFabScale.value = p.scale;
    u.uFabOpacity.value = p.denier;
    u.uThread.value = p.thread;
    u.uCell.value = p.cell;
    u.uSeams.value = p.seams;
    this.roughness = f.rough;
    this.metalness = 0;
    this.sheen = f.sheen ?? 0;
    this.sheenRoughness = f.sheenRough ?? 0.8;
    const base = new THREE.Color(p.color);
    this.sheenColor.copy(base).lerp(new THREE.Color(1, 1, 1), f.sheenMix ?? 0.35).multiplyScalar(f.sheenBoost ?? 1);
    this.clearcoat = f.clearcoat ?? 0;
    this.clearcoatRoughness = f.ccRough ?? 0.2;
    // transparência suave (sem recorte duro): evita moiré; renda/arrastão/meia fina vêm depois do corpo
    const blend = !!f.cutout || !!f.transparent || p.trim === 'scallop';
    this.transparent = blend;
    this.depthWrite = !f.transparent && !f.cutout;
    this.alphaTest = blend ? 0.02 : 0;
    this.alphaToCoverage = false;
    this.side = blend ? THREE.DoubleSide : THREE.FrontSide;
    const defines = {};
    defines['BUMP_' + f.bump] = '';
    if (p.pattern && p.pattern !== 'none') defines['PAT_' + p.pattern.toUpperCase()] = '';
    if (p.trim && p.trim !== 'none') defines['TRIM_' + p.trim.toUpperCase()] = '';
    if (p.seams > 0) defines.SEAMS = '';
    if (p.fabric === 'sheer') defines.FAB_SHEER = '';
    if (p.fabric === 'fishnet') defines.FAB_FISHNET = '';
    if (p.fabric === 'lace') defines.FAB_LACE = '';
    const changed = JSON.stringify(defines) !== JSON.stringify(this.defines || {});
    this.defines = defines;
    if (changed) this.needsUpdate = true;
  }
}
