// Skin (ver GLOSSARY.md): tom, subtom, Imperfections (cada uma pode ir a zero), Sheen e extras.
const L = (pt, en) => ({ pt, en });

/** Tons de pele (sRGB). `Skin Tone` é independente de Ancestry. */
export const SKIN_TONES = [
  { id: 'porcelain', label: L('Porcelana', 'Porcelain'), color: '#f3d3c4' },
  { id: 'fair', label: L('Clara', 'Fair'), color: '#ecc0a8' },
  { id: 'light', label: L('Rosada', 'Light'), color: '#e6b196' },
  { id: 'medium', label: L('Média', 'Medium'), color: '#d29b7a' },
  { id: 'olive', label: L('Oliva', 'Olive'), color: '#c28d63' },
  { id: 'tan', label: L('Bronzeada', 'Tan'), color: '#b07a52' },
  { id: 'brown', label: L('Morena', 'Brown'), color: '#8d5a3d' },
  { id: 'dark', label: L('Escura', 'Dark'), color: '#62402c' },
  { id: 'deep', label: L('Ébano', 'Deep'), color: '#3e281e' },
];

/** Parâmetros numéricos da pele. `imperfection: true` entra no botão "pele perfeita". */
export const SKIN_PARAMS = [
  { id: 'undertone', label: L('Subtom (frio ↔ quente)', 'Undertone (cool ↔ warm)'), min: -1, max: 1, def: 0.15, step: 0.01 },
  { id: 'pores', label: L('Poros', 'Pores'), min: 0, max: 1.6, def: 0.55, step: 0.01, imperfection: true },
  { id: 'mottling', label: L('Manchas / irregularidade de cor', 'Mottling / blotchiness'), min: 0, max: 1.6, def: 0.5, step: 0.01, imperfection: true },
  { id: 'freckles', label: L('Sardas', 'Freckles'), min: 0, max: 1, def: 0, step: 0.01, imperfection: true },
  { id: 'moles', label: L('Pintas', 'Moles'), min: 0, max: 1, def: 0.35, step: 0.01, imperfection: true },
  { id: 'veins', label: L('Veias', 'Veins'), min: 0, max: 1, def: 0.2, step: 0.01, imperfection: true },
  { id: 'redness', label: L('Vermelhidão (joelhos, tornozelos…)', 'Redness (knees, ankles…)'), min: 0, max: 1.5, def: 0.5, step: 0.01, imperfection: true },
  { id: 'fuzz', label: L('Penugem (brilho suave)', 'Peach fuzz (soft glow)'), min: 0, max: 1, def: 0.4, step: 0.01, imperfection: true },
  { id: 'oil', label: L('Brilho / oleosidade', 'Gloss / oiliness'), min: 0, max: 1, def: 0.25, step: 0.01 },
  { id: 'sss', label: L('Translucidez da pele', 'Skin translucency'), min: 0, max: 1, def: 0.85, step: 0.01 },
  { id: 'shimmer', label: L('Glitter corporal', 'Body glitter'), min: 0, max: 1, def: 0, step: 0.01 },
  // Anatomia da superfície: relevo e sombra de ossos, tendões e músculos (não muda a geometria)
  { id: 'anatomy', group: 'anatomy', label: L('Definição anatômica (geral)', 'Anatomical definition (overall)'), min: 0, max: 1.6, def: 0.85, step: 0.01 },
  { id: 'anaCollar', group: 'anatomy', label: L('Clavículas e tendões do pescoço', 'Collarbones and neck tendons'), min: 0, max: 1.6, def: 1, step: 0.01 },
  { id: 'anaAbs', group: 'anatomy', label: L('Abdômen (linha alba, marcado)', 'Abdomen (linea alba, defined)'), min: 0, max: 1.6, def: 0.8, step: 0.01 },
  { id: 'anaNavel', group: 'anatomy', label: L('Umbigo', 'Navel'), min: 0, max: 1.6, def: 1, step: 0.01 },
  { id: 'anaHips', group: 'anatomy', label: L('Ossos do quadril e linha em V', 'Hip bones and V-line'), min: 0, max: 1.6, def: 0.8, step: 0.01 },
  { id: 'anaRibs', group: 'anatomy', label: L('Costelas', 'Ribs'), min: 0, max: 1.6, def: 0.6, step: 0.01 },
  { id: 'anaBack', group: 'anatomy', label: L('Costas (coluna, escápulas, covinhas)', 'Back (spine, shoulder blades, dimples)'), min: 0, max: 1.6, def: 0.8, step: 0.01 },
  { id: 'nails', label: L('Esmalte nos pés', 'Toenail polish'), min: 0, max: 1, def: 0, step: 0.01 },
];

export const SKIN_COLORS = [
  { id: 'tone', label: L('Tom de pele', 'Skin tone'), def: '#e6b196' },
  { id: 'shimmerColor', label: L('Cor do glitter', 'Glitter color'), def: '#fff1c9' },
  { id: 'nailColor', label: L('Cor do esmalte', 'Polish color'), def: '#d6336c' },
];

export function defaultSkin() {
  const s = { toneId: 'light' };
  for (const p of SKIN_PARAMS) s[p.id] = p.def;
  for (const c of SKIN_COLORS) s[c.id] = c.def;
  s.smooth = 0; // "pele perfeita": 0 = natural … 1 = sem nenhuma Imperfection
  s.molesSeed = 7;
  return s;
}

/** Valor efetivo de uma Imperfection depois do controle mestre "pele perfeita". */
export function effectiveSkin(skin) {
  const out = { ...skin };
  const k = 1 - Math.min(1, Math.max(0, skin.smooth || 0));
  for (const p of SKIN_PARAMS) if (p.imperfection) out[p.id] = skin[p.id] * k;
  return out;
}

export const SKIN_PRESETS = [
  { id: 'natural', label: L('Natural', 'Natural'), patch: {} },
  { id: 'flawless', label: L('Pele perfeita', 'Flawless'), patch: { smooth: 1 } },
  { id: 'freckled', label: L('Sardenta', 'Freckled'), patch: { freckles: 0.7, moles: 0.4, mottling: 0.6, smooth: 0 } },
  { id: 'glow', label: L('Brilhante (óleo)', 'Glowing (oiled)'), patch: { oil: 0.8, fuzz: 0.2, pores: 0.25, smooth: 0 } },
  { id: 'matte', label: L('Matte', 'Matte'), patch: { oil: 0, fuzz: 0.5, smooth: 0 } },
];
