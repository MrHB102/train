// Aba Roupas: conjuntos prontos (bunny girl, maid, colegial…), biquíni-base e peças vestidas com
// tecido, cor, padrão, acabamento e medidas editáveis.
import { h } from '../dom.js';
import { slider, toggle, select, chips, group, colorField, button } from '../components.js';
import { tr } from '../i18n.js';
import { FABRICS, PATTERNS, TRIMS } from '../../shaders/fabric.js';
import { GARMENT_TYPES, OUTFITS, SLOTS } from '../../domain/wardrobe.js';

const fabricOptions = Object.entries(FABRICS).map(([id, f]) => ({ id, label: { pt: f.pt, en: f.en } }));

/** Editor de tecido: tecido, cores, padrão, acabamento e costuras. */
function styleEditor(app, getStyle, setStyle) {
  const box = h('div');
  const st = () => getStyle();
  const rows = [];
  const add = (c, key, visible) => {
    rows.push({ c, key, visible });
    box.append(c.el);
    return c;
  };
  const apply = (patch) => {
    setStyle(patch);
    sync();
  };
  const fab = add(select({ label: { pt: 'Tecido', en: 'Fabric' }, options: fabricOptions, value: st().fabric, onChange: (v) => (apply({ fabric: v }), app.commit()) }), 'fabric');
  const col = add(colorField({ label: { pt: 'Cor', en: 'Color' }, value: st().color, onInput: (v) => apply({ color: v }), onChange: () => app.commit() }), 'color');
  const pat = add(select({ label: { pt: 'Padrão', en: 'Pattern' }, options: PATTERNS.map((p) => ({ id: p.id, label: { pt: p.pt, en: p.en } })), value: st().pattern, onChange: (v) => (apply({ pattern: v }), app.commit()) }), 'pattern');
  const col2 = add(colorField({ label: { pt: 'Cor do padrão', en: 'Pattern color' }, value: st().color2, onInput: (v) => apply({ color2: v }), onChange: () => app.commit() }), 'color2', () => st().pattern !== 'none');
  const trim = add(select({ label: { pt: 'Acabamento', en: 'Trim' }, options: TRIMS.map((p) => ({ id: p.id, label: { pt: p.pt, en: p.en } })), value: st().trim, onChange: (v) => (apply({ trim: v }), app.commit()) }), 'trim');
  const trimCol = add(colorField({ label: { pt: 'Cor do acabamento', en: 'Trim color' }, value: st().trimColor, onInput: (v) => apply({ trimColor: v }), onChange: () => app.commit() }), 'trimColor', () => st().trim !== 'none');
  const trimW = add(
    slider({ label: { pt: 'Largura do acabamento', en: 'Trim width' }, min: 0.003, max: 0.05, step: 0.001, neutral: 0.012, format: (v) => `${(v * 1000).toFixed(0)} mm`, value: st().trimWidth, onInput: (v) => apply({ trimWidth: v }), onChange: () => app.commit() }),
    'trimWidth',
    () => st().trim !== 'none'
  );
  const seams = add(slider({ label: { pt: 'Costuras', en: 'Seams' }, min: 0, max: 1, step: 0.01, neutral: 0, value: st().seams, onInput: (v) => apply({ seams: v }), onChange: () => app.commit() }), 'seams');
  const seamCol = add(colorField({ label: { pt: 'Cor das costuras', en: 'Seam color' }, value: st().seamColor, onInput: (v) => apply({ seamColor: v }), onChange: () => app.commit() }), 'seamColor', () => st().seams > 0);
  const scale = add(slider({ label: { pt: 'Escala do padrão', en: 'Pattern scale' }, min: 0.4, max: 3, step: 0.01, neutral: 1, value: st().scale, onInput: (v) => apply({ scale: v }), onChange: () => app.commit() }), 'scale', () => st().pattern !== 'none' || ['lace', 'fishnet'].includes(st().fabric));
  const denier = add(slider({ label: { pt: 'Opacidade (transparência)', en: 'Opacity (sheerness)' }, min: 0.05, max: 1, step: 0.01, neutral: 0.3, value: st().denier, onInput: (v) => apply({ denier: v }), onChange: () => app.commit() }), 'denier', () => st().fabric === 'sheer');
  const cell = add(slider({ label: { pt: 'Tamanho da malha', en: 'Mesh size' }, min: 0.002, max: 0.02, step: 0.0005, neutral: 0.0042, format: (v) => `${(v * 1000).toFixed(1)} mm`, value: st().cell, onInput: (v) => apply({ cell: v }), onChange: () => app.commit() }), 'cell', () => ['fishnet', 'lace'].includes(st().fabric));
  const sync = () => {
    const s = st();
    for (const r of rows) r.c.el.style.display = !r.visible || r.visible() ? '' : 'none';
    fab.set(s.fabric); col.set(s.color); pat.set(s.pattern); col2.set(s.color2); trim.set(s.trim); trimCol.set(s.trimColor);
    trimW.set(s.trimWidth); seams.set(s.seams); seamCol.set(s.seamColor); scale.set(s.scale); denier.set(s.denier); cell.set(s.cell);
  };
  sync();
  return { el: box, sync };
}

/** Controles das opções (geometria) de um tipo de peça. */
function optionControls(app, def, getOpt, setOpt) {
  const box = h('div');
  for (const o of def.options) {
    if (o.type === 'range') {
      box.append(slider({ label: o.label, min: o.min, max: o.max, step: o.step, neutral: o.def, value: getOpt(o.id), format: o.format, onInput: (v) => setOpt({ [o.id]: v }), onChange: () => app.commit() }).el);
    } else if (o.type === 'toggle') {
      box.append(toggle({ label: o.label, value: getOpt(o.id), onChange: (v) => (setOpt({ [o.id]: v }), app.commit()) }).el);
    } else if (o.type === 'choice') {
      const c = chips({ items: o.items.map((it) => ({ id: String(it.id), label: { pt: it.pt, en: it.en } })), value: String(getOpt(o.id)), onPick: (id) => (setOpt({ [o.id]: +id }), c.set(id), app.commit()) });
      box.append(h('div.plabel', { style: { marginTop: '6px' } }, tr(o.label)), c.el);
    }
  }
  return box;
}

export function buildOutfitTab(app) {
  const root = h('div');
  const dr = app.dresser;

  // ---- conjuntos prontos
  const gSets = group({ pt: 'Conjuntos prontos', en: 'Ready-made outfits' });
  const grid = h('div.cardgrid');
  for (const o of OUTFITS) {
    grid.append(h('button.card', { type: 'button', onclick: () => (dr.applyOutfit(o.id), app.commit()) }, h('b', tr(o.label)), h('small', o.items.length ? o.items.map((i) => tr(GARMENT_TYPES[i.type].label)).slice(0, 3).join(' · ') : tr({ pt: 'Só o biquíni', en: 'Bikini only' }))));
  }
  gSets.body.append(grid, h('div.btnrow', button(tr({ pt: 'Tirar todas as peças', en: 'Remove all garments' }), () => (dr.clear(), app.commit()))));

  // ---- camada-base
  const gBase = group({ pt: 'Biquíni (camada-base)', en: 'Bikini (base layer)' });
  gBase.body.append(h('div.hint', tr({ pt: 'Sempre por baixo de tudo: o corpo nunca fica sem roupa.', en: 'Always underneath: the body is never left bare.' })));
  for (const which of ['top', 'bottom']) {
    const e = dr.base[which];
    const title = which === 'top' ? { pt: 'Parte de cima', en: 'Top' } : { pt: 'Parte de baixo', en: 'Bottom' };
    const sub = h('div.garment', h('div.gtitle', h('span', tr(title))));
    const styleChips = chips({
      items: which === 'top' ? [{ id: 'triangle', label: { pt: 'Triângulo', en: 'Triangle' } }, { id: 'bandeau', label: { pt: 'Faixa (bandeau)', en: 'Bandeau' } }] : [{ id: 'bikini', label: { pt: 'Biquíni clássico', en: 'Classic bikini' } }, { id: 'boy', label: { pt: 'Boyshort', en: 'Boyshort' } }],
      value: e.options.style,
      onPick: (id) => (dr.setBase(which, { style: id }), styleChips.set(id), app.commit()),
    });
    sub.append(styleChips.el);
    const ranges =
      which === 'top'
        ? [['padding', { pt: 'Enchimento (0 = tecido fino que marca o contorno)', en: 'Padding (0 = thin fabric tracing the form)' }, 0, 1, 0, 0.01], ['cover', { pt: 'Cobertura do triângulo', en: 'Triangle coverage' }, 0.85, 1.4, 1, 0.01]]
        : [['rise', { pt: 'Altura da cintura', en: 'Waist rise' }, -0.03, 0.07, 0, 0.001], ['cut', { pt: 'Cavado da perna', en: 'Leg cut' }, 0, 1, 0.5, 0.01], ['backCover', { pt: 'Cobertura atrás', en: 'Back coverage' }, 0, 1, 0.6, 0.01]];
    for (const [id, label, min, max, def, step] of ranges) sub.append(slider({ label, min, max, step, neutral: def, value: e.options[id], onInput: (v) => dr.setBase(which, { [id]: v }), onChange: () => app.commit() }).el);
    sub.append(styleEditor(app, () => dr.base[which].style, (p) => dr.setBase(which, p)).el);
    gBase.body.append(sub);
  }

  // ---- peças vestidas
  const gWorn = group({ pt: 'Peças vestidas', en: 'Worn garments' });
  const worn = h('div');
  gWorn.body.append(worn);
  let sig = '';
  const renderWorn = () => {
    const entries = [...dr.entries.values()];
    worn.replaceChildren();
    if (!entries.length) worn.append(h('div.hint', tr({ pt: 'Nenhuma peça: só o biquíni. Escolha um conjunto ou adicione peças abaixo.', en: 'No garments: bikini only. Pick an outfit or add pieces below.' })));
    for (const e of entries) {
      const def = GARMENT_TYPES[e.type];
      const box = h(
        'div.garment',
        h('div.gtitle', h('span', tr(def.label)), h('button', { title: tr({ pt: 'Remover', en: 'Remove' }), onclick: () => (dr.removeSlot(def.slot), app.commit()) }, '✕')),
        optionControls(app, def, (id) => dr.entries.get(def.slot)?.options[id], (patch) => dr.setItemOptions(def.slot, patch)),
        styleEditor(app, () => dr.entries.get(def.slot).style, (p) => dr.setItemStyle(def.slot, p)).el
      );
      worn.append(box);
    }
  };
  const update = () => {
    const ns = [...dr.entries.values()].map((e) => e.slot + ':' + e.type).join(',');
    if (ns !== sig) {
      sig = ns;
      renderWorn();
    }
  };
  dr.onChange(update);
  update();

  // ---- adicionar peça
  const gAdd = group({ pt: 'Adicionar peça', en: 'Add garment' });
  const bySlot = {};
  for (const [type, def] of Object.entries(GARMENT_TYPES)) {
    if (def.slot === 'baseTop' || def.slot === 'baseBottom') continue;
    (bySlot[def.slot] ||= []).push(type);
  }
  for (const slot of SLOTS) {
    if (!bySlot[slot.id]) continue;
    gAdd.body.append(
      h('div.plabel', { style: { marginTop: '6px' } }, tr(slot)),
      chips({ items: bySlot[slot.id].map((t) => ({ id: t, label: GARMENT_TYPES[t].label })), value: '', onPick: (t) => (dr.addItem(t), app.commit()) }).el
    );
  }
  root.append(gSets.el, gBase.el, gWorn.el, gAdd.el);
  return {
    el: root,
    refresh: () => {
      sig = '';
      update();
    },
    activate: () => app.focus('full'),
  };
}
