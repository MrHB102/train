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
    m = max(m, smoothstep(r, r * 0.35, d));
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
// veias (linhas azul-esverdeadas sutis, mais nas pernas/pés)
float veinMask = smoothstep(0.1, -0.35, rp.y) * 0.8 + 0.2;
float vein = smoothstep(0.80, 0.95, texture(uNoise, rp * 11.0 + 0.5).b);
skinCol = mix(skinCol, skinCol * vec3(0.80, 0.88, 0.96), vein * veinMask * uVeins * 0.55);
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
  skinCol = mix(skinCol, vec3(0.20, 0.11, 0.08) * (0.6 + 0.4 * dot(uTone, vec3(0.33))), smoothstep(m.w, m.w * 0.55, d) * uMoles);
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
  gNail = max(gNail, smoothstep(n.w, n.w * 0.72, length(d)));
}
skinCol = mix(skinCol, uNailColor, gNail * uNails);
gNail *= uNails;
diffuseColor.rgb = skinCol;
`;

const ROUGH = /* glsl */ `
roughnessFactor = clamp(0.54 - uOil * 0.27 + (nA.r - 0.5) * 0.10 + (nB.g - 0.5) * 0.07 - gNail * 0.38, 0.1, 1.0);
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
  normal = skinBump(-vViewPosition, normal, (hPore + hMid) * uPores);
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
      uNailColor: { value: new THREE.Color() },
      uShimmerColor: { value: new THREE.Color() },
      uBlush: { value: Array.from({ length: BLUSH_N }, () => new THREE.Vector4(0, 0, 0, 0)) },
      uMole: { value: Array.from({ length: MOLE_N }, () => new THREE.Vector4(0, 0, 0, 0)) },
      uNail: { value: Array.from({ length: NAIL_N }, () => new THREE.Vector4(0, 0, 0, 0)) },
    };
    this.setSkin(defaultSkin());
  }

  customProgramCacheKey() {
    return 'skin-v1';
  }

  onBeforeCompile(shader) {
    Object.assign(shader.uniforms, this.u);
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\nattribute vec3 aRest;\nvarying vec3 vRest;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvRest = aRest;');
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
    u.uNailColor.value.set(e.nailColor || '#d6336c');
    u.uShimmerColor.value.set(e.shimmerColor || '#fff1c9');
    this.sheenColor.set(0.95, 0.74, 0.64).multiplyScalar(0.55 * e.fuzz);
    this.clearcoat = 0.12 + 0.55 * e.oil;
    this.clearcoatRoughness = 0.42 - 0.22 * e.oil;
    this.skin = skin;
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
