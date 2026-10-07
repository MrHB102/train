// Aba Presets: personagens prontos (do natural ao gigante), salvar/carregar, compartilhar, exportar e captura.
import { h } from '../dom.js';
import { group, button, toast, select, showBlob } from '../components.js';
import { tr, s } from '../i18n.js';
import { CHARACTER_PRESETS } from '../../domain/presets.js';

const KEY = 'avatar-studio.slots';
const readSlots = () => {
  try {
    return JSON.parse(localStorage.getItem(KEY) || '[]');
  } catch {
    return [];
  }
};
const writeSlots = (a) => {
  try {
    localStorage.setItem(KEY, JSON.stringify(a));
  } catch {}
};

export function buildPresetsTab(app) {
  const root = h('div');

  const gP = group({ pt: 'Personagens prontos', en: 'Character presets' });
  const grid = h('div.cardgrid');
  for (const p of CHARACTER_PRESETS) {
    grid.append(h('button.card', { type: 'button', onclick: () => app.applyBodyPreset(p) }, h('b', tr(p.label)), h('small', tr(p.hint))));
  }
  gP.body.append(grid, h('div.btnrow', button(s('ui.random'), () => app.randomize()), button(s('ui.resetAll'), () => app.resetAll())));

  // salvar / carregar
  const gS = group({ pt: 'Meus personagens (neste navegador)', en: 'My characters (this browser)' });
  const list = h('div');
  const nameIn = h('input', { type: 'text', placeholder: tr({ pt: 'Nome do personagem', en: 'Character name' }), style: { flex: '1' } });
  const renderSlots = () => {
    list.replaceChildren();
    const slots = readSlots();
    if (!slots.length) list.append(h('div.hint', tr({ pt: 'Nada salvo ainda.', en: 'Nothing saved yet.' })));
    slots.forEach((sl, i) => {
      list.append(
        h(
          'div.btnrow',
          { style: { alignItems: 'center' } },
          h('span', { style: { flex: '1' } }, sl.name),
          button(s('ui.load'), () => (app.restore(sl.data), toast(sl.name))),
          button('✕', () => {
            slots.splice(i, 1);
            writeSlots(slots);
            renderSlots();
          })
        )
      );
    });
  };
  gS.body.append(
    h(
      'div.btnrow',
      nameIn,
      button(s('ui.save'), () => {
        const slots = readSlots();
        slots.push({ name: nameIn.value.trim() || `${tr({ pt: 'Personagem', en: 'Character' })} ${slots.length + 1}`, data: app.serialize() });
        writeSlots(slots);
        nameIn.value = '';
        renderSlots();
        toast(tr({ pt: 'Salvo!', en: 'Saved!' }));
      })
    ),
    list
  );
  renderSlots();

  // compartilhar
  const gC = group({ pt: 'Compartilhar', en: 'Share' });
  const code = h('textarea', { placeholder: tr({ pt: 'Cole aqui um código para carregar…', en: 'Paste a code here to load…' }) });
  gC.body.append(
    code,
    h(
      'div.btnrow',
      button(s('ui.copyCode'), async () => {
        code.value = app.shareCode();
        try {
          await navigator.clipboard.writeText(code.value);
          toast(tr({ pt: 'Código copiado', en: 'Code copied' }));
        } catch {
          code.select();
        }
      }),
      button(s('ui.pasteCode'), () => {
        try {
          app.loadCode(code.value);
          toast(tr({ pt: 'Carregado!', en: 'Loaded!' }));
        } catch {
          toast(tr({ pt: 'Código inválido', en: 'Invalid code' }));
        }
      }),
      button('JSON', () => showBlob(new Blob([JSON.stringify(app.serialize(), null, 2)], { type: 'application/json' }), 'avatar.json'))
    )
  );

  // captura
  const gX = group({ pt: 'Exportar', en: 'Export' });
  gX.body.append(
    h(
      'div.btnrow',
      button(s('ui.screenshot'), async () => showBlob(await app.screenshot(), 'avatar.png'))
    )
  );
  root.append(gP.el, gS.el, gC.el, gX.el);
  void select;
  return { el: root, refresh: () => renderSlots(), activate: () => app.focus('full') };
}
