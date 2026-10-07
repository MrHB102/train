// Dials (ver GLOSSARY.md): um controle que move vários Traits juntos rumo a um visual nomeado.
// O Design guarda a posição do Dial separada dos Traits; o valor efetivo de cada Trait é
//     efetivo = valor do Trait + Σ (posição do Dial × peso), limitado ao Extended Range.
// Para Macro Traits o peso é em unidades do próprio Macro (ex.: Muscle neutro 0.5).
import { TRAIT_BY_ID } from './traits.js';

const L = (pt, en) => ({ pt, en });

export const DIALS = [
  {
    id: 'curves',
    label: L('Curvas', 'Curves'),
    hint: L('Cintura mais fina, quadril, glúteos e coxas mais cheios', 'Slimmer waist, fuller hips, glutes and thighs'),
    neutral: 0,
    natural: [-1, 1],
    extended: [-1.2, 2],
    weights: {
      'waist.width': -0.75,
      'hips.width': 0.4,
      'hips.circumference': 0.55,
      'glutes.volume': 0.5,
      'glutes.extraVolume': 0.25,
      'thighs.fullness': 0.25,
      'bust.size': 0.12,
      'silhouette.hourglassFull': 0.45,
    },
  },
  {
    id: 'tone',
    label: L('Definição muscular (malhada ↔ macia)', 'Muscle tone (fit ↔ soft)'),
    hint: L('Mais malhada: músculos definidos e menos gordura; negativo = mais macia', 'More fit: defined muscles and less fat; negative = softer'),
    neutral: 0,
    natural: [-1, 1],
    extended: [-1.2, 1.6],
    weights: {
      muscle: 0.3,
      weight: -0.1,
      'belly.tone': 0.7,
      'belly.volume': -0.25,
      'thighs.muscle': 0.7,
      'calves.muscle': 0.7,
      'torso.back': 0.45,
      'thighs.fullness': -0.15,
    },
  },
  {
    id: 'anime',
    label: L('Proporções anime', 'Anime proportions'),
    hint: L('Pernas longas, cintura bem fina, coxas e quadril marcantes, tornozelos e pés pequenos', 'Long legs, tiny waist, bold thighs and hips, slim ankles and small feet'),
    neutral: 0,
    natural: [0, 1],
    extended: [-0.6, 1.6],
    weights: {
      'thighs.length': 0.55,
      'calves.length': 0.55,
      'waist.width': -0.95,
      'hips.width': 0.45,
      'hips.circumference': 0.5,
      'thighs.fullness': 0.4,
      'thighs.upperVolume': 0.6,
      'thighs.extraVolume': 0.3,
      'thighs.contact': 1,
      'calves.fullness': -0.3,
      'calves.circumference': -0.35,
      'knees.size': -0.4,
      'ankles.size': -0.55,
      'feet.size': -0.3,
      'torso.length': -0.25,
      'glutes.volume': 0.35,
      'glutes.extraVolume': 0.2,
      proportions: 0.25,
      'silhouette.hourglassNeat': 0.35,
    },
  },
  {
    id: 'thickness',
    label: L('Coxas (finas ↔ grossas)', 'Thighs (slim ↔ thick)'),
    hint: L('Aumenta ou reduz o volume das coxas', 'Grows or reduces thigh volume'),
    neutral: 0,
    natural: [-1, 1.4],
    extended: [-1.2, 2.6],
    size: true,
    weights: {
      'thighs.fullness': 0.7,
      'thighs.circumference': 0.5,
      'thighs.width': 0.35,
      'thighs.depth': 0.25,
      'thighs.extraVolume': 0.35,
      'thighs.upperVolume': 0.45,
      'thighs.contact': 0.7,
    },
  },
  {
    id: 'bombshell',
    label: L('Volume do busto e glúteos', 'Bust & glute volume'),
    hint: L('Aumenta seios e glúteos juntos (estilo exagerado)', 'Grows bust and glutes together (stylized)'),
    neutral: 0,
    natural: [-1, 1],
    extended: [-1.2, 2],
    weights: {
      'bust.size': 0.45,
      'bust.extraVolume': 0.45,
      'glutes.volume': 0.55,
      'glutes.extraVolume': 0.45,
      'hips.width': 0.15,
    },
  },
  // ---- Dials de tamanho (um controle só do pequeno ao gigante, como nos criadores de personagem) ----
  {
    id: 'bustSize',
    label: L('Tamanho do busto', 'Bust size'),
    hint: L('Do menor ao gigante: tamanho + volume extra. Os seios se encostam ao crescer', 'Smallest to giant: size + extra volume. The breasts touch as they grow'),
    neutral: 0,
    natural: [-1, 1.4],
    extended: [-1, 3],
    size: true,
    // u < 0 encolhe; 0..1 vai ao grande; 1..3 vai do grande ao gigante (limite do Extended Range)
    curve: (u) => ({
      'bust.size': u < 1 ? 0.5 * u : 0.5 + 0.15 * (u - 1),
      'bust.extraVolume': u < 0 ? 0.8 * u : u < 1 ? 0.5 * u : 0.5 + 0.65 * (u - 1),
    }),
  },
  {
    id: 'glutesSize',
    label: L('Tamanho dos glúteos', 'Glute size'),
    hint: L('Do menor ao gigante: volume + arredondamento', 'Smallest to giant: volume + roundness'),
    neutral: 0,
    natural: [-1, 1.4],
    extended: [-1, 3],
    size: true,
    curve: (u) => ({
      'glutes.volume': u <= 1 ? 1.0 * u : 1.0 + 0.35 * (u - 1),
      'glutes.extraVolume': u < 0 ? 0.6 * u : u <= 1 ? 0.5 * u : 0.5 + 0.65 * (u - 1),
      'hips.width': 0.12 * u,
    }),
  },
  {
    id: 'hipSize',
    label: L('Largura do quadril', 'Hip width'),
    hint: L('Quadril mais estreito ou mais largo, com transição suave da cintura', 'Narrower or wider hips with a smooth waist transition'),
    neutral: 0,
    natural: [-1, 1.4],
    extended: [-1, 2.6],
    size: true,
    curve: (u) => ({
      'hips.width': 0.55 * u,
      'hips.circumference': 0.6 * u,
      'hips.depth': 0.18 * u,
    }),
  },
];
export const DIAL_BY_ID = Object.fromEntries(DIALS.map((d) => [d.id, d]));

export function neutralDials() {
  const v = {};
  for (const d of DIALS) v[d.id] = d.neutral;
  return v;
}

/**
 * Valores efetivos dos Traits = Traits + Dials, limitados ao Extended Range.
 * `slack` (0..1) alarga o limite em uma fração do intervalo: deixa a animação de repique ultrapassar o
 * extremo por um instante (sem isso o overshoot seria cortado justamente no valor máximo).
 */
export function effectiveValues(values, dials, slack = 0) {
  const out = { ...values };
  for (const d of DIALS) {
    const p = dials?.[d.id] || 0;
    if (!p) continue;
    // Dial linear (peso × posição) ou com curva (composição não linear: 0..100% cobre do pequeno ao gigante)
    const deltas = d.curve ? d.curve(p) : null;
    for (const [id, w] of Object.entries(d.weights || {})) out[id] = (out[id] ?? TRAIT_BY_ID[id].neutral) + (deltas ? 0 : p * w);
    if (deltas) for (const [id, dv] of Object.entries(deltas)) out[id] = (out[id] ?? TRAIT_BY_ID[id].neutral) + dv;
  }
  for (const id of Object.keys(out)) {
    const t = TRAIT_BY_ID[id];
    if (t) {
      const span = t.extended[1] - t.extended[0];
      out[id] = Math.min(t.extended[1] + span * slack, Math.max(t.extended[0] - span * slack, out[id]));
    }
  }
  return out;
}
