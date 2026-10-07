// Interface: barra superior com abas, painel lateral, barra inferior com foco de câmera e repique.
import './style.css';
import { h } from './dom.js';
import { chips, showBlob } from './components.js';
import { s, tr, getLang, setLang, onLang, STRINGS } from './i18n.js';
import { buildBodyTab } from './tabs/body.js';
import { buildSkinTab } from './tabs/skin.js';
import { buildOutfitTab } from './tabs/outfit.js';
import { buildDynamicsTab } from './tabs/dynamics.js';
import { buildSceneTab } from './tabs/scene.js';
import { buildPresetsTab } from './tabs/presets.js';

const TABS = [
  ['body', buildBodyTab],
  ['skin', buildSkinTab],
  ['outfit', buildOutfitTab],
  ['dynamics', buildDynamicsTab],
  ['scene', buildSceneTab],
  ['presets', buildPresetsTab],
];

const QUICK_FOCUS = ['full', 'bust', 'waist', 'hips', 'glutes', 'thighs', 'legs'];
const FOCUS_SHORT = {
  full: { pt: 'Corpo', en: 'Full' },
  bust: { pt: 'Busto', en: 'Bust' },
  waist: { pt: 'Cintura', en: 'Waist' },
  hips: { pt: 'Quadril', en: 'Hips' },
  glutes: { pt: 'Costas', en: 'Back' },
  thighs: { pt: 'Coxas', en: 'Thighs' },
  legs: { pt: 'Pernas', en: 'Legs' },
};

export function createUI(app) {
  let current = 'body';
  try {
    current = localStorage.getItem('avatar-studio.tab') || 'body';
  } catch {}
  if (!TABS.some(([id]) => id === current)) current = 'body';
  let built = {};
  const dirty = new Set();
  const ui = h('div.ui');
  document.body.append(ui);

  const fitView = () => {
    const hidden = document.body.classList.contains('hidepanel');
    const mobile = window.innerWidth <= 760;
    if (hidden) app.engine.setViewShift(0, 0);
    else if (mobile) app.engine.setViewShift(0, window.innerHeight * 0.215);
    else app.engine.setViewShift(194, 0);
  };
  window.addEventListener('resize', fitView);
  const panelBody = h('div.panel-body');
  const panelTitle = h('div.panel-title');
  const panel = h('div.panel', h('div.panel-head', panelTitle), panelBody);

  const undoBtn = h('button.ibtn', { title: s('ui.undo') + ' (Ctrl+Z)', onclick: () => app.undo() }, '↶');
  const redoBtn = h('button.ibtn', { title: s('ui.redo') + ' (Ctrl+Y)', onclick: () => app.redo() }, '↷');
  const langBtn = h('button.ibtn', { title: s('ui.language'), onclick: () => setLang(getLang() === 'pt' ? 'en' : 'pt') }, getLang().toUpperCase());
  const hideBtn = h('button.ibtn', { title: 'Ocultar/mostrar painel', onclick: () => (document.body.classList.toggle('hidepanel'), fitView()) }, '◧');
  const shotBtn = h('button.ibtn', { title: s('ui.screenshot'), onclick: async () => showBlob(await app.screenshot(), 'avatar.png') }, '▣');
  const tabsEl = h('nav.tabs');
  const top = h('div.topbar', h('div.brand', h('i'), 'Avatar Studio', h('small', tr({ pt: 'torso e pernas', en: 'torso & legs' }))), tabsEl, h('div.topactions', undoBtn, redoBtn, shotBtn, hideBtn, langBtn));

  const focusChips = chips({ items: QUICK_FOCUS.map((id) => ({ id, label: FOCUS_SHORT[id] })), value: 'full', onPick: (id) => (app.focus(id), focusChips.set(id)) });
  const recoilChip = h('button.chip', { type: 'button', onclick: () => {
    app.setDyn('recoil', { enabled: !app.dyn.recoil.enabled });
    app.commit();
    paintRecoil();
    built.dynamics && dirty.add('dynamics');
  } });
  const paintRecoil = () => {
    recoilChip.textContent = `${s('ui.recoil')}: ${app.dyn.recoil.enabled ? s('ui.on') : s('ui.off')}`;
    recoilChip.classList.toggle('on', app.dyn.recoil.enabled);
  };
  const bottom = h('div.bottombar', h('div.pill', focusChips.el), h('div.pill.right', recoilChip));
  ui.append(top, panel, bottom);

  const paintHistory = () => {
    undoBtn.disabled = !app.canUndo;
    redoBtn.disabled = !app.canRedo;
  };
  const getTab = (id) => (built[id] ||= TABS.find(([i]) => i === id)[1](app));

  const show = (id, { focus = true } = {}) => {
    current = id;
    try {
      localStorage.setItem('avatar-studio.tab', id);
    } catch {}
    [...tabsEl.children].forEach((b) => b.classList.toggle('on', b.dataset.id === id));
    panelTitle.replaceChildren(h('span', s(`tabs.${id}`)));
    const tab = getTab(id);
    if (dirty.delete(id)) tab.refresh?.();
    panelBody.replaceChildren(tab.el);
    panelBody.scrollTop = 0;
    if (focus) tab.activate?.();
  };

  const buildTabs = () => {
    tabsEl.replaceChildren(...TABS.map(([id]) => h('button.tab', { type: 'button', dataset: { id }, onclick: () => show(id) }, s(`tabs.${id}`))));
  };
  buildTabs();
  paintRecoil();
  paintHistory();

  app.on('history', paintHistory);
  app.on('restore', () => {
    for (const id of Object.keys(built)) dirty.add(id);
    if (built[current]) {
      dirty.delete(current);
      built[current].refresh?.();
    }
    paintRecoil();
    paintHistory();
  });

  onLang(() => {
    built = {};
    langBtn.textContent = getLang().toUpperCase();
    undoBtn.title = s('ui.undo') + ' (Ctrl+Z)';
    redoBtn.title = s('ui.redo') + ' (Ctrl+Y)';
    focusChips.el.replaceWith((focusChips.el = chips({ items: QUICK_FOCUS.map((id) => ({ id, label: FOCUS_SHORT[id] })), value: 'full', onPick: (id) => app.focus(id) }).el));
    buildTabs();
    paintRecoil();
    show(current, { focus: false });
  });

  window.addEventListener('keydown', (e) => {
    if (/^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName) && e.target.type !== 'range') return;
    const mod = e.ctrlKey || e.metaKey;
    if (mod && e.key.toLowerCase() === 'z') {
      e.preventDefault();
      e.shiftKey ? app.redo() : app.undo();
    } else if (mod && e.key.toLowerCase() === 'y') {
      e.preventDefault();
      app.redo();
    }
  });

  fitView();
  show(current, { focus: false });
  void STRINGS;
  return { show };
}
