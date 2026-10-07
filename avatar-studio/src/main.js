import * as THREE from 'three';
import { createEngine } from './engine/engine.js';
import { loadBodyPackage } from './avatar/package.js';
import { Body } from './avatar/body.js';
import { createContext } from './garments/context.js';
import { Wardrobe } from './garments/wardrobe.js';
import { baseTop, baseBottom } from './garments/recipes/base.js';

async function main() {
  const engine = createEngine(document.getElementById('app'));
  const pkg = await loadBodyPackage('./data/');
  const body = new Body(pkg);
  const ctx = createContext(body);
  const mat = new THREE.MeshStandardMaterial({ color: 0xd9d4d2, roughness: 0.75 });
  const wardrobe = new Wardrobe(body, ctx);
  wardrobe.add('base.top', { ...baseTop(ctx), material: mat, layer: 1 });
  wardrobe.add('base.bottom', { ...baseBottom(ctx), material: mat, layer: 1 });
  body.group.position.y = -body.floorY;
  engine.stage.add(body.group);
  engine.start();
  window.__app = { engine, body, pkg, ctx, wardrobe, THREE };
  document.body.dataset.ready = '1';
}
main().catch((e) => {
  console.error(e);
  document.body.dataset.error = String(e && e.stack ? e.stack : e);
});
