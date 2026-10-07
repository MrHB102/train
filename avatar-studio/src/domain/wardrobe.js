// Garments e Outfits (ver GLOSSARY.md). Dados puros: a UI e o Dresser leem este catálogo.
//   - Garment type: peça que o Dresser sabe construir (Shell colado ao corpo, Drape simulado ou Accessory);
//   - slot: uma peça por slot (uma nova substitui a anterior; 'onepiece' ocupa top + bottom);
//   - Outfit: conjunto temático de Garments aplicados juntos.
const L = (pt, en) => ({ pt, en });
const range = (id, pt, en, min, max, def, step = 0.01) => ({ id, type: 'range', label: L(pt, en), min, max, def, step });
const choice = (id, pt, en, items, def) => ({ id, type: 'choice', label: L(pt, en), items, def });
const toggle = (id, pt, en, def) => ({ id, type: 'toggle', label: L(pt, en), def });

export const SLOTS = [
  { id: 'onepiece', pt: 'Peça única', en: 'One-piece' },
  { id: 'top', pt: 'Parte de cima', en: 'Top' },
  { id: 'bottom', pt: 'Parte de baixo', en: 'Bottom' },
  { id: 'skirt', pt: 'Saia', en: 'Skirt' },
  { id: 'sleeves', pt: 'Mangas', en: 'Sleeves' },
  { id: 'apron', pt: 'Avental', en: 'Apron' },
  { id: 'legwear', pt: 'Meias / meia-calça', en: 'Legwear' },
  { id: 'neck', pt: 'Colarinho / gargantilha', en: 'Collar / choker' },
  { id: 'neckBow', pt: 'Gravata / laço', en: 'Bow tie / bow' },
  { id: 'tail', pt: 'Rabo', en: 'Tail' },
  { id: 'shoes', pt: 'Calçados', en: 'Shoes' },
];

const style = (o) => ({ fabric: 'cotton', color: '#e9e4e0', color2: '#ffffff', pattern: 'none', trim: 'none', trimColor: '#ffffff', trimWidth: 0.012, seams: 0, seamColor: '#000000', scale: 1, denier: 0.3, cell: 0.0042, thread: 0.22, ...o });

export const GARMENT_TYPES = {
  base_top: {
    slot: 'baseTop', layer: 1, label: L('Top-base', 'Base top'),
    style: style({ fabric: 'knit', color: '#e9e4e0', trim: 'band', trimColor: '#cfc8c4', trimWidth: 0.014 }),
    options: [range('padding', 'Enchimento do busto (0 = marca o contorno)', 'Bust padding (0 = traces the form)', 0, 1, 0)],
  },
  base_bottom: {
    slot: 'baseBottom', layer: 1, label: L('Shorts-base', 'Base shorts'),
    style: style({ fabric: 'cotton', color: '#e9e4e0', trim: 'band', trimColor: '#cfc8c4', trimWidth: 0.012 }),
    options: [],
  },
  leotard: {
    slot: 'onepiece', layer: 3, label: L('Collant / maiô', 'Leotard'),
    style: style({ fabric: 'satin', color: '#14141b', trim: 'piping', trimColor: '#f4f4f4', trimWidth: 0.012, seams: 1 }),
    options: [
      choice('neckline', 'Decote', 'Neckline', [{ id: 0, pt: 'Reto', en: 'Straight' }, { id: 1, pt: 'Coração', en: 'Sweetheart' }, { id: 3, pt: 'Em V', en: 'V-neck' }], 1),
      range('legCut', 'Cavado da perna', 'Leg cut height', 0, 1, 0.72),
      range('topHeight', 'Altura do decote', 'Neckline height', -0.5, 1, 0.1),
      range('backDrop', 'Cobertura atrás', 'Back coverage', 0, 1, 0.6),
      range('padding', 'Enchimento do busto', 'Bust padding', 0, 1, 0.35),
    ],
  },
  bodice: {
    slot: 'top', layer: 3, label: L('Corpete / vestido (corpo)', 'Bodice'),
    style: style({ fabric: 'satin', color: '#15151c', trim: 'piping', trimColor: '#f1f1f1', trimWidth: 0.012 }),
    options: [
      choice('neckline', 'Decote', 'Neckline', [{ id: 0, pt: 'Quadrado', en: 'Square' }, { id: 1, pt: 'Coração', en: 'Sweetheart' }, { id: 2, pt: 'Alto', en: 'High' }], 1),
      range('length', 'Comprimento até a cintura', 'Length to waist', -0.05, 0.08, 0.0),
      range('padding', 'Enchimento do busto', 'Bust padding', 0, 1, 0.3),
    ],
  },
  cropTee: {
    slot: 'top', layer: 3, label: L('Blusinha curta', 'Crop top'),
    style: style({ fabric: 'cotton', color: '#f4f1ee' }),
    options: [
      range('length', 'Comprimento', 'Length', 0, 1, 0.25),
      range('neck', 'Decote', 'Neckline', 0, 1, 0.5),
    ],
  },
  tubeTop: {
    slot: 'top', layer: 3, label: L('Top tomara que caia', 'Tube top'),
    style: style({ fabric: 'knit', color: '#d94f7a' }),
    options: [range('padding', 'Enchimento do busto', 'Bust padding', 0, 1, 0)],
  },
  shorts: {
    slot: 'bottom', layer: 3, label: L('Shorts', 'Shorts'),
    style: style({ fabric: 'denim', color: '#3b5b8f', trim: 'band', trimColor: '#2c4571', trimWidth: 0.014 }),
    options: [range('length', 'Comprimento', 'Length', 0.02, 0.3, 0.1), range('rise', 'Altura da cintura', 'Waist rise', -0.05, 0.1, 0.0)],
  },
  leggings: {
    slot: 'bottom', layer: 3, label: L('Legging', 'Leggings'),
    style: style({ fabric: 'latex', color: '#17171c' }),
    options: [range('length', 'Comprimento (joelho → tornozelo)', 'Length (knee → ankle)', 0, 1, 1), range('rise', 'Altura da cintura', 'Waist rise', -0.05, 0.1, 0.0)],
  },
  skirt: {
    slot: 'skirt', layer: 0, drape: true, label: L('Saia (simulada)', 'Skirt (simulated)'),
    style: style({ fabric: 'satin', color: '#15151c', trim: 'piping', trimColor: '#f4f4f4', trimWidth: 0.03 }),
    options: [
      range('length', 'Comprimento', 'Length', 0.14, 0.75, 0.34),
      range('flare', 'Volume / godê', 'Flare', 0, 1.3, 0.8),
      toggle('pleats', 'Pregas', 'Pleats', false),
      range('rise', 'Altura da cintura', 'Waist rise', -0.04, 0.06, 0.0),
      range('stiffness', 'Rigidez do tecido', 'Fabric stiffness', 0.3, 2.5, 1.0),
    ],
  },
  apron: {
    slot: 'apron', layer: 4, drape: true, label: L('Avental', 'Apron'),
    style: style({ fabric: 'cotton', color: '#fbfbfb', trim: 'scallop', trimColor: '#fbfbfb', trimWidth: 0.04 }),
    options: [range('length', 'Comprimento', 'Length', 0.1, 0.55, 0.3), toggle('bib', 'Peitilho', 'Bib', true)],
  },
  puffSleeves: {
    slot: 'sleeves', layer: 4, label: L('Mangas bufantes', 'Puff sleeves'),
    style: style({ fabric: 'satin', color: '#15151c', trim: 'scallop', trimColor: '#fbfbfb', trimWidth: 0.026 }),
    options: [range('puff', 'Volume da manga', 'Puff amount', 0, 1, 0.75)],
  },
  legwear: {
    slot: 'legwear', layer: 2, label: L('Meias / meia-calça', 'Stockings / tights'),
    style: style({ fabric: 'sheer', color: '#15151a', denier: 0.34, trim: 'scallop', trimColor: '#15151a', trimWidth: 0.035 }),
    options: [
      range('top', 'Altura (tornozelo → cintura)', 'Height (ankle → waist)', 0, 1, 0.78),
      toggle('feet', 'Cobrir os pés', 'Cover feet', false),
    ],
  },
  collar: {
    slot: 'neck', layer: 3, label: L('Colarinho / gargantilha', 'Collar / choker'),
    style: style({ fabric: 'cotton', color: '#fafafa', trim: 'piping', trimColor: '#14141a', trimWidth: 0.004 }),
    options: [range('height', 'Altura', 'Height', 0.014, 0.05, 0.03), range('lift', 'Posição', 'Position', 0, 0.04, 0.012)],
  },
  bowtie: {
    slot: 'neckBow', layer: 5, label: L('Gravata borboleta / laço', 'Bow tie / bow'),
    style: style({ fabric: 'satin', color: '#14141b' }),
    options: [range('size', 'Tamanho', 'Size', 0.6, 1.8, 1.0), range('lift', 'Posição', 'Position', 0, 0.04, 0.012)],
  },
  tail: {
    slot: 'tail', layer: 5, label: L('Rabo de coelha (pompom)', 'Bunny tail (pom-pom)'),
    style: style({ fabric: 'velvet', color: '#fbfbfb' }),
    options: [
      range('size', 'Tamanho', 'Size', 0.5, 1.8, 1.0),
      range('height', 'Altura nas costas', 'Height on back', -0.04, 0.08, 0.0),
    ],
  },
};

/** Presets de Outfit: lista de Garments (tipo, estilo parcial e opções parciais). */
export const OUTFITS = [
  { id: 'none', label: L('Só a roupa-base', 'Base layer only'), items: [] },
  {
    id: 'bunny',
    label: L('Coelhinha (bunny girl)', 'Bunny girl'),
    items: [
      { type: 'leotard', style: { fabric: 'satin', color: '#14141b', trim: 'piping', trimColor: '#f4f4f4' } },
      { type: 'collar', style: { fabric: 'cotton', color: '#fafafa', trim: 'piping', trimColor: '#14141a' } },
      { type: 'bowtie', style: { fabric: 'satin', color: '#14141b' } },
      { type: 'legwear', style: { fabric: 'fishnet', color: '#101014', cell: 0.0072, thread: 0.18, trim: 'none' }, options: { top: 1 } },
      { type: 'tail' },
    ],
  },
  {
    id: 'maid',
    label: L('Empregada (maid)', 'Maid'),
    items: [
      { type: 'bodice', style: { fabric: 'satin', color: '#15151c', trim: 'piping', trimColor: '#f1f1f1' }, options: { neckline: 1 } },
      { type: 'puffSleeves', style: { fabric: 'satin', color: '#15151c', trim: 'scallop', trimColor: '#fbfbfb' } },
      { type: 'skirt', style: { fabric: 'satin', color: '#15151c', trim: 'piping', trimColor: '#f4f4f4' }, options: { length: 0.36, flare: 0.9 } },
      { type: 'apron', style: { fabric: 'cotton', color: '#fbfbfb', trim: 'scallop', trimColor: '#fbfbfb' }, options: { length: 0.3, bib: true } },
      { type: 'collar', style: { fabric: 'lace', color: '#fbfbfb', cell: 0.014, trim: 'none' }, options: { height: 0.026 } },
      { type: 'bowtie', style: { fabric: 'satin', color: '#fbfbfb' }, options: { size: 0.8 } },
      { type: 'legwear', style: { fabric: 'sheer', color: '#fafafa', denier: 0.5, trim: 'scallop', trimColor: '#fafafa', trimWidth: 0.04 }, options: { top: 0.7 } },
    ],
  },
  {
    id: 'school',
    label: L('Colegial', 'School uniform'),
    items: [
      { type: 'cropTee', style: { fabric: 'cotton', color: '#f6f6f8' }, options: { length: 0.55, neck: 0.4 } },
      { type: 'skirt', style: { fabric: 'cotton', color: '#2a3a6a', pattern: 'plaid', color2: '#8aa0d8', trim: 'none' }, options: { length: 0.3, flare: 0.5, pleats: true } },
      { type: 'legwear', style: { fabric: 'knit', color: '#f2f2f2', trim: 'band', trimColor: '#2a3a6a', trimWidth: 0.02 }, options: { top: 0.42 } },
      { type: 'bowtie', style: { fabric: 'satin', color: '#c01f3d' }, options: { size: 1.1 } },
    ],
  },
  {
    id: 'summer',
    label: L('Vestido de verão', 'Sundress'),
    items: [
      { type: 'bodice', style: { fabric: 'cotton', color: '#f4e9d8', pattern: 'polka', color2: '#d9578a', trim: 'band', trimColor: '#f4e9d8' }, options: { neckline: 1, padding: 0.25 } },
      { type: 'skirt', style: { fabric: 'cotton', color: '#f4e9d8', pattern: 'polka', color2: '#d9578a', trim: 'none' }, options: { length: 0.42, flare: 1.0 } },
    ],
  },
  {
    id: 'casual',
    label: L('Casual (blusinha e shorts)', 'Casual'),
    items: [
      { type: 'cropTee', style: { fabric: 'cotton', color: '#e6edf7', pattern: 'checks', color2: '#e0508a' }, options: { length: 0.3 } },
      { type: 'shorts', style: { fabric: 'denim', color: '#3b5b8f' }, options: { length: 0.1 } },
    ],
  },
  {
    id: 'sport',
    label: L('Esportiva', 'Sportswear'),
    items: [
      { type: 'tubeTop', style: { fabric: 'knit', color: '#ff4d8d' } },
      { type: 'leggings', style: { fabric: 'latex', color: '#1a1a22' }, options: { length: 1 } },
    ],
  },
  {
    id: 'gothic',
    label: L('Gótica', 'Gothic'),
    items: [
      { type: 'leotard', style: { fabric: 'latex', color: '#101014', trim: 'piping', trimColor: '#a31428', seams: 1, seamColor: '#a31428' }, options: { legCut: 0.4, backDrop: 0.8 } },
      { type: 'skirt', style: { fabric: 'velvet', color: '#16161c', trim: 'scallop', trimColor: '#16161c' }, options: { length: 0.55, flare: 1.1 } },
      { type: 'collar', style: { fabric: 'leather', color: '#101014', trim: 'piping', trimColor: '#a31428' } },
      { type: 'legwear', style: { fabric: 'fishnet', color: '#0c0c10', cell: 0.0058, thread: 0.2 }, options: { top: 1 } },
    ],
  },
];
export const OUTFIT_BY_ID = Object.fromEntries(OUTFITS.map((o) => [o.id, o]));

export function defaultItem(type) {
  const t = GARMENT_TYPES[type];
  const options = {};
  for (const o of t.options) options[o.id] = o.def;
  return { type, style: { ...t.style }, options };
}

/** Expande um preset de Outfit em itens completos (estilo e opções mesclados aos padrões do tipo). */
export function expandOutfit(preset) {
  return preset.items.map((it) => {
    const base = defaultItem(it.type);
    return { type: it.type, style: { ...base.style, ...(it.style || {}) }, options: { ...base.options, ...(it.options || {}) } };
  });
}
