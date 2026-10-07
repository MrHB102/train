import * as THREE from 'three';
import { createEngine } from './engine/engine.js';
import { loadBodyPackage } from './avatar/package.js';
import { Body } from './avatar/body.js';

async function main() {
  const engine = createEngine(document.getElementById('app'));
  const pkg = await loadBodyPackage('./data/');
  const body = new Body(pkg);
  body.group.position.y = -body.floorY;
  engine.stage.add(body.group);
  engine.start();
  window.__app = { engine, body, pkg, THREE };
  document.body.dataset.ready = '1';
}
main().catch((e) => {
  console.error(e);
  document.body.dataset.error = String(e && e.stack ? e.stack : e);
});
