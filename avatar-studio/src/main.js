import * as THREE from 'three';
import { createEngine } from './engine/engine.js';
import { loadBodyPackage } from './avatar/package.js';
import { Body } from './avatar/body.js';
import { Animator } from './avatar/animation.js';
import { Jiggle } from './physics/jiggle.js';
import { BodyColliders } from './physics/colliders.js';
import { createSkirtCloth, refitSkirt } from './garments/drapes/skirt.js';
import { createContext } from './garments/context.js';
import { Wardrobe } from './garments/wardrobe.js';
import { createNoise3D, createSkinLUT } from './shaders/textures.js';
import { SkinMaterial } from './shaders/skin.js';
import { FabricMaterial } from './shaders/fabric.js';
import { baseTop, baseBottom } from './garments/recipes/base.js';
import { computeAnatomy } from './avatar/anatomy.js';

async function main() {
  const engine = createEngine(document.getElementById('app'));
  const pkg = await loadBodyPackage('./data/');
  const body = new Body(pkg);
  const ctx = createContext(body);
  const skin = new SkinMaterial({ noise: createNoise3D(), lut: createSkinLUT() });
  skin.setLandmarks(ctx, 7);
  body.mesh.material = skin;
  const noise = skin.u.uNoise.value;
  const matTop = new FabricMaterial({ noise, fabric: 'cotton', color: '#f2eeea' });
  const matBottom = new FabricMaterial({ noise, fabric: 'cotton', color: '#f2eeea' });
  const wardrobe = new Wardrobe(body, ctx);
  const addBase = (which, res, mat) => {
    wardrobe.add(`base.${which}`, { ...res.shell, material: mat, layer: 1 });
    res.ribbons.forEach((r, i) => wardrobe.addRibbon(`base.${which}.r${i}`, { ...r, material: mat, width: 0.0042, profile: 'round', sides: 6, offset: 0.0008, layer: 1 }));
  };
  addBase('top', baseTop(ctx, { style: 'triangle' }), matTop);
  addBase('bottom', baseBottom(ctx, { style: 'bikini' }), matBottom);
  engine.stage.add(body.group);
  const animator = new Animator(body);
  animator.setMotion('none');
  const jiggle = new Jiggle(body);
  const colliders = new BodyColliders(body);
  const skirtMat = new FabricMaterial({ noise, fabric: 'satin', color: '#15151c', trim: 'piping', trimColor: '#f4f4f4', trimWidth: 0.03 });
  let skirt = createSkirtCloth(body, ctx, { length: 0.34, flare: 0.8 });
  const skirtMesh = new THREE.Mesh(skirt.geometry, skirtMat);
  skirtMesh.frustumCulled = false;
  skirtMesh.castShadow = true;
  skirtMesh.receiveShadow = true;
  body.group.add(skirtMesh);
  body.onChange(() => refitSkirt(skirt, body, ctx));
  engine.onUpdate((dt) => {
    animator.update(dt);
    jiggle.update(dt);
    skirt.step(dt, colliders.update(), 0);
    if (animator.motion === 'twirl') engine.stage.rotation.y = animator.twirl;
  });
  const anat = computeAnatomy(ctx);
  skin.setAnatomy(anat);
  const syncSkinState = (b) => {
    const e = b.effective();
    skin.setBodyState({
      tone: 0.18 + 0.75 * (e['belly.tone'] || 0) + 0.8 * (e.muscle - 0.5) - 0.9 * (e.weight - 0.5),
      lean: 1.25 - 1.5 * e.weight,
    });
  };
  body.onChange(syncSkinState);
  syncSkinState(body);
  const debugAnatomy = (on = true) => {
    body.group.children.filter((c) => c.name === 'dbg').forEach((c) => c.removeFromParent());
    if (!on) return;
    const g = new THREE.SphereGeometry(0.0035, 8, 6);
    for (let i = 0; i < anat.length / 3; i++) {
      const m = new THREE.Mesh(g, new THREE.MeshBasicMaterial({ color: i < 10 ? 0xff2020 : i < 16 ? 0x20ff20 : i < 17 ? 0xffff00 : i < 25 ? 0x2080ff : i < 29 ? 0xff00ff : i < 33 ? 0x00ffff : 0xffffff }));
      m.position.set(anat[i * 3], anat[i * 3 + 1], anat[i * 3 + 2]);
      m.name = 'dbg';
      body.group.add(m);
    }
  };
  const cam = (p, t, n = 3) => {
    engine.stop();
    engine.camera.position.set(...p);
    engine.controls.target.set(...t);
    engine.controls.update();
    engine.step(1 / 60, n);
  };
  engine.start();
  window.__app = { cam, anat, debugAnatomy, engine, body, pkg, ctx, wardrobe, skin, animator, jiggle, colliders, get skirt() { return skirt; }, skirtMat, matTop, matBottom, noise, THREE };
  document.body.dataset.ready = '1';
}
main().catch((e) => {
  console.error(e);
  document.body.dataset.error = String(e && e.stack ? e.stack : e);
});
