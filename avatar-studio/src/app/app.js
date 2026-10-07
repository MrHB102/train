// App: raiz de composição. Cria o engine, o Body e os sistemas (pele, roupas, física, animação, repique) e
// guarda o Design (tudo que a UI edita) com histórico de desfazer/refazer, compartilhamento e presets.
import * as THREE from 'three';
import { createEngine } from '../engine/engine.js';
import { loadBodyPackage } from '../avatar/package.js';
import { Body } from '../avatar/body.js';
import { Animator, POSES, MOTIONS } from '../avatar/animation.js';
import { Jiggle } from '../physics/jiggle.js';
import { BodyColliders } from '../physics/colliders.js';
import { Elastic } from '../avatar/elastic.js';
import { computeAnatomy } from '../avatar/anatomy.js';
import { createContext } from '../garments/context.js';
import { Wardrobe } from '../garments/wardrobe.js';
import { Dresser } from '../garments/dresser.js';
import { createNoise3D, createSkinLUT } from '../shaders/textures.js';
import { SkinMaterial } from '../shaders/skin.js';
import { TRAITS, TRAIT_BY_ID } from '../domain/traits.js';
import { DIALS } from '../domain/dials.js';
import { defaultSkin, SKIN_TONES, SKIN_PARAMS } from '../domain/skin.js';

/** Enquadramentos da câmera (posições no espaço de referência do corpo; az em graus, 0 = frente). */
export const FOCUS = {
  full: { t: [0, 0.07, 0], d: 3.6, az: 0, el: 4 },
  bust: { t: [0, 0.33, 0.07], d: 1.6, az: 0, el: 4 },
  waist: { t: [0, 0.14, 0.05], d: 1.7, az: 0, el: 4 },
  hips: { t: [0, -0.04, 0.03], d: 1.9, az: 18, el: 4 },
  glutes: { t: [0, -0.05, -0.04], d: 1.9, az: 180, el: 6 },
  thighs: { t: [0, -0.28, 0.04], d: 2.0, az: 0, el: 3 },
  legs: { t: [0, -0.5, 0.04], d: 2.6, az: 0, el: 2 },
  feet: { t: [0, -0.74, 0.08], d: 1.6, az: 0, el: 12 },
  neck: { t: [0, 0.5, 0.03], d: 1.25, az: 0, el: 5 },
};

export const DYN_DEFAULT = {
  recoil: { enabled: true, amount: 1 },
  jiggle: { enabled: true, bust: 1, glutes: 1, thighs: 1, belly: 1, damping: 1, stiffness: 1 },
  cloth: { wind: 0, stiffness: 1 },
};
export const VIEW_DEFAULT = { pose: 'stand', motion: 'idle', speed: 1, heel: 0, autoRotate: false, rotateSpeed: 0.5, exposure: 1.05 };

const clone = (o) => JSON.parse(JSON.stringify(o));

export class App {
  constructor() {
    this.listeners = new Map();
    this.skin = defaultSkin();
    this.dyn = clone(DYN_DEFAULT);
    this.view = { ...VIEW_DEFAULT };
    this.history = [];
    this.future = [];
    this.tween = null;
  }

  static async create(container, { onProgress } = {}) {
    const app = new App();
    onProgress?.('engine');
    app.engine = createEngine(container);
    onProgress?.('body');
    const pkg = await loadBodyPackage('./data/');
    app.pkg = pkg;
    app.body = new Body(pkg);
    app.ctx = createContext(app.body);
    onProgress?.('skin');
    const noise = createNoise3D();
    app.noise = noise;
    app.skinMat = new SkinMaterial({ noise, lut: createSkinLUT() });
    app.skinMat.setLandmarks(app.ctx, 7);
    app.skinMat.setAnatomy(computeAnatomy(app.ctx));
    app.body.mesh.material = app.skinMat;
    app.wardrobe = new Wardrobe(app.body, app.ctx);
    app.animator = new Animator(app.body);
    app.jiggle = new Jiggle(app.body);
    app.colliders = new BodyColliders(app.body);
    app.elastic = new Elastic(app.body, app.jiggle);
    onProgress?.('outfit');
    app.dresser = new Dresser({ body: app.body, ctx: app.ctx, wardrobe: app.wardrobe, noise, engine: app.engine, colliders: app.colliders });
    app.dresser.sim = { elastic: app.elastic, animator: app.animator };
    app.engine.stage.add(app.body.group);
    app.body.onChange((b) => app._syncSkinState(b));
    app._syncSkinState(app.body);
    app.applyDyn();
    app.applyView();
    app.engine.onUpdate((dt) => app._update(dt));
    app.dresser.onChange(() => (app.applyView(), app.emit('design')));
    app.engine.start();
    app.history = [app.serialize()];
    return app;
  }

  // ------------------------------------------------------------------ eventos
  on(evt, fn) {
    if (!this.listeners.has(evt)) this.listeners.set(evt, new Set());
    this.listeners.get(evt).add(fn);
    return () => this.listeners.get(evt).delete(fn);
  }
  emit(evt, data) {
    this.listeners.get(evt)?.forEach((fn) => fn(data));
  }

  // ------------------------------------------------------------------ laço principal
  _update(dt) {
    this._tweenCamera(dt);
    this.elastic.update(dt);
    this.animator.update(dt);
    this.jiggle.update(dt);
    this.dresser.update(dt);
    if (this.animator.motion === 'twirl') this.engine.stage.rotation.y = this.animator.twirl;
  }

  _syncSkinState(b) {
    const e = b.effective();
    this.skinMat.setBodyState({
      tone: 0.18 + 0.75 * (e['belly.tone'] || 0) + 0.8 * (e.muscle - 0.5) - 0.9 * (e.weight - 0.5),
      lean: 1.25 - 1.5 * e.weight,
    });
  }

  // ------------------------------------------------------------------ corpo
  trait(id) {
    return this.elastic.target('trait', id) ?? TRAIT_BY_ID[id].neutral;
  }
  dial(id) {
    return this.elastic.target('dial', id) ?? 0;
  }
  setTrait(id, v) {
    this.elastic.set({ traits: { [id]: v } });
    this.emit('design');
  }
  setDial(id, v) {
    this.elastic.set({ dials: { [id]: v } });
    this.emit('design');
  }
  setSkin(patch) {
    this.skin = { ...this.skin, ...patch };
    this.skinMat.setSkin(this.skin);
    this.emit('design');
  }
  setDyn(group, patch) {
    this.dyn[group] = { ...this.dyn[group], ...patch };
    this.applyDyn();
    this.emit('design');
  }
  applyDyn() {
    const d = this.dyn;
    this.elastic.enabled = d.recoil.enabled;
    this.elastic.amount = d.recoil.amount;
    this.jiggle.setDynamics({ enabled: d.jiggle.enabled, bust: d.jiggle.bust, glutes: d.jiggle.glutes, thighs: d.jiggle.thighs, belly: d.jiggle.belly, damping: d.jiggle.damping, stiffnessScale: d.jiggle.stiffness });
    this.dresser.setCloth?.(d.cloth);
  }
  setView(patch) {
    this.view = { ...this.view, ...patch };
    this.applyView();
    this.emit('design');
  }
  applyView() {
    const v = this.view;
    this.animator.setPose(v.pose);
    this.animator.setMotion(v.motion);
    this.animator.speed = v.speed;
    this.animator.heelMeters = this.dresser?.entries.get('shoes')?.options.heel ?? v.heel; // com sapato, o salto vem dele
    this.engine.state.autoRotate = v.autoRotate;
    this.engine.state.rotateSpeed = v.rotateSpeed;
    this.engine.renderer.toneMappingExposure = v.exposure;
  }

  // ------------------------------------------------------------------ câmera
  focus(name) {
    const f = FOCUS[name];
    if (!f) return;
    const e = this.engine;
    e.stage.rotation.y = 0;
    e.stage.updateMatrixWorld(true);
    const target = this.body.group.localToWorld(new THREE.Vector3(...f.t));
    const az = (f.az * Math.PI) / 180;
    const el = (f.el * Math.PI) / 180;
    const pos = target.clone().add(new THREE.Vector3(Math.sin(az) * Math.cos(el), Math.sin(el), Math.cos(az) * Math.cos(el)).multiplyScalar(f.d));
    this.tween = { t: 0, dur: 0.7, fromP: e.camera.position.clone(), fromT: e.controls.target.clone(), toP: pos, toT: target };
  }
  _tweenCamera(dt) {
    const tw = this.tween;
    if (!tw) return;
    tw.t += dt / tw.dur;
    const k = Math.min(1, tw.t);
    const s = k * k * (3 - 2 * k);
    const e = this.engine;
    e.camera.position.lerpVectors(tw.fromP, tw.toP, s);
    e.controls.target.lerpVectors(tw.fromT, tw.toT, s);
    if (k >= 1) this.tween = null;
  }

  // ------------------------------------------------------------------ histórico
  /** Registra o estado atual no histórico (chamado ao soltar um slider, clicar um botão…). */
  commit() {
    const snap = this.serialize();
    if (JSON.stringify(snap) === JSON.stringify(this.history[this.history.length - 1])) return;
    this.history.push(snap);
    if (this.history.length > 120) this.history.shift();
    this.future = [];
    this.emit('history');
  }
  get canUndo() {
    return this.history.length > 1;
  }
  get canRedo() {
    return this.future.length > 0;
  }
  undo() {
    if (!this.canUndo) return;
    this.future.push(this.history.pop());
    this.restore(this.history[this.history.length - 1], { silent: true });
    this.emit('history');
  }
  redo() {
    if (!this.canRedo) return;
    const s = this.future.pop();
    this.history.push(s);
    this.restore(s, { silent: true });
    this.emit('history');
  }

  // ------------------------------------------------------------------ estado
  serialize() {
    const traits = {};
    for (const t of TRAITS) {
      const v = this.elastic.target('trait', t.id);
      if (v !== undefined && Math.abs(v - t.neutral) > 1e-6) traits[t.id] = +v.toFixed(4);
    }
    const dials = {};
    for (const d of DIALS) {
      const v = this.elastic.target('dial', d.id);
      if (v && Math.abs(v) > 1e-6) dials[d.id] = +v.toFixed(4);
    }
    return { v: 1, traits, dials, skin: this.skin, dresser: this.dresser.serialize(), dyn: this.dyn, view: this.view };
  }

  restore(s, { snap = false, silent = false } = {}) {
    if (!s) return;
    const traits = {};
    for (const t of TRAITS) traits[t.id] = s.traits?.[t.id] ?? t.neutral;
    const dials = {};
    for (const d of DIALS) dials[d.id] = s.dials?.[d.id] ?? d.neutral;
    this.elastic.set({ traits, dials }, { snap });
    if (snap) this.elastic.snap();
    this.skin = { ...defaultSkin(), ...(s.skin || {}) };
    this.skinMat.setSkin(this.skin);
    this.dresser.restore(s.dresser);
    this.dyn = { ...clone(DYN_DEFAULT), ...(s.dyn || {}) };
    this.view = { ...VIEW_DEFAULT, ...(s.view || {}) };
    this.applyDyn();
    this.applyView();
    if (!silent) this.commit();
    this.emit('restore');
    this.emit('design');
  }

  resetAll() {
    this.restore({ v: 1 });
  }

  /** Código para compartilhar: JSON compacto em base64url. */
  shareCode() {
    const json = JSON.stringify(this.serialize());
    return btoa(unescape(encodeURIComponent(json))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  }
  loadCode(code) {
    const b64 = code.trim().replace(/-/g, '+').replace(/_/g, '/');
    const json = decodeURIComponent(escape(atob(b64 + '==='.slice((b64.length + 3) % 4))));
    this.restore(JSON.parse(json));
  }

  /** Aplica um preset de corpo (Traits e Dials); o corpo anima até lá, com o repique. */
  applyBodyPreset(p) {
    const traits = {};
    for (const t of TRAITS) traits[t.id] = p.traits?.[t.id] ?? t.neutral;
    const dials = {};
    for (const d of DIALS) dials[d.id] = p.dials?.[d.id] ?? d.neutral;
    this.elastic.set({ traits, dials });
    this.commit();
    this.emit('restore');
  }

  randomize() {
    const pick = (a, b) => a + Math.random() * (b - a);
    const traits = {};
    for (const t of TRAITS) {
      if (t.kind !== 'detail' || t.runtime || t.group === 'silhouette') continue;
      if (/^(neck|shoulders|torso\.(vshape|back|chestMuscle|width|depth|posture)|feet|ankles)/.test(t.id) && Math.random() < 0.7) continue;
      const [a, b] = t.natural;
      traits[t.id] = pick(a * 0.6, b * 0.75);
    }
    const dials = { curves: pick(-0.3, 1.1), tone: pick(-0.4, 0.9), anime: pick(0, 0.9), bustSize: pick(-0.4, 1.6), glutesSize: pick(-0.3, 1.5), hipSize: pick(-0.3, 0.9), thickness: pick(-0.4, 1.1) };
    this.elastic.set({ traits: { ...traits, age: pick(25, 38), weight: pick(0.25, 0.7), muscle: pick(0.3, 0.7), height: pick(0.35, 0.7) }, dials });
    const tone = SKIN_TONES[Math.floor(Math.random() * SKIN_TONES.length)];
    this.setSkin({ toneId: tone.id, tone: tone.color });
    this.commit();
    this.emit('restore');
  }

  // ------------------------------------------------------------------ captura
  screenshot() {
    const e = this.engine;
    e.renderOnce();
    return new Promise((res) => e.renderer.domElement.toBlob(res, 'image/png'));
  }
}

export { POSES, MOTIONS, SKIN_PARAMS };
