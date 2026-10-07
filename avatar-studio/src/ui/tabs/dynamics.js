// Aba Dinâmica: repique elástico ao mudar o corpo, balanço da carne (Jiggle) e tecidos simulados.
import { h } from '../dom.js';
import { slider, toggle, group, button } from '../components.js';
import { tr } from '../i18n.js';

export function buildDynamicsTab(app) {
  const root = h('div');
  const refreshers = [];
  const sl = (label, grp, key, min, max, def, hint) => {
    const c = slider({ label, hint, min, max, step: 0.01, neutral: def, value: app.dyn[grp][key], onInput: (v) => app.setDyn(grp, { [key]: v }), onChange: () => app.commit() });
    refreshers.push(() => c.set(app.dyn[grp][key]));
    return c.el;
  };
  const tg = (label, grp, key, hint) => {
    const c = toggle({ label, hint, value: app.dyn[grp][key], onChange: (v) => (app.setDyn(grp, { [key]: v }), app.commit()) });
    refreshers.push(() => c.set(app.dyn[grp][key]));
    return c.el;
  };

  const gR = group({ pt: 'Repique elástico', en: 'Elastic recoil' });
  gR.body.append(
    tg({ pt: 'Repique ao mudar o corpo', en: 'Recoil when the body changes' }, 'recoil', 'enabled', { pt: 'O corpo cresce passando do ponto e volta, com balanço', en: 'The body overshoots and settles back, with wobble' }),
    sl({ pt: 'Intensidade do repique', en: 'Recoil strength' }, 'recoil', 'amount', 0, 2.5, 1, { pt: '0 = sem overshoot · 1 = padrão · 2.5 = exagerado (desenho animado)', en: '0 = none · 1 = default · 2.5 = cartoon' }),
    button(tr({ pt: 'Testar repique', en: 'Test recoil' }), () => {
      const v = app.dial('bustSize');
      app.elastic.set({ dials: { bustSize: v > 1.5 ? 0 : 3 } });
      setTimeout(() => app.elastic.set({ dials: { bustSize: v } }), 1600);
    })
  );
  const gJ = group({ pt: 'Balanço da carne (Jiggle)', en: 'Soft-tissue wobble (Jiggle)' });
  gJ.body.append(
    tg({ pt: 'Física do corpo ligada', en: 'Body physics on' }, 'jiggle', 'enabled'),
    sl({ pt: 'Busto', en: 'Bust' }, 'jiggle', 'bust', 0, 2.5, 1),
    sl({ pt: 'Glúteos', en: 'Glutes' }, 'jiggle', 'glutes', 0, 2.5, 1),
    sl({ pt: 'Coxas', en: 'Thighs' }, 'jiggle', 'thighs', 0, 2.5, 1),
    sl({ pt: 'Barriga', en: 'Belly' }, 'jiggle', 'belly', 0, 2.5, 1),
    sl({ pt: 'Amortecimento', en: 'Damping' }, 'jiggle', 'damping', 0.3, 2.2, 1, { pt: 'Quanto a carne demora a parar', en: 'How quickly the wobble dies out' }),
    sl({ pt: 'Firmeza (rigidez da mola)', en: 'Firmness (spring stiffness)' }, 'jiggle', 'stiffness', 0.5, 2.2, 1)
  );
  const gC = group({ pt: 'Tecidos simulados', en: 'Simulated cloth' });
  gC.body.append(
    sl({ pt: 'Vento', en: 'Wind' }, 'cloth', 'wind', 0, 8, 0),
    sl({ pt: 'Rigidez do tecido', en: 'Fabric stiffness' }, 'cloth', 'stiffness', 0.3, 2.5, 1)
  );
  root.append(gR.el, gJ.el, gC.el);
  return { el: root, refresh: () => refreshers.forEach((r) => r()), activate: () => app.focus('bust') };
}
