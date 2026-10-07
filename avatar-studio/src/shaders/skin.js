// Material da pele: MeshPhysicalMaterial + patches (onBeforeCompile) em coordenadas de referência (aRest).
//
//  - Texturas 100% procedurais ancoradas na pele (aRest = posição no estado neutro): poros, mosqueado,
//    veias, sardas, pintas e vermelhidão acompanham qualquer morph sem esticar.
//  - Espalhamento subsuperficial: difusão pré-integrada (LUT N·L × curvatura) com penumbra avermelhada.
//  - Cada Imperfection (poros, manchas, sardas, pintas, veias, vermelhidão, penugem) é um uniforme e
//    pode ir a zero (ver domain/skin.js).
import * as THREE from 'three';
import { defaultSkin, effectiveSkin } from '../domain/skin.js';

const BLUSH_N = 12;
const MOLE_N = 10;
const NAIL_N = 10;

const ANATOMY = /* glsl */ `
// ---------------- anatomia da superfície (marcas em avatar/anatomy.js) ----------------
#define A_CLAV 0
#define A_SCM 10
#define A_NOTCH 16
#define A_COST 17
#define A_LINEA 25
#define A_NAVEL 28
#define A_ASIS 29
#define A_SPINE 33
#define A_DIMPLE 36
#define A_SCAP 38
#define A_RIBS 42
uniform vec3 uAnat[44];
uniform vec4 uAnatK;
uniform vec4 uAnatK2;
uniform float uLean, uCavGain;
varying float vCav;
float gAnatH = 0.0;
float gAnatCav = 0.0;
float gaussA(float x, float w) { return exp(-(x * x) / (w * w)); }
float segD(vec3 p, vec3 a, vec3 b, out float t) {
  vec3 ab = b - a;
  t = clamp(dot(p - a, ab) / max(dot(ab, ab), 1e-9), 0.0, 1.0);
  return length(p - (a + ab * t));
}
void anatomyField(vec3 p) {
  float K = uAnatK.x;
  if (K <= 0.001 || p.y < -0.12) return;
  float H = 0.0;
  float C = 0.0;
  // pescoço, clavículas e incisura jugular
  float kc = uAnatK.y * K;
  if (kc > 0.0 && p.y > 0.40) {
    for (int sd = 0; sd < 2; sd++) {
      float sgn = sd == 0 ? 1.0 : -1.0;
      float best = 1e9;
      float bt = 0.0;
      vec3 q = vec3(0.0);
      for (int i = 0; i < 4; i++) {
        vec3 a = uAnat[A_CLAV + sd * 5 + i];
        vec3 b = uAnat[A_CLAV + sd * 5 + i + 1];
        float t;
        float d = segD(p, a, b, t);
        if (d < best) { best = d; bt = (float(i) + t) * 0.25; q = a + (b - a) * t; }
      }
      float up = smoothstep(-0.005, 0.005, p.y - q.y);
      float taper = smoothstep(0.0, 0.1, bt) * (1.0 - smoothstep(0.86, 1.0, bt));
      float ridge = gaussA(best, 0.0085);
      float fossa = up * gaussA(best - 0.022, 0.015);
      float infra = (1.0 - up) * gaussA(best - 0.019, 0.016);
      H += kc * taper * (0.0031 * ridge - 0.0042 * fossa - 0.0018 * infra);
      C += kc * taper * (0.75 * fossa + 0.40 * infra);
      float bm = 1e9;
      float tm = 0.0;
      vec3 qm = vec3(0.0);
      for (int i = 0; i < 2; i++) {
        vec3 a = uAnat[A_SCM + sd * 3 + i];
        vec3 b = uAnat[A_SCM + sd * 3 + i + 1];
        float t;
        float d = segD(p, a, b, t);
        if (d < bm) { bm = d; tm = (float(i) + t) * 0.5; qm = a + (b - a) * t; }
      }
      float lat = smoothstep(-0.004, 0.004, (p.x - qm.x) * sgn);
      float tp = smoothstep(0.0, 0.15, tm);
      H += kc * tp * (0.0030 * gaussA(bm, 0.0100) - 0.0022 * lat * gaussA(bm - 0.0150, 0.0085));
      C += kc * tp * 0.55 * lat * gaussA(bm - 0.0150, 0.0085);
    }
    vec3 dn = p - uAnat[A_NOTCH];
    dn.y *= 0.8;
    float pit = gaussA(length(dn), 0.0105);
    H -= kc * 0.0050 * pit;
    C += kc * 0.75 * pit;
  }
  // arco costal e costelas laterais
  float kr = uAnatK2.y * K * uLean;
  if (kr > 0.0 && p.z > 0.0 && p.y > 0.10 && p.y < 0.34) {
    for (int sd = 0; sd < 2; sd++) {
      float best = 1e9;
      float bt = 0.0;
      vec3 q = vec3(0.0);
      for (int i = 0; i < 3; i++) {
        vec3 a = uAnat[A_COST + sd * 4 + i];
        vec3 b = uAnat[A_COST + sd * 4 + i + 1];
        float t;
        float d = segD(p, a, b, t);
        if (d < best) { best = d; bt = (float(i) + t) * 0.3333; q = a + (b - a) * t; }
      }
      float below = smoothstep(0.004, -0.004, p.y - q.y);
      float tp = smoothstep(0.0, 0.12, bt);
      H += kr * tp * (0.0018 * gaussA(best, 0.0120) - 0.0022 * below * gaussA(best - 0.016, 0.013));
      C += kr * tp * 0.45 * below * gaussA(best - 0.016, 0.013);
      vec3 rc = uAnat[A_RIBS + sd];
      vec3 dr = p - rc;
      float m = exp(-dot(dr, dr) / 0.003);
      float lodR = 1.0 - smoothstep(0.004, 0.009, fwidth(p.y));
      float rb = sin(p.y * 232.7);
      H += kr * 0.0007 * rb * m * lodR;
      C += kr * 0.12 * max(-rb, 0.0) * m * lodR;
    }
  }
  // abdômen: linha alba, retos abdominais (tônus), interseções tendíneas
  float ka = uAnatK.z * K;
  float yX = uAnat[A_LINEA].y;
  float yN = uAnat[A_NAVEL].y;
  float yP = uAnat[A_LINEA + 2].y;
  if (ka > 0.0 && p.z > 0.0 && p.y < yX + 0.03 && p.y > yP - 0.03) {
    float ax = abs(p.x);
    float tone = uAnatK2.w;
    float win = smoothstep(yP - 0.005, yP + 0.05, p.y) * (1.0 - smoothstep(yX - 0.03, yX, p.y));
    float above = 0.15 + 0.85 * smoothstep(yN - 0.01, yN + 0.04, p.y);
    float lin = gaussA(p.x, 0.0105) * win * above;
    H -= ka * lin * (0.0009 + 0.0011 * tone);
    C += ka * lin * 0.20;
    float rect = gaussA(ax - 0.027, 0.012) * smoothstep(yN - 0.045, yN + 0.02, p.y) * (1.0 - smoothstep(yX - 0.05, yX - 0.01, p.y));
    H += ka * tone * 0.0021 * rect;
    float mk = smoothstep(0.05, 0.032, ax);
    for (int k = 0; k < 3; k++) {
      float yk = yN + 0.032 + 0.037 * float(k);
      float g = gaussA(p.y - yk, 0.0046) * mk;
      H -= ka * tone * 0.0011 * g;
      C += ka * tone * 0.25 * g;
    }
  }
  // umbigo
  float kn = uAnatK2.z * K;
  if (kn > 0.0) {
    vec3 dv = p - uAnat[A_NAVEL];
    if (abs(dv.z) < 0.03 && abs(dv.y) < 0.03) {
      float e = length(vec2(dv.x / 0.0062, dv.y / 0.0092));
      float pitN = exp(-e * e * 0.9);
      float rimN = exp(-pow(e - 1.5, 2.0) / 0.35);
      H += kn * (-0.0050 * pitN + 0.0013 * rimN);
      C += kn * 0.65 * pitN;
    }
  }
  // quadril: espinha ilíaca e prega inguinal (linha em V)
  float kh = uAnatK.w * K;
  if (kh > 0.0 && p.z > 0.0 && p.y < 0.12 && p.y > -0.12) {
    for (int sd = 0; sd < 2; sd++) {
      vec3 a = uAnat[A_ASIS + sd * 2];
      vec3 b = uAnat[A_ASIS + sd * 2 + 1];
      float t;
      float d = segD(p, a, b, t);
      float g = gaussA(d, 0.0110) * smoothstep(0.12, 0.4, t) * (1.0 - smoothstep(0.88, 1.0, t));
      H -= kh * 0.0024 * g;
      C += kh * 0.50 * g;
      H += kh * 0.0030 * gaussA(length(p - a), 0.015);
    }
  }
  // costas: coluna, vértebra C7, covinhas lombares, escápulas
  float kb = uAnatK2.x * K;
  if (kb > 0.0 && p.z < 0.0) {
    for (int i = 0; i < 2; i++) {
      vec3 a = uAnat[A_SPINE + i];
      vec3 b = uAnat[A_SPINE + i + 1];
      float t;
      float d = segD(p, a, b, t);
      float tt = (float(i) + t) * 0.5;
      float w = smoothstep(0.0, 0.08, tt) * (1.0 - smoothstep(0.82, 1.0, tt));
      H -= kb * 0.0014 * gaussA(d, 0.0120) * w;
      H += kb * 0.0016 * gaussA(abs(p.x) - 0.032, 0.016) * w * smoothstep(0.35, 0.65, tt) * (1.0 - smoothstep(0.85, 1.0, tt));
      C += kb * 0.22 * gaussA(d, 0.0120) * w;
    }
    H += kb * 0.0030 * gaussA(length(p - uAnat[A_SPINE]), 0.011);
    for (int sd = 0; sd < 2; sd++) {
      float dd = length(p - uAnat[A_DIMPLE + sd]);
      H -= kb * 0.0032 * gaussA(dd, 0.0130);
      C += kb * 0.6 * gaussA(dd, 0.0130);
      vec3 a = uAnat[A_SCAP + sd * 2];
      vec3 b = uAnat[A_SCAP + sd * 2 + 1];
      float t;
      float d = segD(p, a, b, t);
      float tp = smoothstep(0.0, 0.2, t) * (1.0 - smoothstep(0.8, 1.0, t));
      H += kb * 0.0022 * gaussA(d, 0.013) * tp;
      C += kb * 0.20 * gaussA(d - 0.018, 0.013) * tp;
    }
  }
  gAnatH = H;
  gAnatCav = clamp(C, 0.0, 1.0);
}
`;

const DECL = /* glsl */ `
uniform highp sampler3D uNoise;
uniform sampler2D uSkinLUT;
uniform vec3 uTone;
uniform float uUndertone, uPores, uMottle, uFreckles, uMoles, uVeins, uRedness, uOil, uSSS, uShimmer, uNails;
uniform vec3 uNailColor, uShimmerColor;
uniform vec4 uBlush[${BLUSH_N}];
uniform vec4 uMole[${MOLE_N}];
uniform vec4 uNail[${NAIL_N}];
varying vec3 vRest;
float gCurvY = 0.5;
float gCavT = 0.0;
float gNail = 0.0;

float hash13(vec3 p3) {
  p3 = fract(p3 * 0.1031);
  p3 += dot(p3, p3.zyx + 31.32);
  return fract((p3.x + p3.y) * p3.z);
}
vec3 hash33(vec3 p3) {
  p3 = fract(p3 * vec3(0.1031, 0.1030, 0.0973));
  p3 += dot(p3, p3.yxz + 33.33);
  return fract((p3.xxy + p3.yxx) * p3.zyx);
}
// sardas: pontos aleatórios numa grade 3D (cada célula pode ou não ter uma sarda)
float freckleSpots(vec3 p, float density) {
  vec3 i = floor(p);
  vec3 f = fract(p);
  float m = 0.0;
  for (int z = -1; z <= 1; z++) for (int y = -1; y <= 1; y++) for (int x = -1; x <= 1; x++) {
    vec3 c = vec3(float(x), float(y), float(z));
    vec3 id = i + c;
    if (hash13(id) > density) continue;
    vec3 o = hash33(id);
    float r = 0.15 + 0.11 * hash13(id + 7.7);
    float d = length(c + 0.2 + 0.6 * o - f);
    m = max(m, 1.0 - smoothstep(r * 0.35, r, d));
  }
  return m;
}
// bump mapping por derivadas de tela (sem tangentes)
vec3 skinBump(vec3 pos, vec3 N, float h) {
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
vec3 skinLUT(float ndl) {
  vec3 lut = texture2D(uSkinLUT, vec2(ndl * 0.5 + 0.5, gCurvY)).rgb;
  return mix(vec3(max(ndl, 0.0)), lut, uSSS);
}
${ANATOMY}
`;

const LIGHT_OVERRIDE = /* glsl */ `
// ---- difusão de pele: penumbra avermelhada pré-integrada ----
void RE_Direct_Skin( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight ) {
  ReflectedLight tmp = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
  RE_Direct_Physical( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, tmp );
  reflectedLight.directSpecular += tmp.directSpecular;
  vec3 wrap = skinLUT( dot( geometryNormal, directLight.direction ) );
  reflectedLight.directDiffuse += directLight.color * wrap * BRDF_Lambert( material.diffuseContribution );
}
void RE_IndirectDiffuse_Skin( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight ) {
  vec3 bleed = mix( vec3( 1.0 ), vec3( 1.07, 0.94, 0.90 ), uSSS );
  RE_IndirectDiffuse_Physical( irradiance * bleed, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
}
#undef RE_Direct
#undef RE_IndirectDiffuse
#define RE_Direct RE_Direct_Skin
#define RE_IndirectDiffuse RE_IndirectDiffuse_Skin
`;

const ALBEDO = /* glsl */ `
vec3 rp = vRest;
vec4 nA = texture(uNoise, rp * 28.0);
vec4 nA2 = texture(uNoise, rp * 41.3 + vec3(0.31, 0.17, 0.53));
vec4 nB = texture(uNoise, rp * 7.0 + 0.37);
vec4 nC = texture(uNoise, rp * 2.2 + 0.71);
vec3 skinCol = uTone;
skinCol *= mix(vec3(0.965, 0.985, 1.04), vec3(1.045, 0.995, 0.925), uUndertone * 0.5 + 0.5);
// mosqueado (manchas suaves de cor)
float mott = (nC.a - 0.5) * 0.30 + (nB.g - 0.5) * 0.18;
skinCol *= 1.0 + mott * uMottle;
skinCol *= vec3(1.0 + (nB.a - 0.5) * 0.10 * uMottle, 1.0, 1.0 - (nB.a - 0.5) * 0.12 * uMottle);
// vermelhidão (joelhos, tornozelos, calcanhares, dedos)
float redAcc = 0.0;
for (int i = 0; i < ${BLUSH_N}; i++) {
  vec4 b = uBlush[i];
  if (b.w <= 0.0) continue;
  vec3 d = rp - b.xyz;
  redAcc += exp(-dot(d, d) / (b.w * b.w));
}
skinCol = mix(skinCol, skinCol * vec3(1.09, 0.80, 0.78), clamp(redAcc * 0.55 * uRedness, 0.0, 0.9));
// veias: linhas finas e contínuas (curvas de nível do ruído 3D), azuladas e sutis, em manchas e mais nas pernas e pés.
// (antes eram os picos do ruído, que viravam tracinhos soltos atrás da coxa)
float veinMask = (1.0 - smoothstep(-0.35, 0.1, rp.y)) * 0.8 + 0.2;
float vn = texture(uNoise, rp * 6.5 + 0.5).b;
float vein = (1.0 - smoothstep(0.0, 0.022, abs(vn - 0.5))) * (1.0 - smoothstep(0.015, 0.05, fwidth(vn)));
vein *= smoothstep(0.3, 0.55, texture(uNoise, rp * 2.3 + 0.2).g);
skinCol = mix(skinCol, skinCol * vec3(0.76, 0.85, 0.96), vein * veinMask * uVeins * 0.9);
// sardas (mais nos ombros e na parte de cima)
if (uFreckles > 0.001) {
  float sun = smoothstep(-0.05, 0.38, rp.y) * 0.85 + 0.15;
  float fr = freckleSpots(rp * 230.0, 0.55 * uFreckles * sun);
  skinCol = mix(skinCol, vec3(0.50, 0.30, 0.20) * dot(skinCol, vec3(0.45)) * 1.6, fr * 0.65 * min(uFreckles * 1.4, 1.0));
}
// pintas (posições fixas, ancoradas em aRest)
for (int i = 0; i < ${MOLE_N}; i++) {
  vec4 m = uMole[i];
  if (m.w <= 0.0) continue;
  float d = length(rp - m.xyz);
  skinCol = mix(skinCol, vec3(0.20, 0.11, 0.08) * (0.6 + 0.4 * dot(uTone, vec3(0.33))), (1.0 - smoothstep(m.w * 0.55, m.w, d)) * uMoles);
}
// poros: pequenas cavidades escurecem levemente a cor
float pit = 1.0 - smoothstep(0.30, 0.52, nA.r);
skinCol *= 1.0 - pit * 0.07 * uPores;
// esmalte nos dedos dos pés
gNail = 0.0;
for (int i = 0; i < ${NAIL_N}; i++) {
  vec4 n = uNail[i];
  if (n.w <= 0.0) continue;
  vec3 d = rp - n.xyz;
  d.z *= 0.8;
  gNail = max(gNail, 1.0 - smoothstep(n.w * 0.72, n.w, length(d)));
}
skinCol = mix(skinCol, uNailColor, gNail * uNails);
gNail *= uNails;
// anatomia e cavidade da malha: sombra suave e mais quente em vãos, cristas levemente mais claras
anatomyField(rp);
float cavG = clamp(vCav * uCavGain, -0.5, 1.0);
float cavT = clamp(gAnatCav + max(cavG, 0.0) * 0.7, 0.0, 1.0) * clamp(uAnatK.x * 1.2, 0.0, 1.0);
skinCol *= 1.0 - cavT * 0.38;
skinCol = mix(skinCol, skinCol * vec3(1.07, 0.84, 0.80), cavT * 0.5);
skinCol *= 1.0 + min(cavG, 0.0) * -0.08 * uAnatK.x;
gCavT = cavT;
diffuseColor.rgb = skinCol;
`;

const ROUGH = /* glsl */ `
roughnessFactor = clamp(0.60 - uOil * 0.30 + (nA.r - 0.5) * 0.10 + (nB.g - 0.5) * 0.07 + gCavT * 0.18 - gNail * 0.42, 0.1, 1.0);
`;

const NORMAL = /* glsl */ `
{
  // curvatura local para a LUT de SSS (1/mm)
  float curv = length(fwidth(nonPerturbedNormal)) / max(length(fwidth(-vViewPosition)), 1e-5);
  float cmm = clamp(curv * 0.001, 1.0 / 300.0, 1.0 / 3.0);
  gCurvY = (log(cmm) - log(1.0 / 300.0)) / (log(1.0 / 3.0) - log(1.0 / 300.0));
  // poros e relevo fino (desaparecem com a distância: sem serrilhado)
  float fwFine = length(fwidth(rp * 28.0));
  float fwMid = length(fwidth(rp * 7.0));
  float fadeFine = 1.0 - smoothstep(0.004, 0.012, fwFine);
  float fadeMid = 1.0 - smoothstep(0.02, 0.07, fwMid);
  float hPore = -(1.0 - smoothstep(0.28, 0.5, nA.r)) * 0.00016 * fadeFine + (nA2.r - 0.5) * 0.00006 * fadeFine;
  float hMid = (nB.r - 0.5) * 0.00032 * fadeMid;
  normal = skinBump(-vViewPosition, normal, (hPore + hMid) * uPores + gAnatH);
}
`;

const EMISSIVE = /* glsl */ `
if (uShimmer > 0.001) {
  vec3 gp = rp * 520.0;
  vec3 gc = floor(gp);
  float h = hash13(gc);
  float spark = step(0.965, h);
  float tw = pow(abs(sin(dot(normalize(normal), normalize(vViewPosition)) * 38.0 + h * 40.0)), 30.0);
  totalEmissiveRadiance += uShimmerColor * spark * tw * uShimmer * 2.2;
}
`;

export class SkinMaterial extends THREE.MeshPhysicalMaterial {
  constructor({ noise, lut }) {
    super({
      color: 0xffffff,
      roughness: 0.5,
      metalness: 0,
      clearcoat: 0.3,
      clearcoatRoughness: 0.35,
      sheen: 1,
      sheenRoughness: 0.55,
      sheenColor: new THREE.Color(0.9, 0.7, 0.6).multiplyScalar(0.2),
      specularIntensity: 1,
      ior: 1.4,
    });
    this.u = {
      uNoise: { value: noise },
      uSkinLUT: { value: lut },
      uTone: { value: new THREE.Color() },
      uUndertone: { value: 0.15 },
      uPores: { value: 0.55 },
      uMottle: { value: 0.5 },
      uFreckles: { value: 0 },
      uMoles: { value: 0.35 },
      uVeins: { value: 0.2 },
      uRedness: { value: 0.5 },
      uOil: { value: 0.25 },
      uSSS: { value: 0.85 },
      uShimmer: { value: 0 },
      uNails: { value: 0 },
      uAnat: { value: Array.from({ length: 44 }, () => new THREE.Vector3()) },
      uAnatK: { value: new THREE.Vector4(0.8, 1, 0.7, 0.8) },
      uAnatK2: { value: new THREE.Vector4(0.8, 0.6, 1, 0.3) },
      uLean: { value: 1 },
      uCavGain: { value: 1 / 0.0018 },
      uNailColor: { value: new THREE.Color() },
      uShimmerColor: { value: new THREE.Color() },
      uBlush: { value: Array.from({ length: BLUSH_N }, () => new THREE.Vector4(0, 0, 0, 0)) },
      uMole: { value: Array.from({ length: MOLE_N }, () => new THREE.Vector4(0, 0, 0, 0)) },
      uNail: { value: Array.from({ length: NAIL_N }, () => new THREE.Vector4(0, 0, 0, 0)) },
    };
    this.setSkin(defaultSkin());
  }

  customProgramCacheKey() {
    return 'skin-v3';
  }

  onBeforeCompile(shader) {
    Object.assign(shader.uniforms, this.u);
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\nattribute vec3 aRest;\nattribute float aCav;\nvarying vec3 vRest;\nvarying float vCav;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvRest = aRest;\nvCav = aCav;');
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', '#include <common>\n' + DECL)
      .replace('#include <lights_physical_pars_fragment>', '#include <lights_physical_pars_fragment>\n' + LIGHT_OVERRIDE)
      .replace('#include <map_fragment>', '#include <map_fragment>\n' + ALBEDO)
      .replace('#include <roughnessmap_fragment>', '#include <roughnessmap_fragment>\n' + ROUGH)
      .replace('#include <normal_fragment_maps>', '#include <normal_fragment_maps>\n' + NORMAL)
      .replace('#include <emissivemap_fragment>', '#include <emissivemap_fragment>\n' + EMISSIVE);
  }

  /** Aplica as configurações de pele (domain/skin.js). */
  setSkin(skin) {
    const e = effectiveSkin(skin);
    const u = this.u;
    u.uTone.value.set(e.tone || '#e6b196');
    u.uUndertone.value = e.undertone;
    u.uPores.value = e.pores;
    u.uMottle.value = e.mottling;
    u.uFreckles.value = e.freckles;
    u.uMoles.value = e.moles;
    u.uVeins.value = e.veins;
    u.uRedness.value = e.redness;
    u.uOil.value = e.oil;
    u.uSSS.value = e.sss;
    u.uShimmer.value = e.shimmer;
    u.uNails.value = e.nails;
    u.uAnatK.value.set(e.anatomy, e.anaCollar, e.anaAbs, e.anaHips);
    u.uAnatK2.value.x = e.anaBack;
    u.uAnatK2.value.y = e.anaRibs;
    u.uAnatK2.value.z = e.anaNavel;
    u.uNailColor.value.set(e.nailColor || '#d6336c');
    u.uShimmerColor.value.set(e.shimmerColor || '#fff1c9');
    this.sheenColor.set(0.95, 0.74, 0.64).multiplyScalar(0.55 * e.fuzz);
    this.clearcoat = 0.12 + 0.55 * e.oil;
    this.clearcoatRoughness = 0.42 - 0.22 * e.oil;
    this.skin = skin;
  }

  /** Marcas anatômicas (avatar/anatomy.js) em metros, no espaço de referência. */
  setAnatomy(points) {
    const arr = this.u.uAnat.value;
    for (let i = 0; i < arr.length; i++) arr[i].set(points[i * 3], points[i * 3 + 1], points[i * 3 + 2]);
  }

  /** Estado do corpo que modula a anatomia: tônus abdominal (0..1) e magreza (costelas aparecem mais). */
  setBodyState({ tone, lean }) {
    this.u.uAnatK2.value.w = Math.min(1, Math.max(0, tone));
    this.u.uLean.value = Math.min(1.4, Math.max(0.15, lean));
  }

  /** Pontos de vermelhidão e esmalte, no espaço de referência (estado neutro). */
  setLandmarks(ctx, skinSeedVertices) {
    const { ref, rig } = ctx;
    const blush = this.u.uBlush.value;
    let n = 0;
    const put = (x, y, z, r) => {
      if (n < BLUSH_N) blush[n++].set(x, y, z, r);
    };
    for (const s of ['L', 'R']) {
      const knee = ref.heads[rig.index.get(`lowerleg01.${s}`)];
      put(knee.x, knee.y, knee.z + 0.05, 0.05); // joelho (frente)
      const ankle = ref.heads[rig.index.get(`foot.${s}`)];
      put(ankle.x + (s === 'L' ? 0.03 : -0.03), ankle.y, ankle.z, 0.028);
      put(ankle.x - (s === 'L' ? 0.03 : -0.03), ankle.y, ankle.z, 0.028);
      put(ankle.x, ankle.y - 0.035, ankle.z - 0.05, 0.04); // calcanhar
    }
    // dedos: ponta das falanges distais
    const tips = [];
    for (const s of ['L', 'R']) {
      for (let t = 1; t <= 5; t++) {
        let last = null;
        for (let k = 1; k <= 4; k++) {
          const name = `toe${t}-${k}.${s}`;
          if (rig.index.has(name)) last = name;
        }
        if (!last) continue;
        const tail = ref.tails[rig.index.get(last)];
        tips.push(tail);
        put(tail.x, tail.y, tail.z, 0.016);
      }
    }
    const nail = this.u.uNail.value;
    tips.slice(0, NAIL_N).forEach((t, i) => nail[i].set(t.x, t.y + 0.003, t.z - 0.004, t.x ? 0.0058 : 0.0058));
    if (skinSeedVertices) this.setMoles(ctx, skinSeedVertices);
  }

  /** Pintas: posições aleatórias (semente fixa) sobre a superfície de referência. */
  setMoles(ctx, seed = 7) {
    const { ref, N } = ctx;
    let s = seed >>> 0 || 1;
    const rnd = () => {
      s ^= s << 13; s >>>= 0;
      s ^= s >>> 17;
      s ^= s << 5; s >>>= 0;
      return s / 4294967296;
    };
    const arr = this.u.uMole.value;
    for (let i = 0; i < MOLE_N; i++) {
      for (let tries = 0; tries < 50; tries++) {
        const v = Math.floor(rnd() * N);
        const y = ref.pos[v * 3 + 1];
        if (y < -0.7) continue; // evita os pés
        arr[i].set(ref.pos[v * 3], y, ref.pos[v * 3 + 2], 0.0016 + rnd() * 0.0022);
        break;
      }
    }
  }
}
