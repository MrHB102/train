// Presets de personagem (só o corpo: Traits e Dials). A pele e as roupas ficam como estão; aplicar um preset
// anima o corpo até lá (com o repique elástico). Valores além do limite natural são o modo exagerado.
const L = (pt, en) => ({ pt, en });

export const CHARACTER_PRESETS = [
  { id: 'natural', label: L('Natural', 'Natural'), hint: L('Corpo médio, sem ajustes', 'Average body, no tweaks'), traits: {}, dials: {} },
  {
    id: 'anime',
    label: L('Anime curvilínea', 'Anime curvy'),
    hint: L('Pernas longas, cintura fina, coxas juntas e marcantes', 'Long legs, tiny waist, bold touching thighs'),
    traits: { 'thighs.contact': 0.7 },
    dials: { anime: 0.9, curves: 0.55, bustSize: 0.9, glutesSize: 0.8, hipSize: 0.45, tone: 0.2 },
  },
  {
    id: 'athletic',
    label: L('Atlética (malhada)', 'Athletic (toned)'),
    hint: L('Músculos definidos e abdômen marcado', 'Defined muscles and visible abs'),
    traits: { muscle: 0.66, weight: 0.36 },
    dials: { tone: 1.2, curves: 0.35, bustSize: 0.2, glutesSize: 0.6 },
  },
  {
    id: 'petite',
    label: L('Delicada', 'Petite'),
    hint: L('Pequena e esguia', 'Small and slender'),
    traits: { height: 0.18, weight: 0.3 },
    dials: { anime: 0.35, bustSize: -0.3, glutesSize: 0.1 },
  },
  {
    id: 'thick',
    label: L('Coxas grossas', 'Thick thighs'),
    hint: L('Quadril largo, coxas bem cheias e juntas', 'Wide hips, very full touching thighs'),
    traits: { 'thighs.contact': 1, 'glutes.lift': 0.25 },
    dials: { thickness: 1.7, hipSize: 1.1, glutesSize: 1.3, anime: 0.7, curves: 0.7, bustSize: 0.8 },
  },
  {
    id: 'bombshell',
    label: L('Exagerada', 'Exaggerated'),
    hint: L('Busto e glúteos bem grandes, cintura fina', 'Very large bust and glutes, tiny waist'),
    traits: { 'thighs.contact': 1 },
    dials: { bustSize: 2.1, glutesSize: 2.0, hipSize: 1.2, curves: 1.2, anime: 0.9, thickness: 1.2 },
  },
  {
    id: 'giant',
    label: L('Gigante (extremo)', 'Giant (extreme)'),
    hint: L('Tudo no máximo da faixa exagerada', 'Everything at the top of the exaggerated range'),
    traits: { 'thighs.contact': 1 },
    dials: { bustSize: 3, glutesSize: 3, hipSize: 2.2, thickness: 2.2, curves: 1.6, anime: 1 },
  },
];
export const PRESET_BY_ID = Object.fromEntries(CHARACTER_PRESETS.map((p) => [p.id, p]));
