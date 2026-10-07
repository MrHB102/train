// Estúdio procedural: cúpula em gradiente + softboxes emissivas, pré-filtrado em PMREM para IBL.
import * as THREE from 'three';

export function buildStudioEnvironment(renderer) {
  const scene = new THREE.Scene();
  const dome = new THREE.Mesh(
    new THREE.SphereGeometry(40, 48, 24),
    new THREE.ShaderMaterial({
      side: THREE.BackSide,
      depthWrite: false,
      uniforms: {},
      vertexShader: 'varying vec3 vP; void main(){ vP = normalize(position); gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0);} ',
      fragmentShader: `varying vec3 vP;
        void main(){
          float h = vP.y*0.5+0.5;
          vec3 top = vec3(0.060, 0.062, 0.085);
          vec3 mid = vec3(0.030, 0.030, 0.042);
          vec3 bot = vec3(0.090, 0.060, 0.050);
          vec3 c = mix(bot, mid, smoothstep(0.0, 0.45, h));
          c = mix(c, top, smoothstep(0.45, 1.0, h));
          gl_FragColor = vec4(c, 1.0);
        }`,
    })
  );
  scene.add(dome);

  const box = (w, h, x, y, z, color, intensity) => {
    const m = new THREE.Mesh(
      new THREE.PlaneGeometry(w, h),
      new THREE.MeshBasicMaterial({ color: new THREE.Color(color).multiplyScalar(intensity), side: THREE.DoubleSide, toneMapped: false })
    );
    m.position.set(x, y, z);
    m.lookAt(0, 1.0, 0);
    scene.add(m);
  };
  // chave (quente), preenchimento (frio), recortes traseiros (strip), topo, bounce
  box(3.2, 3.6, -4.2, 3.4, 4.2, 0xfff0e2, 7.5);
  box(2.6, 3.0, 4.8, 1.8, 3.4, 0xcfe0ff, 2.4);
  box(0.9, 4.2, -3.6, 2.2, -3.6, 0xfff4ea, 11);
  box(0.9, 4.2, 3.8, 2.0, -3.2, 0xdfe9ff, 10);
  box(5, 5, 0, 7.5, 0.5, 0xffffff, 2.2);
  box(6, 2, 0, -0.6, 3.5, 0xffd9c4, 0.9);

  const pmrem = new THREE.PMREMGenerator(renderer);
  const rt = pmrem.fromScene(scene, 0.015);
  pmrem.dispose();
  scene.traverse((o) => {
    if (o.geometry) o.geometry.dispose();
    if (o.material) o.material.dispose();
  });
  return rt.texture;
}

export function gradientBackground(top = '#1a1a24', bottom = '#07070b') {
  const c = document.createElement('canvas');
  c.width = 4;
  c.height = 256;
  const g = c.getContext('2d');
  const grad = g.createLinearGradient(0, 0, 0, 256);
  grad.addColorStop(0, top);
  grad.addColorStop(0.55, '#101017');
  grad.addColorStop(1, bottom);
  g.fillStyle = grad;
  g.fillRect(0, 0, 4, 256);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}
