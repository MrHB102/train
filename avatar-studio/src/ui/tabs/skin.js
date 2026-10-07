// Aba Pele: tom, imperfeições (todas removíveis), acabamento e anatomia da superfície.
import { h } from '../dom.js';
import { slider, group, swatches, colorField, chips } from '../components.js';
import { tr } from '../i18n.js';
import { SKIN_TONES, SKIN_PARAMS, SKIN_PRESETS, defaultSkin } from '../../domain/skin.js';

export function buildSkinTab(app) {
  const root = h('div');
  const refreshers = [];
  const par = (id) => SKIN_PARAMS.find((p) => p.id === id);

  const sk = (p) => {
    const c = slider({
      label: p.label,
      min: p.min,
      max: p.max,
      step: p.step,
      neutral: p.def,
      value: app.skin[p.id],
      onInput: (v) => app.setSkin({ [p.id]: v }),
      onChange: () => app.commit(),
    });
    refreshers.push(() => c.set(app.skin[p.id]));
    return c.el;
  };

  // tom
  const gTone = group({ pt: 'Tom de pele', en: 'Skin tone' });
  const sw = swatches({
    items: SKIN_TONES,
    value: app.skin.toneId,
    onPick: (it) => {
      app.setSkin({ toneId: it.id, tone: it.color });
      app.commit();
      sw.set(it.id);
      custom.set(it.color);
    },
  });
  const custom = colorField({
    label: { pt: 'Cor personalizada', en: 'Custom color' },
    value: app.skin.tone,
    onInput: (v) => app.setSkin({ tone: v, toneId: 'custom' }),
    onChange: () => (app.commit(), sw.set('custom')),
  });
  gTone.body.append(sw.el, custom.el, sk(par('undertone')));
  refreshers.push(() => (sw.set(app.skin.toneId), custom.set(app.skin.tone)));

  // imperfeições
  const gImp = group({ pt: 'Imperfeições (poros, manchas, sardas…)', en: 'Imperfections (pores, blotches, freckles…)' });
  const master = slider({
    label: { pt: 'Pele perfeita (remove todas)', en: 'Flawless skin (removes all)' },
    hint: { pt: 'Tira poros, manchas, sardas, pintas, veias, vermelhidão e penugem de uma vez', en: 'Removes pores, blotches, freckles, moles, veins, redness and fuzz at once' },
    min: 0,
    max: 1,
    step: 0.01,
    neutral: 0,
    value: app.skin.smooth || 0,
    onInput: (v) => app.setSkin({ smooth: v }),
    onChange: () => app.commit(),
  });
  refreshers.push(() => master.set(app.skin.smooth || 0));
  gImp.body.append(master.el);
  for (const p of SKIN_PARAMS.filter((q) => q.imperfection)) gImp.body.append(sk(p));
  const presets = chips({
    items: SKIN_PRESETS.map((p) => ({ id: p.id, label: p.label })),
    value: '',
    onPick: (id) => {
      const pr = SKIN_PRESETS.find((p) => p.id === id);
      app.setSkin({ ...Object.fromEntries(SKIN_PARAMS.filter((q) => q.imperfection || q.id === 'oil').map((q) => [q.id, q.def])), smooth: 0, ...pr.patch });
      app.commit();
      refreshers.forEach((r) => r());
    },
  });
  gImp.body.prepend(presets.el);

  // acabamento
  const gFin = group({ pt: 'Acabamento', en: 'Finish' });
  for (const id of ['oil', 'sss', 'shimmer', 'nails']) gFin.body.append(sk(par(id)));
  const shimmerColor = colorField({ label: { pt: 'Cor do glitter', en: 'Glitter color' }, value: app.skin.shimmerColor, onInput: (v) => app.setSkin({ shimmerColor: v }), onChange: () => app.commit() });
  const nailColor = colorField({ label: { pt: 'Cor do esmalte', en: 'Polish color' }, value: app.skin.nailColor, onInput: (v) => app.setSkin({ nailColor: v }), onChange: () => app.commit() });
  gFin.body.append(shimmerColor.el, nailColor.el);
  refreshers.push(() => (shimmerColor.set(app.skin.shimmerColor), nailColor.set(app.skin.nailColor)));

  // anatomia
  const gAna = group({ pt: 'Anatomia (ossos, tendões, músculos)', en: 'Anatomy (bones, tendons, muscles)' });
  gAna.body.append(h('div.hint', tr({ pt: 'Relevo e sombra de clavículas, pescoço, abdômen, quadril e costas. Não muda a geometria.', en: 'Relief and shading of collarbones, neck, abdomen, hips and back. Does not change the geometry.' })));
  for (const p of SKIN_PARAMS.filter((q) => q.group === 'anatomy')) gAna.body.append(sk(p));

  root.append(gTone.el, gImp.el, gAna.el, gFin.el);
  return { el: root, refresh: () => refreshers.forEach((r) => r()), activate: () => app.focus('bust') };
}

export { defaultSkin };
