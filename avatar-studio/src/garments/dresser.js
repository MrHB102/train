// Dresser: gerencia a camada-base (biquíni) e as peças do Outfit.
//
//  - Cada peça é uma Entry { id, type, style, options, mat, parts[] } num slot (uma peça por slot;
//    'onepiece' ocupa 'top' + 'bottom'). O estilo (tecido, cor, padrão…) só mexe no material; as opções
//    (altura, decote, volume…) reconstroem a geometria.
//  - Uma peça é feita de partes: Shell (recortado da superfície), Ribbon (cordão/alça), Drape (tecido
//    simulado) e objetos livres (laço, rabo…). Os builders ficam em builders.js.
//  - A camada-base nunca some, mas esconde-se sob peças opacas: ela é recortada para dentro da peça por
//    cima (senão apareceria uma faixa clara acima de um decote mais baixo, por exemplo).
import { FabricMaterial } from '../shaders/fabric.js';
import { GARMENT_TYPES, OUTFIT_BY_ID, defaultItem, expandOutfit } from '../domain/wardrobe.js';
import { BUILDERS } from './builders.js';

const SLOT_EXCLUDES = {
  onepiece: ['top', 'bottom'],
  top: ['onepiece'],
  bottom: ['onepiece'],
};

export const BASE_DEFAULT = {
  top: { style: 'triangle', padding: 0, cover: 1 },
  bottom: { style: 'bikini', rise: 0, cut: 0.5, backCover: 0.6 },
};
export const BASE_STYLE_DEFAULT = { fabric: 'cotton', color: '#f2eeea', color2: '#ffffff', pattern: 'none', trim: 'none', trimColor: '#ffffff', trimWidth: 0.004, seams: 0, seamColor: '#000000', scale: 1, denier: 0.3, cell: 0.0042, thread: 0.22 };

export class Dresser {
  constructor({ body, ctx, wardrobe, noise, engine, colliders }) {
    this.body = body;
    this.ctx = ctx;
    this.wardrobe = wardrobe;
    this.noise = noise;
    this.engine = engine;
    this.colliders = colliders;
    this.cloth = { wind: 0, stiffness: 1 }; // ajustes globais de tecidos simulados (aba Dinâmica)
    this.entries = new Map(); // slot -> Entry
    this.base = {
      top: this._newEntry('base.top', 'base_top', { ...BASE_STYLE_DEFAULT }, { ...BASE_DEFAULT.top }),
      bottom: this._newEntry('base.bottom', 'base_bottom', { ...BASE_STYLE_DEFAULT }, { ...BASE_DEFAULT.bottom }),
    };
    this.listeners = new Set();
    this.rebuildAll();
  }

  onChange(fn) {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }
  _emit() {
    this.listeners.forEach((fn) => fn(this));
  }

  _newEntry(id, type, style, options) {
    const mat = new FabricMaterial({ noise: this.noise, ...style });
    const entry = { id, type, style, options, mat, parts: [], slot: null };
    // sapatos: segundo material para a sola e o salto (cor2)
    if (type === 'shoes') entry.mat2 = new FabricMaterial({ noise: this.noise, ...style, fabric: 'leather', color: style.color2, pattern: 'none', trim: 'none' });
    return entry;
  }

  // ------------------------------------------------------------------ construção
  _clearParts(entry) {
    for (const p of entry.parts) {
      if (p.kind === 'shell' || p.kind === 'ribbon') this.wardrobe.remove(p.id, true);
      else p.obj?.dispose?.();
    }
    entry.parts = [];
  }

  /** Campo de cobertura (união dos Shells opacos de peças) de um grupo de slots, ou null. */
  _coverField(slots) {
    const fields = [];
    for (const slot of slots) {
      const e = this.entries.get(slot);
      if (!e) continue;
      for (const p of e.parts) if (p.kind === 'shell' && p.spec.opaque !== false && p.spec.field) fields.push(p.spec.field);
    }
    if (!fields.length) return null;
    return (v) => {
      let f = 1e9;
      for (const fn of fields) f = Math.min(f, fn(v));
      return f;
    };
  }

  /**
   * Espessura (m) da peça opaca mais alta que está por baixo de `layer` no vértice v. Uma peça de camada
   * superior (avental sobre o corpete, por exemplo) passa por cima dela em qualquer enchimento do busto;
   * sem isso o corpete aparece à frente do avental e o limite entre os dois vira uma escada de triângulos.
   */
  underOffset(layer, v) {
    let m = 0;
    for (const e of this.entries.values()) {
      for (const p of e.parts) {
        const sp = p.spec;
        if (p.kind !== 'shell' || sp.opaque === false || !sp.offsetFn || !((sp.layer ?? 3) < layer)) continue;
        if (sp.field(v, this.ctx) > 0.002) continue;
        m = Math.max(m, sp.offsetFn(v, this.ctx));
      }
    }
    return m;
  }

  /** Reavalia a espessura das peças de camada alta (dependem do que está por baixo delas). */
  _relayer() {
    for (const e of this.entries.values()) {
      for (const p of e.parts) if ((p.kind === 'shell' || p.kind === 'ribbon') && (p.spec.layer ?? 3) >= 4) p.obj.refresh?.();
    }
  }

  _build(entry) {
    this._clearParts(entry);
    const def = BUILDERS[entry.type];
    if (!def) return;
    let inside = null;
    if (entry.type === 'base_top') inside = this._coverField(['top', 'onepiece']);
    else if (entry.type === 'base_bottom') inside = this._coverField(['bottom', 'onepiece']);
    const res = def(this.ctx, entry.options, { style: entry.style, dresser: this, entry });
    const ensure = (spec, extra) => ({ ...spec, material: spec.material ?? entry.mat, ...extra });
    let k = 0;
    for (const sh of res.shells || []) {
      const spec = ensure(sh, {});
      if (inside) {
        const own = spec.field;
        // a camada-base fica 6 mm para dentro da peça que a cobre (some por inteiro, sem faixa à mostra)
        spec.field = (v, c) => Math.max(own(v, c), inside(v) + 0.006);
      }
      const id = `${entry.id}.s${k++}`;
      const shell = this.wardrobe.add(id, spec);
      entry.parts.push({ kind: 'shell', id, spec, obj: shell });
    }
    for (const rb of res.ribbons || []) {
      if (inside) continue; // cordões da base não aparecem quando há peça por cima
      const id = `${entry.id}.r${k++}`;
      const r = this.wardrobe.addRibbon(id, ensure(rb, { width: rb.width ?? 0.0042, profile: rb.profile ?? 'round', sides: rb.sides ?? 6, offset: rb.offset ?? 0.0008, layer: rb.layer ?? 1 }));
      entry.parts.push({ kind: 'ribbon', id, spec: rb, obj: r });
    }
    for (const o of res.objects || []) {
      entry.parts.push({ kind: 'object', id: o.id, obj: o.object, update: o.update, dispose: o.dispose });
    }
    for (const d of res.drapes || []) entry.parts.push({ kind: 'drape', id: d.id, obj: d.object, update: d.update, dispose: d.dispose, cloth: d.cloth });
    this.wardrobe.updateCoverage();
    // peças que dependem de outras (laço ↔ gola, avental ↔ saia) acompanham quando a de que dependem muda
    if (!this._cascade) {
      this._cascade = true;
      const dep = { neck: 'neckBow', skirt: 'apron' }[entry.slot];
      const e2 = dep && this.entries.get(dep);
      if (e2) this._build(e2);
      this._cascade = false;
    }
  }

  rebuildAll() {
    for (const e of this.entries.values()) this._build(e);
    this._rebuildBases();
  }

  // ------------------------------------------------------------------ camada-base
  setBase(which, patch) {
    const e = this.base[which];
    const optKeys = Object.keys(BASE_DEFAULT[which]);
    const style = {};
    const opt = {};
    for (const [k, v] of Object.entries(patch)) (optKeys.includes(k) ? opt : style)[k] = v;
    if (Object.keys(style).length) {
      e.style = { ...e.style, ...style };
      e.mat.setParams(style);
    }
    if (Object.keys(opt).length) {
      e.options = { ...e.options, ...opt };
      this._build(e);
      this._guardBase();
    }
    this._emit();
  }

  // ------------------------------------------------------------------ peças
  slotOf(type) {
    return GARMENT_TYPES[type].slot;
  }

  /** Veste uma peça (substitui a do mesmo slot e remove as que conflitam). */
  addItem(type, partial = {}) {
    const def = GARMENT_TYPES[type];
    if (!def) return null;
    const slot = def.slot;
    for (const ex of SLOT_EXCLUDES[slot] || []) this.removeSlot(ex, true);
    this.removeSlot(slot, true);
    const item = defaultItem(type);
    const style = { ...item.style, ...(partial.style || {}) };
    const options = { ...item.options, ...(partial.options || {}) };
    const entry = this._newEntry(`g.${slot}`, type, style, options);
    entry.slot = slot;
    this.entries.set(slot, entry);
    this._build(entry);
    this._rebuildBases();
    this._emit();
    return entry;
  }

  removeSlot(slot, silent = false) {
    const e = this.entries.get(slot);
    if (!e) return;
    this._clearParts(e);
    this.entries.delete(slot);
    if (!silent) {
      this._rebuildBases();
      this.wardrobe.updateCoverage();
      this._emit();
    }
  }

  _rebuildBases() {
    this._build(this.base.top);
    this._build(this.base.bottom);
    this._guardBase();
    this._relayer();
  }

  /**
   * Salvaguarda: a camada-base nunca pode faltar. Se, por qualquer motivo, ela não tiver geometria, volta ao
   * estilo seguro (faixa + boyshort) e avisa no console.
   */
  _guardBase() {
    for (const which of ['top', 'bottom']) {
      const e = this.base[which];
      const covered = this._coverField(which === 'top' ? ['top', 'onepiece'] : ['bottom', 'onepiece']);
      const ok = covered || e.parts.some((p) => p.kind === 'shell' && p.obj && p.obj.count > 0);
      if (ok) continue;
      console.warn(`camada-base (${which}) sem geometria: restaurando o estilo padrão`);
      e.options = { ...BASE_DEFAULT[which], style: which === 'top' ? 'bandeau' : 'boy' };
      this._build(e);
    }
  }

  setItemStyle(slot, patch) {
    const e = this.entries.get(slot);
    if (!e) return;
    e.style = { ...e.style, ...patch };
    e.mat.setParams(patch);
    if (e.mat2) e.mat2.setParams({ color: e.style.color2 });
    for (const p of e.parts) p.obj?.setStyle?.(e.style);
    this._emit();
  }

  /** Ajustes globais de tecidos simulados: vento e rigidez. */
  setCloth(c) {
    if (c) this.cloth = { ...this.cloth, ...c };
  }

  setItemOptions(slot, patch) {
    const e = this.entries.get(slot);
    if (!e) return;
    e.options = { ...e.options, ...patch };
    this._build(e);
    this._rebuildBases();
    this._emit();
  }

  clear() {
    for (const slot of [...this.entries.keys()]) this.removeSlot(slot, true);
    this._rebuildBases();
    this.wardrobe.updateCoverage();
    this._emit();
  }

  applyOutfit(id) {
    const preset = OUTFIT_BY_ID[id];
    if (!preset) return;
    for (const slot of [...this.entries.keys()]) this.removeSlot(slot, true);
    for (const it of expandOutfit(preset)) {
      const def = GARMENT_TYPES[it.type];
      for (const ex of SLOT_EXCLUDES[def.slot] || []) this.removeSlot(ex, true);
      const entry = this._newEntry(`g.${def.slot}`, it.type, it.style, it.options);
      entry.slot = def.slot;
      this.entries.set(def.slot, entry);
      this._build(entry);
    }
    this._rebuildBases();
    this._emit();
  }

  // ------------------------------------------------------------------ simulação
  update(dt) {
    for (const e of this.entries.values()) for (const p of e.parts) p.update?.(dt, this);
  }

  // ------------------------------------------------------------------ estado
  serialize() {
    return {
      base: {
        top: { style: this.base.top.style, options: this.base.top.options },
        bottom: { style: this.base.bottom.style, options: this.base.bottom.options },
      },
      items: [...this.entries.values()].map((e) => ({ type: e.type, style: e.style, options: e.options })),
    };
  }

  restore(state) {
    if (!state) return;
    for (const slot of [...this.entries.keys()]) this.removeSlot(slot, true);
    for (const which of ['top', 'bottom']) {
      const b = state.base?.[which];
      const e = this.base[which];
      e.style = { ...BASE_STYLE_DEFAULT, ...(b?.style || {}) };
      e.options = { ...BASE_DEFAULT[which], ...(b?.options || {}) };
      e.mat.setParams(e.style);
    }
    for (const it of state.items || []) {
      const def = GARMENT_TYPES[it.type];
      if (!def) continue;
      const entry = this._newEntry(`g.${def.slot}`, it.type, { ...defaultItem(it.type).style, ...it.style }, { ...defaultItem(it.type).options, ...it.options });
      entry.slot = def.slot;
      this.entries.set(def.slot, entry);
      this._build(entry);
    }
    this._rebuildBases();
    this._emit();
  }
}
