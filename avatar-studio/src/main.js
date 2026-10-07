import * as THREE from 'three';
import { App } from './app/app.js';
import { createUI } from './ui/ui.js';

async function main() {
  const loading = document.getElementById('loading');
  const app = await App.create(document.getElementById('app'));
  createUI(app);
  app.focus('full');
  // enquadramento inicial sem animação
  app.tween = null;
  const f = app.engine;
  f.camera.position.set(0, 1.0, 3.55);
  f.controls.target.set(0, 0.86, 0);
  f.controls.update();
  loading?.classList.add('done');
  setTimeout(() => loading?.remove(), 700);

  // ganchos de depuração e testes automatizados
  const cam = (p, t, n = 3) => {
    f.stop();
    f.camera.position.set(...p);
    f.controls.target.set(...t);
    f.controls.update();
    f.step(1 / 60, n);
  };
  window.__app = Object.assign(app, { cam, THREE, engine: f });
  document.body.dataset.ready = '1';
}
main().catch((e) => {
  console.error(e);
  document.body.dataset.error = String(e && e.stack ? e.stack : e);
});
