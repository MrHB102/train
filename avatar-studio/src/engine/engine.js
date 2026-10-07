// Engine: renderer WebGL2, câmera, controles, luzes, palco e loop.
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { buildStudioEnvironment, gradientBackground } from './environment.js';

export function createEngine(container) {
  const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance', preserveDrawingBuffer: false });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  container.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  scene.background = gradientBackground();
  scene.environment = buildStudioEnvironment(renderer);
  scene.environmentIntensity = 0.9;

  const camera = new THREE.PerspectiveCamera(28, 1, 0.05, 60);
  camera.position.set(0.0, 0.95, 3.6);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.target.set(0, 0.72, 0);
  controls.enableDamping = true;
  controls.dampingFactor = 0.07;
  controls.minDistance = 0.45;
  controls.maxDistance = 7;
  controls.maxPolarAngle = Math.PI * 0.56;
  controls.screenSpacePanning = true;
  controls.update();

  // luzes
  const key = new THREE.DirectionalLight(0xfff1e3, 2.2);
  key.position.set(-2.4, 3.2, 3.0);
  key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048);
  key.shadow.camera.left = -1.2;
  key.shadow.camera.right = 1.2;
  key.shadow.camera.top = 1.8;
  key.shadow.camera.bottom = -0.4;
  key.shadow.camera.near = 0.5;
  key.shadow.camera.far = 9;
  key.shadow.radius = 4;
  key.shadow.bias = -0.0004;
  key.shadow.normalBias = 0.012;
  key.target.position.set(0, 0.8, 0);
  scene.add(key, key.target);
  const rim = new THREE.DirectionalLight(0xdfe8ff, 1.4);
  rim.position.set(2.6, 2.2, -3.0);
  rim.target.position.set(0, 0.9, 0);
  scene.add(rim, rim.target);
  const fill = new THREE.DirectionalLight(0xffe2d0, 0.35);
  fill.position.set(3.0, 0.6, 2.4);
  scene.add(fill);

  // palco: pedestal giratório
  const stage = new THREE.Group();
  scene.add(stage);
  const pedestal = new THREE.Mesh(
    new THREE.CylinderGeometry(0.62, 0.66, 0.06, 128),
    new THREE.MeshPhysicalMaterial({ color: 0x14141a, roughness: 0.28, metalness: 0.15, clearcoat: 1, clearcoatRoughness: 0.12 })
  );
  pedestal.position.y = -0.03;
  pedestal.receiveShadow = true;
  scene.add(pedestal);
  const ring = new THREE.Mesh(
    new THREE.TorusGeometry(0.645, 0.006, 12, 160),
    new THREE.MeshBasicMaterial({ color: new THREE.Color(0xff6aa8).multiplyScalar(1.6), toneMapped: false })
  );
  ring.rotation.x = Math.PI / 2;
  ring.position.y = 0.0;
  scene.add(ring);
  const floor = new THREE.Mesh(new THREE.CircleGeometry(6, 64), new THREE.ShadowMaterial({ opacity: 0.35 }));
  floor.rotation.x = -Math.PI / 2;
  floor.position.y = -0.062;
  floor.receiveShadow = true;
  scene.add(floor);

  const updaters = new Set();
  let last = performance.now();
  let running = false;
  const state = { time: 0, autoRotate: false, rotateSpeed: 0.5 };

  // o painel lateral cobre parte da tela: desloca a imagem para o corpo ficar no centro da área livre
  const shift = { x: 0, y: 0 };
  function resize() {
    const w = container.clientWidth || window.innerWidth;
    const h = container.clientHeight || window.innerHeight;
    renderer.setSize(w, h, false);
    renderer.domElement.style.width = '100%';
    renderer.domElement.style.height = '100%';
    camera.aspect = w / h;
    if (shift.x || shift.y) camera.setViewOffset(w, h, shift.x, shift.y, w, h);
    else camera.clearViewOffset();
    camera.updateProjectionMatrix();
  }
  new ResizeObserver(resize).observe(container);
  window.addEventListener('resize', resize);
  resize();

  function frame(now) {
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;
    state.time += dt;
    if (state.autoRotate) stage.rotation.y += dt * state.rotateSpeed;
    controls.update();
    for (const fn of updaters) fn(dt, state.time);
    renderer.render(scene, camera);
  }

  return {
    renderer, scene, camera, controls, stage, key, rim, fill, pedestal, ring, state,
    onUpdate(fn) { updaters.add(fn); return () => updaters.delete(fn); },
    start() {
      if (running) return;
      running = true;
      renderer.setAnimationLoop(frame);
    },
    renderOnce() { frame(performance.now()); },
    /** Para o loop (testes determinísticos). */
    stop() {
      running = false;
      renderer.setAnimationLoop(null);
    },
    /** Avança a simulação com um dt fixo e renderiza (usado nos testes e capturas). */
    step(dt = 1 / 60, n = 1) {
      for (let i = 0; i < n; i++) {
        state.time += dt;
        if (state.autoRotate) stage.rotation.y += dt * state.rotateSpeed;
        for (const fn of updaters) fn(dt, state.time);
      }
      controls.update();
      renderer.render(scene, camera);
    },
    resize,
    /** Desloca a imagem (px): x > 0 move o corpo para a esquerda, y > 0 para cima. */
    setViewShift(x, y = 0) {
      shift.x = x;
      shift.y = y;
      resize();
    },
  };
}
