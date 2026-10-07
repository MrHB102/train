// Aba Pose e cena: poses, movimentos, altura do salto, câmera e exposição.
import { h } from '../dom.js';
import { slider, toggle, group, chips } from '../components.js';
import { tr } from '../i18n.js';
import { POSES, MOTIONS } from '../../avatar/animation.js';
import { FOCUS } from '../../app/app.js';

const FOCUS_LABEL = {
  full: { pt: 'Corpo todo', en: 'Full body' },
  bust: { pt: 'Busto', en: 'Bust' },
  waist: { pt: 'Cintura', en: 'Waist' },
  hips: { pt: 'Quadril', en: 'Hips' },
  glutes: { pt: 'Costas / glúteos', en: 'Back / glutes' },
  thighs: { pt: 'Coxas', en: 'Thighs' },
  legs: { pt: 'Pernas', en: 'Legs' },
  feet: { pt: 'Pés', en: 'Feet' },
  neck: { pt: 'Pescoço', en: 'Neck' },
};

export function buildSceneTab(app) {
  const root = h('div');
  const refreshers = [];

  const gPose = group({ pt: 'Pose', en: 'Pose' });
  const poses = chips({
    items: Object.entries(POSES).map(([id, p]) => ({ id, label: { pt: p.pt, en: p.en } })),
    value: app.view.pose,
    onPick: (id) => (app.setView({ pose: id }), poses.set(id), app.commit()),
  });
  gPose.body.append(poses.el);
  refreshers.push(() => poses.set(app.view.pose));

  const gMove = group({ pt: 'Movimento', en: 'Motion' });
  const motions = chips({
    items: Object.entries(MOTIONS).map(([id, m]) => ({ id, label: { pt: m.pt, en: m.en } })),
    value: app.view.motion,
    onPick: (id) => (app.setView({ motion: id }), motions.set(id), app.commit()),
  });
  const speed = slider({ label: { pt: 'Velocidade', en: 'Speed' }, min: 0.3, max: 2.5, step: 0.01, neutral: 1, value: app.view.speed, onInput: (v) => app.setView({ speed: v }), onChange: () => app.commit() });
  gMove.body.append(motions.el, speed.el);
  refreshers.push(() => (motions.set(app.view.motion), speed.set(app.view.speed)));

  const gHeel = group({ pt: 'Salto', en: 'Heels' });
  const heel = slider({
    label: { pt: 'Altura do salto', en: 'Heel height' },
    hint: { pt: 'Inclina o pé como em um salto alto (vale para as pernas nuas e com sapato)', en: 'Pitches the foot like a high heel' },
    min: 0,
    max: 0.16,
    step: 0.001,
    neutral: 0,
    format: (v) => `${(v * 100).toFixed(0)} cm`,
    value: app.view.heel,
    onInput: (v) => app.setView({ heel: v }),
    onChange: () => app.commit(),
  });
  gHeel.body.append(heel.el);
  refreshers.push(() => heel.set(app.view.heel));

  const gCam = group({ pt: 'Câmera', en: 'Camera' });
  const focus = chips({ items: Object.keys(FOCUS).map((id) => ({ id, label: FOCUS_LABEL[id] })), value: '', onPick: (id) => (app.focus(id), focus.set(id)) });
  const auto = toggle({ label: { pt: 'Girar o palco', en: 'Turntable' }, value: app.view.autoRotate, onChange: (v) => (app.setView({ autoRotate: v }), app.commit()) });
  const rot = slider({ label: { pt: 'Velocidade do giro', en: 'Turntable speed' }, min: 0.1, max: 2, step: 0.01, neutral: 0.5, value: app.view.rotateSpeed, onInput: (v) => app.setView({ rotateSpeed: v }), onChange: () => app.commit() });
  const exp = slider({ label: { pt: 'Exposição', en: 'Exposure' }, min: 0.5, max: 1.8, step: 0.01, neutral: 1.05, value: app.view.exposure, onInput: (v) => app.setView({ exposure: v }), onChange: () => app.commit() });
  gCam.body.append(focus.el, auto.el, rot.el, exp.el);
  refreshers.push(() => (auto.set(app.view.autoRotate), rot.set(app.view.rotateSpeed), exp.set(app.view.exposure)));

  root.append(gPose.el, gMove.el, gHeel.el, gCam.el);
  void tr;
  return { el: root, refresh: () => refreshers.forEach((r) => r()), activate: () => app.focus('full') };
}
