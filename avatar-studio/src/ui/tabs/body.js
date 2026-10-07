// Aba Corpo: regiões (busto, cintura, quadril, glúteos, coxas, pernas…) com sliders 0–100 sobre a faixa
// estendida (a marca laranja é o limite natural; além dela é o modo exagerado) e estilos rápidos.
import { h } from '../dom.js';
import { slider, pad2d, chips, group } from '../components.js';
import { s, STRINGS } from '../i18n.js';
import { TRAIT_BY_ID } from '../../domain/traits.js';
import { DIAL_BY_ID } from '../../domain/dials.js';

const T = (id) => ({ kind: 'trait', id });
const D = (id) => ({ kind: 'dial', id });

// o que cada região mostra, em ordem de importância; { title, items }
const REGIONS = {
  general: {
    focus: 'full',
    sections: [
      { title: { pt: 'Estilos rápidos', en: 'Quick styles' }, items: [D('curves'), D('anime'), D('tone'), D('bombshell')] },
      { title: { pt: 'Corpo todo', en: 'Whole body' }, items: [T('height'), T('weight'), T('muscle'), T('proportions'), T('age')] },
      { title: { pt: 'Silhueta', en: 'Silhouette' }, open: false, items: ['silhouette'] },
      { title: { pt: 'Morfologia (mistura)', en: 'Morphology (mix)' }, open: false, items: [T('ancestry.african'), T('ancestry.asian'), T('ancestry.caucasian')] },
    ],
  },
  bust: {
    focus: 'bust',
    pad: 'bust',
    sections: [
      { title: { pt: 'Tamanho e forma', en: 'Size & shape' }, items: [D('bustSize'), T('bust.firmness'), T('bust.extraVolume'), T('bust.upperFullness'), T('bust.projection')] },
      { title: { pt: 'Posição', en: 'Position' }, items: [T('bust.height'), T('bust.spacing'), T('bust.asymmetry'), T('bust.contact')] },
      { title: { pt: 'Medidas', en: 'Measurements' }, open: false, items: [T('bust.circumference'), T('bust.underbust'), T('bust.size')] },
    ],
  },
  waist: {
    focus: 'waist',
    sections: [
      { title: { pt: 'Cintura', en: 'Waist' }, items: [T('waist.width'), T('waist.height'), T('waist.torsoLength'), T('waist.toHip')] },
      { title: { pt: 'Barriga', en: 'Belly' }, items: [T('belly.volume'), T('belly.tone'), T('belly.navelHeight'), T('belly.navelDepth')] },
      { title: { pt: 'Tronco', en: 'Torso' }, open: false, items: [T('torso.width'), T('torso.depth'), T('torso.length'), T('torso.posture')] },
    ],
  },
  hips: {
    focus: 'hips',
    sections: [
      { title: { pt: 'Quadril', en: 'Hips' }, items: [D('hipSize'), T('hips.width'), T('hips.circumference'), T('hips.depth'), T('hips.height')] },
      { title: { pt: 'Posição', en: 'Position' }, items: [T('hips.forward'), T('hips.lift'), T('hips.tone')] },
    ],
  },
  glutes: {
    focus: 'glutes',
    sections: [
      { title: { pt: 'Tamanho e forma', en: 'Size & shape' }, items: [D('glutesSize'), T('glutes.volume'), T('glutes.extraVolume')] },
      { title: { pt: 'Caimento e dobras', en: 'Lift & folds' }, items: [T('glutes.lift'), T('glutes.fold'), T('glutes.cleft')] },
    ],
  },
  thighs: {
    focus: 'thighs',
    sections: [
      { title: { pt: 'Volume', en: 'Volume' }, items: [D('thickness'), T('thighs.upperVolume'), T('thighs.extraVolume'), T('thighs.fullness'), T('thighs.contact')] },
      { title: { pt: 'Forma', en: 'Shape' }, items: [T('thighs.muscle'), T('thighs.width'), T('thighs.depth'), T('thighs.circumference'), T('thighs.length'), T('thighs.valgus')] },
    ],
  },
  legs: {
    focus: 'legs',
    sections: [
      { title: { pt: 'Joelhos e panturrilhas', en: 'Knees & calves' }, items: [T('knees.size'), T('calves.fullness'), T('calves.muscle'), T('calves.width'), T('calves.circumference'), T('calves.length')] },
      { title: { pt: 'Tornozelos e pés', en: 'Ankles & feet' }, items: [T('ankles.size'), T('feet.size'), T('feet.width'), T('feet.length'), T('feet.arch')] },
    ],
  },
  upper: {
    focus: 'neck',
    sections: [
      { title: { pt: 'Ombros e pescoço', en: 'Shoulders & neck' }, items: [T('shoulders.width'), T('neck.length'), T('neck.thickness'), T('neck.forward')] },
      { title: { pt: 'Costas e peito', en: 'Back & chest' }, items: [T('torso.vshape'), T('torso.back'), T('torso.chestMuscle'), T('torso.chestWidth')] },
    ],
  },
};
const REGION_ORDER = ['general', 'bust', 'waist', 'hips', 'glutes', 'thighs', 'legs', 'upper'];

export function buildBodyTab(app) {
  const root = h('div');
  const refreshers = [];
  let region = 'general';
  const autoFocus = true;

  const makeSlider = (item) => {
    if (item.kind === 'dial') {
      const d = DIAL_BY_ID[item.id];
      const c = slider({
        label: d.label,
        hint: d.hint,
        min: d.extended[0],
        max: d.extended[1],
        neutral: d.neutral,
        natural: d.natural,
        value: app.dial(d.id),
        onInput: (v) => app.setDial(d.id, v),
        onChange: () => app.commit(),
      });
      refreshers.push(() => c.set(app.dial(d.id)));
      return c.el;
    }
    const t = TRAIT_BY_ID[item.id];
    const isAge = t.id === 'age';
    const c = slider({
      label: t.label,
      hint: t.hint,
      min: t.extended[0],
      max: t.extended[1],
      neutral: t.neutral,
      natural: t.natural,
      step: t.step,
      format: isAge ? (v) => `${Math.round(v)} ${s('ui.years')}` : t.runtime ? (v) => `${Math.round(v * 100)}` : undefined,
      value: app.trait(t.id),
      onInput: (v) => app.setTrait(t.id, v),
      onChange: () => app.commit(),
    });
    refreshers.push(() => c.set(app.trait(t.id)));
    return c.el;
  };

  const render = () => {
    root.replaceChildren();
    refreshers.length = 0;
    const cfg = REGIONS[region];
    for (const sec of cfg.sections) {
      const g = group(sec.title, { open: sec.open !== false });
      for (const it of sec.items) {
        if (it === 'silhouette') {
          for (const t of Object.values(TRAIT_BY_ID).filter((x) => x.group === 'silhouette')) g.body.append(makeSlider(T(t.id)));
        } else g.body.append(makeSlider(it));
      }
      root.append(g.el);
    }
    if (cfg.pad === 'bust') {
      const sp = TRAIT_BY_ID['bust.spacing'];
      const hg = TRAIT_BY_ID['bust.height'];
      const pad = pad2d({
        label: { pt: 'Posição do busto', en: 'Bust position' },
        hint: { pt: 'Arraste: horizontal = separação, vertical = altura', en: 'Drag: horizontal = spacing, vertical = height' },
        x: { min: sp.extended[0], max: sp.extended[1], value: app.trait('bust.spacing'), neutral: 0 },
        y: { min: hg.extended[0], max: hg.extended[1], value: app.trait('bust.height'), neutral: 0 },
        onInput: (x, y) => {
          app.setTrait('bust.spacing', x);
          app.setTrait('bust.height', y);
        },
        onChange: () => {
          app.commit();
          refreshers.forEach((r) => r());
        },
      });
      refreshers.push(() => pad.set(app.trait('bust.spacing'), app.trait('bust.height')));
      const g = group({ pt: 'Painel de posição', en: 'Position pad' });
      g.body.append(pad.el);
      root.append(g.el);
    }
  };

  const chipsEl = chips({
    items: REGION_ORDER.map((id) => ({ id, label: STRINGS.regions[id] })),
    value: region,
    onPick: (id) => {
      region = id;
      chipsEl.set(id);
      render();
      if (autoFocus) app.focus(REGIONS[id].focus);
    },
  });
  const el = h('div', h('div.panel-subhead', { style: { padding: '8px 0 2px' } }, chipsEl.el), root);
  render();
  return {
    el,
    refresh: () => refreshers.forEach((r) => r()),
    activate: () => app.focus(REGIONS[region].focus),
  };
}
