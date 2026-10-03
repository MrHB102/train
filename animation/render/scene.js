// Offline 3D renderer for the R6 fight. Pure function of (shot.json, frame): no state between frames,
// so any frame can be rendered in any order / in parallel. Pose data comes from the Python authoring
// side (r6.fk); this file only draws.
import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';

const SRGB = THREE.SRGBColorSpace;
const PARTS = ['Torso', 'Head', 'Left Arm', 'Right Arm', 'Left Leg', 'Right Leg'];
const SIZE = { 'Torso': [2, 2, 1], 'Head': [1.25, 1.25, 1.25], 'Left Arm': [1, 2, 1], 'Right Arm': [1, 2, 1], 'Left Leg': [1, 2, 1], 'Right Leg': [1, 2, 1] };

// ---------------------------------------------------------------- small helpers
function mulberry32(a) { return function () { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
const lerp = (a, b, t) => a + (b - a) * t;
const clamp01 = x => Math.max(0, Math.min(1, x));
const easeOut = t => 1 - Math.pow(1 - t, 3);
const easeIn = t => t * t;

function paint(w, h, fn) {
  const c = document.createElement('canvas'); c.width = w; c.height = h;
  const g = c.getContext('2d'); fn(g, w, h);
  const t = new THREE.CanvasTexture(c); t.colorSpace = SRGB; t.anisotropy = 8; t.generateMipmaps = true;
  t.minFilter = THREE.LinearMipmapLinearFilter; t.magFilter = THREE.LinearFilter;
  return t;
}
function rr(g, x, y, w, h, r) {
  g.beginPath(); g.moveTo(x + r, y); g.arcTo(x + w, y, x + w, y + h, r); g.arcTo(x + w, y + h, x, y + h, r);
  g.arcTo(x, y + h, x, y, r); g.arcTo(x, y, x + w, y, r); g.closePath();
}
function poly(g, pts) { g.beginPath(); pts.forEach(([x, y], i) => i ? g.lineTo(x, y) : g.moveTo(x, y)); g.closePath(); }
function shade(g, w, h, top = 0.10, bottom = 0.22) { // soft vertical form shading baked on every limb face
  const gr = g.createLinearGradient(0, 0, 0, h); gr.addColorStop(0, `rgba(255,255,255,${top})`); gr.addColorStop(1, `rgba(0,0,0,${bottom})`);
  g.fillStyle = gr; g.fillRect(0, 0, w, h);
}
function grain(g, w, h, amt = 0.04, seed = 3) {
  const r = mulberry32(seed); const im = g.getImageData(0, 0, w, h); const d = im.data;
  for (let i = 0; i < d.length; i += 4) { const n = (r() - 0.5) * 255 * amt; d[i] += n; d[i + 1] += n; d[i + 2] += n; }
  g.putImageData(im, 0, 0);
}
const mat = (map, extra = {}) => new THREE.MeshStandardMaterial({ map, roughness: 0.62, metalness: 0.0, ...extra });

// ---------------------------------------------------------------- avatars: plain Roblox R6 looks (no custom skin)
const INK = '#14161c';
const LOOKS = {
  // classic default Roblox avatar: yellow head/arms, blue torso, green legs, smiley face
  player: { head: '#f5cd30', torso: '#0d69ac', arm: '#f5cd30', leg: '#4b974b', face: '#f5cd30' },
  // Studio-style test dummy: plain grey blocks
  dummy: { head: '#a3a2a5', torso: '#a3a2a5', arm: '#a3a2a5', leg: '#8f8e92', face: '#a3a2a5' },
};
function faceTexture(base, hurt) {
  return paint(512, 512, (g, w, h) => {
    g.fillStyle = base; g.fillRect(0, 0, w, h);
    const sh = g.createRadialGradient(w * .5, h * .42, 40, w * .5, h * .5, w * .75); sh.addColorStop(0, 'rgba(255,255,255,0.16)'); sh.addColorStop(1, 'rgba(60,40,0,0.26)');
    g.fillStyle = sh; g.fillRect(0, 0, w, h);
    g.strokeStyle = INK; g.fillStyle = INK; g.lineCap = 'round';
    if (!hurt) {   // default Roblox smile
      g.beginPath(); g.ellipse(176, 238, 22, 34, 0, 0, 7); g.fill(); g.beginPath(); g.ellipse(336, 238, 22, 34, 0, 0, 7); g.fill();
      g.lineWidth = 16; g.beginPath(); g.moveTo(150, 330); g.quadraticCurveTo(256, 430, 362, 330); g.stroke();
    } else {       // knocked-silly face: X eyes, open mouth
      g.lineWidth = 18;
      for (const cx of [170, 342]) { g.beginPath(); g.moveTo(cx - 34, 206); g.lineTo(cx + 34, 272); g.moveTo(cx + 34, 206); g.lineTo(cx - 34, 272); g.stroke(); }
      g.beginPath(); g.ellipse(256, 372, 52, 40, 0, 0, 7); g.fill();
      g.fillStyle = '#c0392b'; g.beginPath(); g.ellipse(256, 386, 34, 20, 0, 0, 7); g.fill();
    }
  });
}
function solid(color) {
  return paint(64, 64, (g, w, h) => { g.fillStyle = color; g.fillRect(0, 0, w, h); shade(g, w, h, .07, .18); });
}

// ---------------------------------------------------------------- characters
function buildCharacter(kind) {
  const L = LOOKS[kind]; const root = new THREE.Group(); const parts = {};
  const solidMat = c => mat(solid(c));
  for (const b of PARTS) {
    const [sx, sy, sz] = SIZE[b];
    let geo, mats;
    if (b === 'Head') {
      geo = new RoundedBoxGeometry(sx, sy, sz, 5, 0.26);
      const sk = solidMat(L.head);
      mats = [sk, sk, sk, sk, sk, mat(faceTexture(L.face, false))];
    } else {
      geo = new RoundedBoxGeometry(sx, sy, sz, 3, 0.07);
      const c = b === 'Torso' ? L.torso : (b.endsWith('Arm') ? L.arm : L.leg); const m = solidMat(c);
      mats = [m, m, m, m, m, m];
    }
    const m = new THREE.Mesh(geo, mats); m.castShadow = true; m.receiveShadow = true; m.matrixAutoUpdate = false; m.name = b;
    root.add(m); parts[b] = m;
  }
  const ch = { kind, root, parts, extras: {} };
  if (kind === 'dummy') { ch.faceNormal = parts.Head.material[5]; ch.faceHurt = mat(faceTexture(L.face, true)); }
  return ch;
}

// ---------------------------------------------------------------- environment
function floorTexture() {
  return paint(2048, 2048, (g, w, h) => {
    const n = 6, tw = w / n, r = mulberry32(11);
    g.fillStyle = '#0f1620'; g.fillRect(0, 0, w, h);
    for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
      const v = r(); const base = 38 + v * 26; const tint = r() < 0.18 ? 14 : 0;
      const gr = g.createLinearGradient(x * tw, y * tw, (x + 1) * tw, (y + 1) * tw);
      gr.addColorStop(0, `rgb(${base * 0.8 + tint},${base * 1.05 + tint},${base * 1.5 + tint})`);
      gr.addColorStop(1, `rgb(${base * 0.62 + tint},${base * 0.84 + tint},${base * 1.25 + tint})`);
      g.fillStyle = gr; rr(g, x * tw + 7, y * tw + 7, tw - 14, tw - 14, 10); g.fill();
      g.strokeStyle = 'rgba(160,200,255,.10)'; g.lineWidth = 3; rr(g, x * tw + 12, y * tw + 12, tw - 24, tw - 24, 8); g.stroke();
    }
    grain(g, w, h, .035, 9);
  });
}
function skyMaterial(sunDir) {
  return new THREE.ShaderMaterial({
    side: THREE.BackSide, depthWrite: false, fog: false,
    uniforms: { sunDir: { value: sunDir.clone() } },
    vertexShader: `varying vec3 vDir; void main(){ vDir = position; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`,
    fragmentShader: `
      varying vec3 vDir; uniform vec3 sunDir;
      float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1,311.7))) * 43758.5453); }
      float noise(vec2 p){ vec2 i=floor(p), f=fract(p); f=f*f*(3.0-2.0*f);
        return mix(mix(hash(i),hash(i+vec2(1,0)),f.x), mix(hash(i+vec2(0,1)),hash(i+vec2(1,1)),f.x), f.y); }
      float fbm(vec2 p){ float a=.5, s=0.; for(int i=0;i<5;i++){ s+=a*noise(p); p*=2.03; a*=.5; } return s; }
      void main(){
        vec3 d = normalize(vDir);
        float h = clamp(d.y, -0.3, 1.0);
        vec3 zenith = vec3(0.07,0.24,0.66), mid = vec3(0.24,0.52,0.90), horizon = vec3(0.62,0.78,0.95);
        vec3 col = mix(horizon, mid, smoothstep(0.0, 0.28, h)); col = mix(col, zenith, smoothstep(0.25, 0.95, h));
        vec2 uv = d.xz / (d.y + 0.32) * 1.4;
        float n = fbm(uv * 1.15 + vec2(3.1, 1.7)); float c = smoothstep(0.50, 0.82, n) * smoothstep(0.02, 0.22, d.y);
        float lit = clamp(0.55 + 0.45 * dot(normalize(vec3(d.x,0.6,d.z)), normalize(vec3(sunDir.x,0.6,sunDir.z))), 0.0, 1.0);
        col = mix(col, mix(vec3(0.72,0.78,0.88), vec3(1.0), lit), c * 0.85);
        float s = max(dot(d, sunDir), 0.0);
        col += vec3(1.0,0.93,0.78) * (pow(s, 900.0) * 6.0 + pow(s, 40.0) * 0.55 + pow(s, 6.0) * 0.16);
        col = mix(col, horizon * 0.92, smoothstep(0.0, -0.15, d.y));
        gl_FragColor = vec4(col, 1.0);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
  });
}
function softDisc() {
  return paint(128, 128, (g, w, h) => { const gr = g.createRadialGradient(64, 64, 0, 64, 64, 64); gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(.45, 'rgba(255,255,255,.55)'); gr.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = gr; g.fillRect(0, 0, w, h); });
}
function glowTex() {   // hot core + wide soft halo + faint 4-point star
  return paint(256, 256, (g, w, h) => {
    const c = w / 2; let gr = g.createRadialGradient(c, c, 0, c, c, c);
    gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.08, 'rgba(255,255,255,0.95)'); gr.addColorStop(0.25, 'rgba(255,255,255,0.35)'); gr.addColorStop(0.6, 'rgba(255,255,255,0.08)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
    g.fillStyle = gr; g.fillRect(0, 0, w, h);
    g.globalCompositeOperation = 'lighter';
    for (const [sx, sy] of [[1, 0.035], [0.035, 1]]) { gr = g.createRadialGradient(c, c, 0, c, c, c); gr.addColorStop(0, 'rgba(255,255,255,0.7)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
      g.save(); g.translate(c, c); g.scale(sx, sy); g.fillStyle = gr; g.beginPath(); g.arc(0, 0, c, 0, 7); g.fill(); g.restore(); }
  });
}
function puffTex(seed) {  // soft billowy smoke puff (fbm-modulated disc)
  return paint(256, 256, (g, w, h) => {
    const r = mulberry32(seed); const im = g.createImageData(w, h); const d = im.data;
    const oct = [[4, 0.5], [8, 0.27], [16, 0.15], [32, 0.08]].map(([f, a]) => ({ f, a, ph: Array.from({ length: 6 }, () => r() * 6.28) }));
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const u = x / w - 0.5, v = y / h - 0.5; const rad = Math.sqrt(u * u + v * v) * 2;
      let n = 0; for (const o of oct) n += o.a * (0.5 + 0.25 * Math.sin(u * o.f * 6.28 + o.ph[0] + Math.sin(v * o.f * 3.1 + o.ph[1])) + 0.25 * Math.sin(v * o.f * 6.28 + o.ph[2] + Math.sin(u * o.f * 2.7 + o.ph[3])));
      const a = Math.max(0, Math.min(1, (1 - rad * (1.05 - 0.35 * n)) * 1.6)) * (0.55 + 0.45 * n);
      const i = (y * w + x) * 4; const sh = 0.82 + 0.18 * (0.5 - v); d[i] = 255 * sh; d[i + 1] = 255 * sh; d[i + 2] = 255 * sh; d[i + 3] = 255 * a * a * (3 - 2 * a);
    }
    g.putImageData(im, 0, 0);
  });
}
function streakTex() {
  return paint(256, 32, (g, w, h) => { const gr = g.createLinearGradient(0, 0, w, 0); gr.addColorStop(0, 'rgba(255,255,255,0)'); gr.addColorStop(.7, 'rgba(255,255,255,.9)'); gr.addColorStop(1, 'rgba(255,255,255,1)'); g.fillStyle = gr; g.fillRect(0, 0, w, h);
    const v = g.createLinearGradient(0, 0, 0, h); v.addColorStop(0, 'rgba(0,0,0,1)'); v.addColorStop(.5, 'rgba(0,0,0,0)'); v.addColorStop(1, 'rgba(0,0,0,1)'); g.globalCompositeOperation = 'destination-out'; g.fillStyle = v; g.fillRect(0, 0, w, h); });
}
function wallTex() {
  return paint(8, 128, (g, w, h) => { const gr = g.createLinearGradient(0, h, 0, 0); gr.addColorStop(0, 'rgba(255,255,255,.95)'); gr.addColorStop(.35, 'rgba(255,255,255,.35)'); gr.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = gr; g.fillRect(0, 0, w, h); });
}
function crackTex(seed) {
  return paint(512, 512, (g, w, h) => {
    const r = mulberry32(seed); g.translate(256, 256); g.lineCap = 'round';
    const branch = (x, y, a, len, wd, depth) => {
      const segs = 5 + (r() * 3 | 0); let px = x, py = y;
      for (let i = 0; i < segs; i++) {
        a += (r() - 0.5) * 0.7; const l = len / segs * (0.7 + r() * 0.6); const nx = px + Math.cos(a) * l, ny = py + Math.sin(a) * l;
        g.strokeStyle = 'rgba(190,225,255,.55)'; g.lineWidth = wd + 5; g.beginPath(); g.moveTo(px, py); g.lineTo(nx, ny); g.stroke();
        g.strokeStyle = 'rgba(4,6,10,.96)'; g.lineWidth = wd; g.beginPath(); g.moveTo(px, py); g.lineTo(nx, ny); g.stroke();
        if (depth < 2 && r() < 0.45) branch(nx, ny, a + (r() < .5 ? 1 : -1) * (0.5 + r() * 0.7), len * 0.45, wd * 0.6, depth + 1);
        px = nx; py = ny; wd *= 0.86;
      }
    };
    const n = 7 + (r() * 4 | 0);
    for (let i = 0; i < n; i++) branch(0, 0, i / n * Math.PI * 2 + r() * 0.5, 120 + r() * 120, 9, 0);
    const gr = g.createRadialGradient(0, 0, 0, 0, 0, 36); gr.addColorStop(0, 'rgba(4,6,10,.9)'); gr.addColorStop(1, 'rgba(4,6,10,0)'); g.fillStyle = gr; g.fillRect(-256, -256, 512, 512);
  });
}
function nameTagTexture(text) {
  return paint(512, 128, (g, w, h) => {
    g.font = '800 64px "Arial Black", Arial, sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle';
    g.lineJoin = 'round'; g.lineWidth = 14; g.strokeStyle = 'rgba(0,0,0,.92)'; g.strokeText(text, w / 2, h / 2 + 2);
    g.fillStyle = '#fff'; g.fillText(text, w / 2, h / 2 + 2);
  });
}

// pooled objects (reset every frame; all effect visuals are pure functions of (event, frame))
class Pool {
  constructor(scene, make) { this.scene = scene; this.make = make; this.items = []; this.used = 0; }
  get() { if (this.used >= this.items.length) { const o = this.make(); this.scene.add(o); this.items.push(o); } const o = this.items[this.used++]; o.visible = true; return o; }
  reset() { for (let i = 0; i < this.used; i++) this.items[i].visible = false; this.used = 0; }
}

export class Stage {
  constructor(shot, opts) {
    this.shot = shot; this.frames = shot.frames;
    // v2 timeline: output frames (shot.fps, e.g. 120) show story frame tau[n] (18 fps authoring grid). v1 shots: tau = n.
    this.tau = shot.tau || null; this.storyFps = shot.story_fps || shot.fps; this.BASE = shot.fps / this.storyFps;
    const scale = opts.scale || 1; this.W = Math.round(shot.width * scale); this.H = Math.round(shot.height * scale);
    const r = this.renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true, powerPreference: 'high-performance' });
    r.setPixelRatio(1); r.setSize(this.W, this.H); r.outputColorSpace = SRGB;
    r.toneMapping = THREE.ACESFilmicToneMapping; r.toneMappingExposure = opts.exposure || 1.0;
    r.shadowMap.enabled = true; r.shadowMap.type = THREE.PCFShadowMap;
    document.body.appendChild(r.domElement);
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(60, this.W / this.H, 0.1, 2000);
    this.sunDir = new THREE.Vector3(-0.45, 0.62, -0.65).normalize();
    this.horizon = new THREE.Color(0.62, 0.78, 0.95);
    this.scene.fog = new THREE.FogExp2(this.horizon.clone().multiplyScalar(0.86), 0.0075);
    this.buildEnvironment(); this.buildLights();
    this.chars = {};
    for (const id of Object.keys(shot.chars)) {
      const c = buildCharacter(shot.chars[id].kind); this.chars[id] = c; this.scene.add(c.root);
    }
    this.buildFxPools();
    this.tag = {};
    for (const id of Object.keys(shot.tags || {})) {
      const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: nameTagTexture(shot.tags[id].text), transparent: true, depthWrite: false, depthTest: false, fog: false }));
      sp.renderOrder = 50; this.scene.add(sp); this.tag[id] = sp;
    }
    this.fx = (shot.fx || []).slice().sort((a, b) => a.f0 - b.f0);
  }

  buildEnvironment() {
    const s = this.scene;
    const sky = new THREE.Mesh(new THREE.SphereGeometry(900, 48, 24), skyMaterial(this.sunDir)); sky.renderOrder = -10; s.add(sky); this.sky = sky;
    const ft = floorTexture(); ft.wrapS = ft.wrapT = THREE.RepeatWrapping; ft.repeat.set(30, 30); ft.anisotropy = 16;
    const floor = new THREE.Mesh(new THREE.PlaneGeometry(1000, 1000), new THREE.MeshStandardMaterial({ map: ft, roughness: 0.6, metalness: 0.0, envMapIntensity: 0 }));
    floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; s.add(floor); this.floor = floor;
    // distant set pieces for parallax / depth (billboards and blocks, like a Roblox test place)
    const bm = new THREE.MeshStandardMaterial({ color: 0xdfe8f3, roughness: 0.9 }); const dk = new THREE.MeshStandardMaterial({ color: 0x1b2433, roughness: 0.7 });
    const blocks = [[-70, -120, 40, 26, 6], [-30, -160, 56, 40, 6], [60, -140, 30, 60, 8], [110, -90, 24, 34, 6], [-120, -60, 20, 30, 20], [150, -170, 70, 50, 10], [10, -210, 90, 30, 12]];
    for (const [x, z, w, h, d] of blocks) {
      const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), (x + z) % 2 ? bm : dk); m.position.set(x, h / 2, z); m.castShadow = false; s.add(m);
    }
    // arena platform rim: glowing edge lines make the playable area readable
    const rim = new THREE.Mesh(new THREE.RingGeometry(34, 34.6, 96), new THREE.MeshBasicMaterial({ color: 0x9fd2ff, transparent: true, opacity: 0.55, fog: true }));
    rim.rotation.x = -Math.PI / 2; rim.position.y = 0.02; s.add(rim);
  }

  buildLights() {
    const s = this.scene;
    this.keyDir = new THREE.Vector3(-0.55, 0.78, 0.62).normalize();
    this.sun = new THREE.DirectionalLight(0xfff1dc, 3.0); this.sun.castShadow = true;
    const sc = this.sun.shadow; sc.mapSize.set(2048, 2048); const E = 17;
    sc.camera.left = -E; sc.camera.right = E; sc.camera.top = E; sc.camera.bottom = -E; sc.camera.near = 1; sc.camera.far = 90; sc.bias = -0.0004; sc.normalBias = 0.03; sc.radius = 4;
    s.add(this.sun); s.add(this.sun.target);
    s.add(new THREE.HemisphereLight(0xbcd8ff, 0x3b4658, 1.15));
    this.back = new THREE.DirectionalLight(0xffe2b8, 1.7); s.add(this.back); s.add(this.back.target);          // warm back-light = the sky's sun
    this.rim = new THREE.DirectionalLight(0x9ec6ff, 0.7); s.add(this.rim); s.add(this.rim.target);              // cool camera-side fill
  }

  buildFxPools() {
    const s = this.scene; const disc = softDisc(); this.tex = { disc, streak: streakTex(), wall: wallTex(), cracks: [crackTex(5), crackTex(17), crackTex(29), crackTex(41)], glow: glowTex(), puffs: [puffTex(3), puffTex(9), puffTex(21)] };
    const boxG = new THREE.BoxGeometry(1, 1, 1);
    // after-image: flat inner tint + bright fresnel rim (reads as light, not as a grey copy)
    const rimVS = 'varying vec3 vN; varying vec3 vV; varying vec3 vW; void main(){ vec4 w = modelMatrix * vec4(position,1.0); vW = w.xyz; vN = normalize(mat3(modelMatrix) * normal); vV = normalize(cameraPosition - w.xyz); gl_Position = projectionMatrix * viewMatrix * w; }';
    this.ghostPool = new Pool(s, () => {
      const g = new THREE.Group(); const m = new THREE.ShaderMaterial({ transparent: true, depthWrite: false, fog: false, blending: THREE.AdditiveBlending,
        uniforms: { col: { value: new THREE.Color(1, 1, 1) }, alpha: { value: 0.5 } }, vertexShader: rimVS,
        fragmentShader: 'uniform vec3 col; uniform float alpha; varying vec3 vN; varying vec3 vV; void main(){ float fr = pow(1.0 - abs(dot(normalize(vN), normalize(vV))), 2.2); gl_FragColor = vec4(col * (0.35 + 1.4 * fr), alpha * (0.45 + 0.9 * fr)); }' });
      g.userData.mat = m; g.userData.parts = {};
      for (const b of PARTS) { const mesh = new THREE.Mesh(boxG, m); mesh.matrixAutoUpdate = false; mesh.renderOrder = 20; g.add(mesh); g.userData.parts[b] = mesh; }
      return g;
    });
    this.ringPool = new Pool(s, () => { const m = new THREE.Mesh(new THREE.RingGeometry(0.86, 1, 72), new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.8, side: THREE.DoubleSide, depthWrite: false, blending: THREE.AdditiveBlending, fog: false })); m.renderOrder = 21; return m; });
    this.wallPool = new Pool(s, () => { const m = new THREE.Mesh(new THREE.CylinderGeometry(1, 1, 1, 56, 1, true), new THREE.MeshBasicMaterial({ map: this.tex.wall, color: 0xffffff, transparent: true, opacity: 0.8, side: THREE.DoubleSide, depthWrite: false, blending: THREE.AdditiveBlending, fog: false })); m.geometry.translate(0, 0.5, 0); m.renderOrder = 21; return m; });
    this.crackPool = new Pool(s, () => { const m = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ transparent: true, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -4, polygonOffsetUnits: -4, fog: true })); m.rotation.x = -Math.PI / 2; m.renderOrder = 5; return m; });
    this.dustPool = new Pool(s, () => { const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: disc, transparent: true, depthWrite: false, fog: true })); sp.renderOrder = 22; return sp; });
    this.debrisPool = new Pool(s, () => {
      const m = new THREE.Mesh(boxG, new THREE.MeshStandardMaterial({ color: 0xf2f4f8, roughness: 0.85 })); m.castShadow = true;
      const o = new THREE.Mesh(boxG, new THREE.MeshBasicMaterial({ color: 0x050608, side: THREE.BackSide })); o.scale.setScalar(1.14); m.add(o); return m;
    });
    this.slashPool = new Pool(s, () => new THREE.Mesh(new THREE.PlaneGeometry(2, 2), new THREE.ShaderMaterial({
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide, fog: false,
      uniforms: { a0: { value: 0 }, a1: { value: 1 }, rin: { value: 0.7 }, th: { value: 0.3 }, col: { value: new THREE.Color(1, 1, 1) }, alpha: { value: 1 } },
      vertexShader: 'varying vec2 vUv; void main(){ vUv = uv * 2.0 - 1.0; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }',
      fragmentShader: `varying vec2 vUv; uniform float a0,a1,rin,th,alpha; uniform vec3 col;
        void main(){ float rho = length(vUv); float ang = atan(vUv.y, vUv.x); float t = (ang - a0) / (a1 - a0);
          if (t < 0.0 || t > 1.0) discard; float taper = sin(3.14159 * pow(t, 0.7)); float outer = rin + th * taper; float inner = rin - th * 0.12 * taper;
          float m = smoothstep(inner, inner + 0.02, rho) * (1.0 - smoothstep(outer - 0.03, outer, rho)); float core = smoothstep(rin, outer, rho) * 0.0;
          float glow = (0.35 + 0.65 * t) * m; if (m <= 0.001) discard; gl_FragColor = vec4(col * (0.8 + 0.8 * t), glow * alpha); }`,
    })));
    this.streakPool = new Pool(s, () => new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ map: this.tex.streak, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide, fog: false })));
    // energy aura: back-face shell with upward-flowing flame noise and a hot rim
    this.auraPool = new Pool(s, () => {
      const g = new THREE.Group(); const m = new THREE.ShaderMaterial({ transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.BackSide, fog: false,
        uniforms: { col: { value: new THREE.Color(1, 0.3, 0.3) }, alpha: { value: 0.4 }, time: { value: 0 } }, vertexShader: rimVS,
        fragmentShader: `uniform vec3 col; uniform float alpha, time; varying vec3 vN; varying vec3 vV; varying vec3 vW;
          float h(vec3 p){ return fract(sin(dot(p, vec3(127.1, 311.7, 74.7))) * 43758.5453); }
          float n3(vec3 p){ vec3 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
            return mix(mix(mix(h(i), h(i + vec3(1,0,0)), f.x), mix(h(i + vec3(0,1,0)), h(i + vec3(1,1,0)), f.x), f.y),
                       mix(mix(h(i + vec3(0,0,1)), h(i + vec3(1,0,1)), f.x), mix(h(i + vec3(0,1,1)), h(i + vec3(1,1,1)), f.x), f.y), f.z); }
          void main(){ vec3 p = vW * 1.7 - vec3(0.0, time * 3.2, 0.0); float n = n3(p) * 0.6 + n3(p * 2.1) * 0.3 + n3(p * 4.3) * 0.1;
            float fr = pow(1.0 - abs(dot(normalize(vN), normalize(vV))), 1.6); float flame = smoothstep(0.35, 0.85, n);
            vec3 c = mix(col, vec3(1.0, 0.95, 0.85), flame * 0.55);
            gl_FragColor = vec4(c * (0.6 + 1.2 * flame), alpha * (0.25 + 0.85 * flame) * (0.55 + 0.6 * fr)); }` });
      g.userData.mat = m; g.userData.parts = {};
      for (const b of PARTS) { const mesh = new THREE.Mesh(boxG, m); mesh.matrixAutoUpdate = false; mesh.renderOrder = 19; g.add(mesh); g.userData.parts[b] = mesh; }
      return g;
    });
    this.pillarPool = new Pool(s, () => {
      const m = new THREE.Mesh(boxG, new THREE.MeshStandardMaterial({ color: 0x8e98ac, roughness: 0.92, flatShading: true })); m.castShadow = true; m.receiveShadow = true;
      const o = new THREE.Mesh(boxG, new THREE.MeshBasicMaterial({ color: 0x050608, side: THREE.BackSide })); o.scale.set(1.07, 1.02, 1.07); m.add(o);
      const cap = new THREE.Mesh(boxG, new THREE.MeshStandardMaterial({ color: 0xc9d2e4, roughness: 0.8 })); cap.scale.set(1.04, 0.05, 1.04); cap.position.y = 0.5; m.add(cap);
      return m;
    });
    // continuous limb trails: a camera-facing triangle strip with per-vertex alpha
    this.trailPool = new Pool(s, () => {
      const K = 18; const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.BufferAttribute(new Float32Array((K + 1) * 6), 3));
      g.setAttribute('alpha', new THREE.BufferAttribute(new Float32Array((K + 1) * 2), 1));
      const idx = []; for (let k = 0; k < K; k++) { const a = 2 * k; idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2); } g.setIndex(idx);
      const m = new THREE.Mesh(g, new THREE.ShaderMaterial({ transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide, fog: false,
        uniforms: { col: { value: new THREE.Color(1, 1, 1) } },
        vertexShader: 'attribute float alpha; varying float vA; void main(){ vA = alpha; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
        fragmentShader: 'uniform vec3 col; varying float vA; void main(){ gl_FragColor = vec4(col, vA); }' }));
      m.frustumCulled = false; m.renderOrder = 23; return m;
    });
    this.glowPool = new Pool(s, () => { const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: this.tex.glow, transparent: true, depthWrite: false, depthTest: false, blending: THREE.AdditiveBlending, fog: false })); sp.renderOrder = 30; return sp; });
    this.emberPool = new Pool(s, () => { const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: disc, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, fog: false })); sp.renderOrder = 24; return sp; });
    // flash lights for impacts: always present (fixed light count = no shader recompiles), intensity 0 when idle
    this.flashLights = [0, 1, 2].map(() => { const L = new THREE.PointLight(0xffffff, 0, 14, 2); s.add(L); return L; });
    this.pools = [this.pillarPool, this.ghostPool, this.ringPool, this.wallPool, this.crackPool, this.dustPool, this.debrisPool, this.slashPool, this.streakPool, this.auraPool, this.trailPool, this.glowPool, this.emberPool];
  }

  af2n(af) {
    const T = this.tau; const last = this.frames - 1;
    if (!T) return Math.max(0, Math.min(last, Math.round(af)));
    if (af <= T[0]) return 0; if (af >= T[last]) return last;
    let lo = 0, hi = last;
    while (hi - lo > 1) { const m = (lo + hi) >> 1; if (T[m] <= af) lo = m; else hi = m; }
    return (af - T[lo]) / Math.max(1e-9, T[hi] - T[lo]) < 0.5 ? lo : hi;
  }
  partPoint(cid, b, n, local) {
    const a = this.shot.chars[cid].parts[b][n];
    return new THREE.Vector3(a[0] + a[3] * local[0] + a[4] * local[1] + a[5] * local[2], a[1] + a[6] * local[0] + a[7] * local[1] + a[8] * local[2], a[2] + a[9] * local[0] + a[10] * local[1] + a[11] * local[2]);
  }

  setPartMatrices(meshes, data, f, scaleMul = 1, pad = 0) {
    for (const b of PARTS) {
      const a = data.parts[b][f]; const m = meshes[b];
      m.matrix.set(a[3], a[4], a[5], a[0], a[6], a[7], a[8], a[1], a[9], a[10], a[11], a[2], 0, 0, 0, 1);
      m.matrixWorldNeedsUpdate = true;
    }
  }
  applyChars(f) {
    for (const id of Object.keys(this.chars)) {
      const ch = this.chars[id], d = this.shot.chars[id];
      this.setPartMatrices(ch.parts, d, f);
      ch.root.visible = d.vis ? !!d.vis[f] : true;
      if (ch.faceHurt) { ch.parts.Head.material[5] = (d.hurt && d.hurt[f]) ? ch.faceHurt : ch.faceNormal; }
      if (ch.spikes && d.hair) {
        const lag = d.hair[f];
        ch.spikes.forEach((s, i) => { const l = lag[i] || [0, 0, 0]; const v = s.dir.clone().add(new THREE.Vector3(l[0], l[1], l[2])).normalize();
          s.m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), v); });
      }
    }
  }

  // ------------------------------------------------------------ FX
  applyFx(n, tau) {
    for (const p of this.pools) p.reset();
    this.lightUse = 0;
    for (const e of this.fx) {
      if (e.f0 > tau + 1e-6) break;
      // story-clock effects follow slow motion / hit-stops; real-clock ones (flashes, stars, sparks) always play at speed
      const f = e.clk === 'real' ? e.f0 + (n - e.n0) / this.BASE : tau;
      if (f < e.f0 - 1e-6) continue;
      const e1 = (e.f1 === undefined ? e.f0 : e.f1) + 1;          // continuous: an event lives on [f0, f1 + 1)
      if (f >= e1 && !(e.t === 'crack' && e.keep)) continue;
      const u = clamp01((f - e.f0) / (e1 - e.f0));
      const age = (f - e.f0) / this.storyFps;
      switch (e.t) {
        case 'ghost': this.fxGhost(e, f, u); break;
        case 'aura': this.fxAura(e, f, u, n); break;
        case 'trail': this.fxTrail(e, f, u); break;
        case 'glow': this.fxGlow(e, f, u); break;
        case 'sparks': this.fxSparks(e, f, age); break;
        case 'ring': this.fxRing(e, u); break;
        case 'wall': this.fxWall(e, u); break;
        case 'debris': this.fxDebris(e, f, age); break;
        case 'crack': this.fxCrack(e, f, u); break;
        case 'dust': this.fxDust(e, f, age, u); break;
        case 'slash': this.fxSlash(e, u); break;
        case 'streak': this.fxStreak(e, u); break;
        case 'pillar': this.fxPillar(e, f); break;
      }
    }
  }
  fxGhost(e, f, u) {
    const d = this.shot.chars[e.c];
    const c0 = new THREE.Color(e.col || '#9fd0ff'), c1 = new THREE.Color(e.col2 || '#b48cff');
    const lags = e.lags || [2, 4, 6];
    lags.forEach((lag, i) => {
      const ff = this.af2n(f - lag); const g = this.ghostPool.get(); const un = g.userData.mat.uniforms;
      un.col.value.copy(c0).lerp(c1, lags.length > 1 ? i / (lags.length - 1) : 0);
      un.alpha.value = 0.8 * (e.a ?? 0.5) * Math.pow(e.decay ?? 0.7, i) * (1 - (e.fade ? u * 0.65 : 0));
      this.setPartMatrices(g.userData.parts, d, ff);
      for (const b of PARTS) { const m = g.userData.parts[b]; const sz = SIZE[b]; m.matrix.scale(new THREE.Vector3(sz[0], sz[1], sz[2])); }
    });
  }
  fxAura(e, f, u, n) {
    const d = this.shot.chars[e.c]; const nn = this.af2n(f);
    const t = n / this.shot.fps;
    for (let layer = 0; layer < 2; layer++) {
      const g = this.auraPool.get(); const un = g.userData.mat.uniforms;
      un.col.value.set(e.col || '#ff4050'); un.time.value = t + layer * 3.1;
      un.alpha.value = (e.a ?? 0.5) * (layer ? 0.55 : 1.0) * (0.85 + 0.15 * Math.sin(t * 2 * Math.PI * 3.1)) * (e.ramp ? clamp01(u * 2) : 1);
      this.setPartMatrices(g.userData.parts, d, nn);
      const k = (e.scale || 1.22) * (layer ? 1.32 : 1.0);
      for (const b of PARTS) { const m = g.userData.parts[b]; const sz = SIZE[b]; m.matrix.scale(new THREE.Vector3(sz[0] * k, sz[1] * k, sz[2] * k)); }
    }
    // embers rising from the body
    const r = mulberry32((e.seed || 3) * 131); const torso = this.partPoint(e.c, 'Torso', nn, [0, 0, 0]);
    const nE = Math.round((e.embers ?? 26) * (e.ramp ? clamp01(u * 2) : 1));
    for (let i = 0; i < nE; i++) {
      const ph = r(), sp = 1.6 + r() * 2.2, ang = r() * 6.283, rad = 0.6 + r() * 1.3;
      const life = 0.7 + r() * 0.6; const a = ((t * (1 / life) + ph) % 1);
      const o = this.emberPool.get();
      o.position.set(torso.x + Math.cos(ang + a * 1.5) * rad * (1 - a * 0.4), torso.y - 2.6 + a * sp * 3.2, torso.z + Math.sin(ang + a * 1.5) * rad * (1 - a * 0.4));
      const sz = 0.11 + 0.1 * (1 - a); o.scale.set(sz, sz * 2.2, 1); o.material.rotation = 0;
      o.material.color.set(e.col || '#ff4050'); o.material.opacity = (e.a ?? 0.5) * 1.6 * Math.sin(Math.PI * a);
    }
  }
  fxTrail(e, f, u) {
    // continuous ribbon through the limb tip's recent path (story time), tapering and fading toward the tail
    const K = 18; const len = e.len ?? 1.6; const m = this.trailPool.get();
    const pos = m.geometry.attributes.position.array, al = m.geometry.attributes.alpha.array;
    const camPos = this.camera.position; const pts = [];
    for (let k = 0; k <= K; k++) { const n = this.af2n(f - len * k / K); pts.push(this.partPoint(e.c, e.part, n, e.tip || [0, -1, 0])); }
    let total = 0; for (let k = 1; k <= K; k++) total += pts[k].distanceTo(pts[k - 1]);
    const fadeIn = clamp01((f - e.f0) / 0.35), fadeOut = 1 - clamp01((u - 0.7) / 0.3);
    for (let k = 0; k <= K; k++) {
      const p = pts[k]; const q = pts[Math.min(K, k + 1)], r0 = pts[Math.max(0, k - 1)];
      const dir = new THREE.Vector3().subVectors(r0, q); if (dir.lengthSq() < 1e-8) dir.set(0, 1, 0); dir.normalize();
      const view = new THREE.Vector3().subVectors(camPos, p).normalize();
      const side = new THREE.Vector3().crossVectors(dir, view).normalize();
      const w = (e.w ?? 0.2) * (1 - k / K) * (total > 0.4 ? 1 : total / 0.4);
      pos.set([p.x + side.x * w, p.y + side.y * w, p.z + side.z * w, p.x - side.x * w, p.y - side.y * w, p.z - side.z * w], k * 6);
      const a = (e.a ?? 0.9) * Math.pow(1 - k / K, 1.4) * fadeIn * fadeOut * (total > 0.25 ? 1 : 0);
      al[k * 2] = a; al[k * 2 + 1] = a;
    }
    m.geometry.attributes.position.needsUpdate = true; m.geometry.attributes.alpha.needsUpdate = true; m.geometry.computeBoundingSphere();
    m.material.uniforms.col.value.set(e.col || '#ffffff');
  }
  fxGlow(e, f, u) {
    const o = this.glowPool.get(); const k = 1 - u;
    const I = (e.i ?? 1.0) * Math.pow(k, 3.0);
    o.position.set(...e.p); const r = (e.r ?? 1.5) * (0.45 + 0.4 * Math.sqrt(u)); o.scale.set(r * 2, r * 2, 1);
    o.material.color.set(e.col || '#fff2d6'); o.material.opacity = Math.min(1, I);
    if (e.light && this.lightUse < this.flashLights.length) {
      const L = this.flashLights[this.lightUse++]; L.position.set(...e.p); L.color.set(e.col || '#fff2d6'); L.intensity = e.light * I * 18; L.distance = 10;
    }
  }
  fxSparks(e, f, age) {
    const r = mulberry32((e.seed || 1) * 7907); const life = e.life ?? 0.38; if (age > life * 1.6) return;
    const d = new THREE.Vector3(...(e.dir || [0, 0, 0]));
    for (let i = 0; i < e.n; i++) {
      const v = new THREE.Vector3(r() * 2 - 1, r() * 2 - 1, r() * 2 - 1).normalize().multiplyScalar((e.speed ?? 18) * (0.35 + r() * 0.65)).addScaledVector(d, (e.speed ?? 18) * 0.6 * r());
      const li = life * (0.5 + r() * 0.7); if (age > li) continue;
      const drag = Math.exp(-age * 3.2); const t = (1 - drag) / 3.2;
      const p = new THREE.Vector3(...e.p).addScaledVector(v, t); p.y -= 0.5 * 26 * age * age;
      const vel = v.clone().multiplyScalar(drag); vel.y -= 26 * age;
      const m = this.streakPool.get(); const tail = p.clone().addScaledVector(vel, -0.028 - 0.02 * r());
      const axis = new THREE.Vector3().subVectors(p, tail); const ln = Math.max(axis.length(), 0.05); axis.normalize();
      const mid = p.clone().add(tail).multiplyScalar(0.5); const view = this.camera.position.clone().sub(mid).normalize();
      const side = new THREE.Vector3().crossVectors(axis, view).normalize(); const nrm = new THREE.Vector3().crossVectors(axis, side).normalize();
      m.matrix.makeBasis(axis.multiplyScalar(ln), side.multiplyScalar(0.05 + 0.04 * r()), nrm); m.matrix.setPosition(mid); m.matrixAutoUpdate = false; m.matrixWorldNeedsUpdate = true;
      m.material.color.set(r() < 0.35 ? (e.col2 || '#ffd27a') : (e.col || '#ffffff')); m.material.opacity = 1 - age / li;
    }
  }
  fxRing(e, u) {
    const m = this.ringPool.get(); const k = (e.ease === 'in' ? easeIn(u) : easeOut(u)); const r = lerp(e.r0, e.r1, k);
    m.position.set(...e.p); m.scale.set(r, r, r); const n = new THREE.Vector3(...(e.n || [0, 1, 0])).normalize();
    m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), n); m.material.color.set(e.col || '#ffffff'); m.material.opacity = lerp(e.a0 ?? 0.9, e.a1 ?? 0, easeIn(u));
    const w = e.w ?? 1; m.geometry.dispose(); m.geometry = new THREE.RingGeometry(1 - 0.14 * w * (1 - 0.5 * u), 1, 72);
  }
  fxWall(e, u) {
    const m = this.wallPool.get(); const k = easeOut(u); const r = lerp(e.r0, e.r1, k); const h = lerp(e.h0 ?? 0.5, e.h1 ?? 1.5, k);
    m.position.set(...e.p); m.scale.set(r, h, r); m.material.color.set(e.col || '#ffffff'); m.material.opacity = lerp(e.a0 ?? 0.8, 0, easeIn(u));
  }
  fxCrack(e, f, u) {
    const m = this.crackPool.get(); const t = clamp01((f - e.f0) / 2); const s = e.s * (0.35 + 0.65 * easeOut(t));
    m.position.set(e.p[0], 0.03 + (e.y || 0), e.p[2]); m.scale.set(s, s, s); m.rotation.z = e.rot || 0;
    m.material.map = this.tex.cracks[(e.seed || 0) % this.tex.cracks.length]; m.material.needsUpdate = true;
    m.material.opacity = e.keep ? (e.fadeAt && f > e.fadeAt ? clamp01(1 - (f - e.fadeAt) / 14) : 1) : 1 - easeIn(u) * 0.8;
  }
  fxDust(e, f, age, u) {
    // billowing puffs: expand fast then drift and roll, lit side warmer, fade with a soft tail
    const r = mulberry32((e.seed || 1) * 7919); const life = (e.f1 - e.f0 + 9) / this.storyFps;
    const base = new THREE.Color(e.col || '#cfd6df'), warm = new THREE.Color('#fff4e6'), cool = new THREE.Color('#8e9db3');
    for (let i = 0; i < e.n; i++) {
      const a = r() * Math.PI * 2, sp = (e.spread || 3) * (0.3 + r() * 0.7), rise = (e.rise ?? 1.5) * (0.4 + r() * 0.6), sz0 = (e.size || 1.2) * (0.6 + r() * 0.8), dl = r() * 0.12;
      const lit = r(), spin = (r() - 0.5) * 1.6, tex = (r() * 3) | 0;
      const t = Math.max(0, age - dl); if (age < dl) continue;
      const drag = 1 - Math.exp(-t * 4.5);
      const o = this.dustPool.get(); const dir = e.dir ? new THREE.Vector3(...e.dir) : null;
      let px = e.p[0] + Math.cos(a) * sp * drag * 0.6, pz = e.p[2] + Math.sin(a) * sp * drag * 0.6;
      if (dir) { px += dir.x * (e.drift || 0) * t * (0.5 + r()); pz += dir.z * (e.drift || 0) * t * (0.5 + r()); }
      o.position.set(px, e.p[1] + 0.2 + rise * drag * 0.6 + sz0 * 0.25 + t * 0.35, pz);
      const sz = sz0 * (0.55 + 1.5 * Math.sqrt(drag) + 0.25 * t); o.scale.set(sz, sz, 1);
      o.material.map = this.tex.puffs[tex];
      o.material.color.copy(base).lerp(lit > 0.5 ? warm : cool, 0.35 * Math.abs(lit - 0.5) * 2);
      const near = clamp01((o.position.distanceTo(this.camera.position) - 1.5 - sz * 0.5) / 5.0);   // soft fade near the lens
      o.material.opacity = (e.a ?? 0.6) * 1.15 * clamp01(t / 0.04) * (1 - easeIn(clamp01(t / life))) * near * near;
      o.material.rotation = a + spin * t;
    }
  }
  fxDebris(e, f, age) {
    const r = mulberry32((e.seed || 1) * 104729); const g = e.grav ?? 38; const life = e.life ?? 0.9;
    if (age > life) return;
    for (let i = 0; i < e.n; i++) {
      const a = r() * Math.PI * 2, el = (e.up ?? 0.6) + r() * 0.8, sp = (e.speed || 10) * (0.35 + r() * 0.65);
      const vx = Math.cos(a) * sp * (e.flat ?? 0.9), vz = Math.sin(a) * sp * (e.flat ?? 0.9), vy = sp * el;
      const dv = e.dir ? new THREE.Vector3(...e.dir).multiplyScalar((e.dirSpeed || 0) * (0.5 + r())) : new THREE.Vector3();
      const sz = lerp(e.size[0], e.size[1], r()); const spin = [(r() - .5) * 14, (r() - .5) * 14, (r() - .5) * 14];
      const t = age; let y = e.p[1] + vy * t - 0.5 * g * t * t + sz * 0.5;
      let bounced = false; if (y < sz * 0.5) { y = sz * 0.5; bounced = true; }
      const o = this.debrisPool.get();
      o.position.set(e.p[0] + (vx + dv.x) * t, y, e.p[2] + (vz + dv.z) * t); o.scale.set(sz, sz * (0.7 + r() * 0.6), sz * (0.7 + r() * 0.6));
      const q = bounced ? 0.0 : 1.0; o.rotation.set(spin[0] * t * q + i, spin[1] * t * q, spin[2] * t * q);
      o.material.color.set(e.col || '#f2f4f8'); o.children[0].visible = e.outline !== false;
    }
  }
  fxSlash(e, u) {
    const m = this.slashPool.get(); const U = new THREE.Vector3(...e.u).normalize(), V = new THREE.Vector3(...e.v).normalize(), N = new THREE.Vector3().crossVectors(U, V).normalize();
    const R = e.r; const mat4 = new THREE.Matrix4().makeBasis(U, V, N); m.quaternion.setFromRotationMatrix(mat4); m.position.set(...e.p); m.scale.set(R, R, R);
    const head = lerp(e.a0, e.a1, easeOut(clamp01(u * 1.6))); const tail = lerp(e.a0, e.a1, clamp01((u - 0.25) * 1.4));
    const dir = Math.sign(e.a1 - e.a0) || 1; const lo = Math.min(head, tail), hi = Math.max(head, tail);
    const un = m.material.uniforms; un.a0.value = lo; un.a1.value = hi + 1e-3; un.rin.value = e.rin ?? 0.78; un.th.value = e.th ?? 0.22; un.col.value.set(e.col || '#ffffff'); un.alpha.value = (e.alpha ?? 1) * (1 - easeIn(u) * 0.7);
    if (dir < 0) { un.a0.value = lo; un.a1.value = hi + 1e-3; }
  }
  fxPillar(e, f) {
    // rises in ~2 frames, stays, is gone after f1 (the shatter is a separate debris event)
    const u = clamp01((f - e.f0) / 2); const h = e.h * (1 - Math.pow(1 - u, 3)); if (h < 0.05) return;
    const m = this.pillarPool.get(); m.position.set(e.p[0], h / 2 - 0.05, e.p[2]); m.scale.set(e.w, h, e.w * (e.d || 1));
    m.rotation.set((e.tilt || 0) * Math.PI / 180, (e.rot || 0) * Math.PI / 180, 0);
    m.material.color.set(e.col || '#8e98ac');
  }
  fxStreak(e, u) {
    const m = this.streakPool.get(); const p0 = new THREE.Vector3(...e.p0), p1 = new THREE.Vector3(...e.p1); const axis = p1.clone().sub(p0); const len = axis.length(); axis.normalize();
    const mid = p0.clone().add(p1).multiplyScalar(0.5); const view = this.camera.position.clone().sub(mid).normalize(); const side = new THREE.Vector3().crossVectors(axis, view).normalize();
    const nrm = new THREE.Vector3().crossVectors(axis, side).normalize(); m.matrix.makeBasis(axis.multiplyScalar(len), side.multiplyScalar(e.w || 0.15), nrm); m.matrix.setPosition(mid); m.matrixAutoUpdate = false; m.matrixWorldNeedsUpdate = true;
    m.material.color.set(e.col || '#ffffff'); m.material.opacity = (e.a ?? 0.9) * (1 - easeIn(u));
  }

  // ------------------------------------------------------------ camera / lights / frame
  applyCamera(f) {
    const c = this.shot.cam[f]; const cam = this.camera;
    cam.fov = c[6]; cam.position.set(c[0], c[1], c[2]); cam.up.set(0, 1, 0); cam.lookAt(c[3], c[4], c[5]);
    if (c[7]) cam.rotateZ(c[7] * Math.PI / 180);
    cam.updateProjectionMatrix(); cam.updateMatrixWorld(true);
    this.sky.position.copy(cam.position);
  }
  applyLights(f) {
    const c = this.shot.focus ? this.shot.focus[f] : [0, 2, 0];
    const snap = v => Math.round(v / 0.25) * 0.25;
    const cx = snap(c[0]), cz = snap(c[2]);
    this.sun.position.set(cx + this.keyDir.x * 40, this.keyDir.y * 40, cz + this.keyDir.z * 40); this.sun.target.position.set(cx, 0, cz);
    this.back.position.set(cx + this.sunDir.x * 40, this.sunDir.y * 40, cz + this.sunDir.z * 40); this.back.target.position.set(cx, 1.5, cz);
    this.rim.position.set(cx + 14, 8, cz + 18); this.rim.target.position.set(cx, 2, cz);
    for (const o of [this.sun, this.back, this.rim]) { o.target.updateMatrixWorld(); o.updateMatrixWorld(); }
  }
  applyTags(f) {
    for (const id of Object.keys(this.tag)) {
      const t = this.shot.tags[id], sp = this.tag[id]; const on = t.vis[f];
      sp.visible = on > 0.01; if (!on) continue;
      const h = this.shot.chars[id].parts.Head[f]; const dist = this.camera.position.distanceTo(new THREE.Vector3(h[0], h[1], h[2]));
      const k = Math.max(0.5, dist * 0.085) * on; sp.position.set(h[0], h[1] + 1.55 + 0.25 * k, h[2]); sp.scale.set(4 * k, 1 * k, 1); sp.material.opacity = Math.min(1, on);
    }
  }
  render(i, pass) {
    const n = Math.max(0, Math.min(this.frames - 1, i | 0)); const tau = this.tau ? this.tau[n] : n;
    for (const L of this.flashLights) L.intensity = 0;
    this.applyChars(n); this.applyCamera(n); this.applyLights(n); this.applyFx(n, tau); this.applyTags(n);
    this.scene.updateMatrixWorld(true);
    this.renderer.render(this.scene, this.camera);
    const color = this.renderer.domElement.toDataURL('image/png');
    if (pass !== 'both') return color;
    // depth pass for the depth-of-field in post: 8-bit log depth (0.3 .. 600 studs), effects / sky / sprites hidden
    if (!this.depthMat) this.depthMat = new THREE.ShaderMaterial({
      vertexShader: 'varying float vz; void main(){ vec4 mv = modelViewMatrix * vec4(position, 1.0); vz = -mv.z; gl_Position = projectionMatrix * mv; }',
      fragmentShader: 'varying float vz; void main(){ float v = clamp(log(max(vz, 0.3) / 0.3) / log(2000.0), 0.0, 1.0); gl_FragColor = vec4(v, v, v, 1.0); }' });
    const hidden = [];
    this.scene.traverse(o => { if (o.visible && (o.isSprite || o.isLight || o === this.sky || (o.material && !Array.isArray(o.material) && o.material.transparent))) { hidden.push(o); o.visible = false; } });
    const fog = this.scene.fog; this.scene.fog = null; this.scene.overrideMaterial = this.depthMat;
    const cc = this.renderer.getClearColor(new THREE.Color()); const ca = this.renderer.getClearAlpha(); const sm = this.renderer.shadowMap.enabled;
    this.renderer.setClearColor(0xffffff, 1); this.renderer.shadowMap.enabled = false;
    this.renderer.render(this.scene, this.camera);
    const depth = this.renderer.domElement.toDataURL('image/png');
    this.scene.overrideMaterial = null; this.scene.fog = fog; this.renderer.setClearColor(cc, ca); this.renderer.shadowMap.enabled = sm;
    for (const o of hidden) o.visible = true;
    return { color, depth };
  }
}
