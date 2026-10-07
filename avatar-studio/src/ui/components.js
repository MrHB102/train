// Componentes da interface (sliders no estilo de criador de personagem, pad 2D, chips, interruptores…).
import { h } from './dom.js';
import { s, tr } from './i18n.js';

const clamp = (x, a, b) => Math.min(b, Math.max(a, x));

/**
 * Slider: mostra 0–100 (posição na faixa estendida); a marca "limite natural" mostra onde termina o
 * realista. Duplo clique no rótulo (ou ↺) volta ao neutro.
 * spec: { label, min, max, value, step, neutral, natural:[a,b], format(v), hint, onInput(v), onChange(v) }
 */
export function slider(spec) {
  const { min, max } = spec;
  const step = spec.step ?? (max - min) / 200;
  const pct = (v) => ((clamp(v, min, max) - min) / (max - min)) * 100;
  const fmt = spec.format || ((v) => String(Math.round(pct(v))));
  const input = h('input', { type: 'range', min, max, step, value: spec.value ?? spec.neutral ?? min, 'aria-label': tr(spec.label) });
  const out = h('output.sval');
  const reset = h('button.sreset', { title: s('ui.reset'), type: 'button', tabIndex: -1 }, '↺');
  const rail = h('div.rail', h('div.fill'), input);
  const row = h(
    'div.srow',
    { title: tr(spec.hint) || undefined },
    h('div.slabel', h('span.stxt', { ondblclick: () => doReset() }, tr(spec.label)), reset, out),
    h(
      'div.strack',
      h('button.sarrow', { type: 'button', tabIndex: -1, onclick: () => nudge(-1) }, '‹'),
      rail,
      h('button.sarrow', { type: 'button', tabIndex: -1, onclick: () => nudge(1) }, '›')
    )
  );
  if (spec.natural && spec.natural[1] < max - 1e-6) rail.append(h('div.mark.nat', { style: { left: pct(spec.natural[1]) + '%' }, title: s('ui.natural') }));
  if (spec.natural && spec.natural[0] > min + 1e-6) rail.append(h('div.mark.nat', { style: { left: pct(spec.natural[0]) + '%' }, title: s('ui.natural') }));
  if (spec.neutral !== undefined) rail.append(h('div.mark.neu', { style: { left: pct(spec.neutral) + '%' }, title: s('ui.neutral') }));

  const paint = () => {
    const v = +input.value;
    row.style.setProperty('--p', pct(v) + '%');
    out.textContent = fmt(v);
    row.classList.toggle('beyond', !!spec.natural && (v > spec.natural[1] + 1e-6 || v < spec.natural[0] - 1e-6));
    row.classList.toggle('changed', spec.neutral !== undefined && Math.abs(v - spec.neutral) > (max - min) * 0.004);
  };
  const doReset = () => {
    if (spec.neutral === undefined) return;
    input.value = spec.neutral;
    paint();
    spec.onInput?.(+input.value);
    spec.onChange?.(+input.value);
  };
  const nudge = (d) => {
    input.value = clamp(+input.value + d * (max - min) * 0.01, min, max);
    paint();
    spec.onInput?.(+input.value);
    spec.onChange?.(+input.value);
  };
  reset.addEventListener('click', doReset);
  input.addEventListener('input', () => {
    paint();
    spec.onInput?.(+input.value);
  });
  input.addEventListener('change', () => spec.onChange?.(+input.value));
  paint();
  return {
    el: row,
    set(v) {
      input.value = v;
      paint();
    },
    get: () => +input.value,
  };
}

/** Pad 2D (x, y) em [0,1]²: posição do busto, por exemplo. */
export function pad2d({ label, x, y, onInput, onChange, hint }) {
  let vx = x.value ?? 0.5;
  let vy = y.value ?? 0.5;
  const dot = h('div.pdot');
  const box = h('div.pad', { tabIndex: 0 }, h('div.pcross.v'), h('div.pcross.h'), dot);
  const paint = () => {
    dot.style.left = ((vx - x.min) / (x.max - x.min)) * 100 + '%';
    dot.style.top = (1 - (vy - y.min) / (y.max - y.min)) * 100 + '%';
  };
  const pick = (e) => {
    const r = box.getBoundingClientRect();
    vx = x.min + clamp((e.clientX - r.left) / r.width, 0, 1) * (x.max - x.min);
    vy = y.min + (1 - clamp((e.clientY - r.top) / r.height, 0, 1)) * (y.max - y.min);
    paint();
    onInput?.(vx, vy);
  };
  box.addEventListener('pointerdown', (e) => {
    box.setPointerCapture(e.pointerId);
    pick(e);
    const move = (ev) => pick(ev);
    const up = () => {
      box.removeEventListener('pointermove', move);
      box.removeEventListener('pointerup', up);
      onChange?.(vx, vy);
    };
    box.addEventListener('pointermove', move);
    box.addEventListener('pointerup', up);
  });
  box.addEventListener('dblclick', () => {
    vx = x.neutral ?? (x.min + x.max) / 2;
    vy = y.neutral ?? (y.min + y.max) / 2;
    paint();
    onInput?.(vx, vy);
    onChange?.(vx, vy);
  });
  paint();
  const el = h('div.padwrap', { title: tr(hint) || undefined }, h('div.plabel', tr(label)), box);
  return {
    el,
    set(a, b) {
      vx = a;
      vy = b;
      paint();
    },
  };
}

export function toggle({ label, value, onChange, hint }) {
  const input = h('input', { type: 'checkbox', checked: !!value });
  const el = h('label.toggle', { title: tr(hint) || undefined }, h('span.stxt', tr(label)), input, h('span.knob'));
  input.addEventListener('change', () => onChange?.(input.checked));
  return { el, set: (v) => (input.checked = !!v), get: () => input.checked };
}

export function select({ label, options, value, onChange }) {
  const sel = h(
    'select',
    options.map((o) => h('option', { value: o.id, selected: o.id === value }, tr(o.label)))
  );
  sel.addEventListener('change', () => onChange?.(sel.value));
  const el = h('label.selrow', h('span.stxt', tr(label)), sel);
  return { el, set: (v) => (sel.value = v), get: () => sel.value, setOptions: (opts) => sel.replaceChildren(...opts.map((o) => h('option', { value: o.id }, tr(o.label)))) };
}

/** Pílulas de escolha única. */
export function chips({ items, value, onPick, cls = '' }) {
  const btns = items.map((it) =>
    h('button.chip', { type: 'button', dataset: { id: it.id }, onclick: () => onPick?.(it.id) }, it.icon ? h('span.cicon', it.icon) : null, tr(it.label))
  );
  const el = h('div.chips ' + cls, btns);
  const set = (v) => btns.forEach((b) => b.classList.toggle('on', b.dataset.id === v));
  set(value);
  return { el, set };
}

export function swatches({ items, value, onPick }) {
  const btns = items.map((it) => h('button.swatch', { type: 'button', title: tr(it.label), dataset: { id: it.id }, style: { background: it.color }, onclick: () => onPick?.(it) }));
  const el = h('div.swatches', btns);
  return { el, set: (v) => btns.forEach((b) => b.classList.toggle('on', b.dataset.id === v)) };
}

export function colorField({ label, value, onInput, onChange }) {
  const input = h('input', { type: 'color', value: value || '#ffffff' });
  input.addEventListener('input', () => onInput?.(input.value));
  input.addEventListener('change', () => onChange?.(input.value));
  const el = h('label.colorrow', h('span.stxt', tr(label)), input);
  return { el, set: (v) => (input.value = v) };
}

export function button(label, onclick, cls = '') {
  return h('button.btn ' + cls, { type: 'button', onclick }, label);
}

/** Seção recolhível. */
export function group(title, { open = true } = {}) {
  const body = h('div.gbody');
  const head = h('button.ghead', { type: 'button' }, h('span', tr(title)), h('span.gcar', '▾'));
  const el = h('section.group', head, body);
  if (!open) el.classList.add('closed');
  head.addEventListener('click', () => el.classList.toggle('closed'));
  return { el, body, setTitle: (t) => (head.firstChild.textContent = tr(t)) };
}

export function toast(msg, ms = 2200) {
  const t = h('div.toast', msg);
  document.body.append(t);
  requestAnimationFrame(() => t.classList.add('show'));
  setTimeout(() => {
    t.classList.remove('show');
    setTimeout(() => t.remove(), 300);
  }, ms);
}
