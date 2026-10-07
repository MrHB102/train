// Catálogo de Traits do Body (ver GLOSSARY.md).
//
//  - Macro Trait: efeitos que se combinam (idade × músculo × peso × altura …).
//  - Detail Trait: remodela uma Region sozinha, somando-se aos Macro Traits.
//  - Cada Trait tem Neutral, Natural Range e Extended Range.
//  - Detail Traits apontam para Morph Targets (nomes do pacote convertido):
//      neg  -> aplicados com peso max(0, -valor)
//      pos  -> aplicados com peso max(0,  valor)
//
// A UI, o motor de morph, o aleatório e o salvar/compartilhar leem apenas este catálogo.

const L = (pt, en) => ({ pt, en });

const dec = (dir, base) => ({ neg: [`${dir}/${base}-decr`], pos: [`${dir}/${base}-incr`] });
const between = (dir, base, a, b) => ({ neg: [`${dir}/${base}-${a}`], pos: [`${dir}/${base}-${b}`] });
const lr = (base, dir = 'armslegs') => ({
  neg: [`${dir}/l-${base}-decr`, `${dir}/r-${base}-decr`],
  pos: [`${dir}/l-${base}-incr`, `${dir}/r-${base}-incr`],
});

const NAT_BI = [-1, 1];
const EXT_BI = [-1.6, 1.6];
const NAT_UNI = [0, 1];
const EXT_UNI = [0, 1.5];

export const TRAITS = [];

function macro(id, group, label, o) {
  TRAITS.push({ id, kind: 'macro', group, label, ...o });
}
function detail(id, region, label, targets, o = {}) {
  TRAITS.push({
    id,
    kind: 'detail',
    group: region,
    region,
    label,
    neutral: 0,
    natural: NAT_BI,
    extended: EXT_BI,
    ...targets,
    ...o,
  });
}
function silhouette(id, label, target) {
  TRAITS.push({
    id,
    kind: 'detail',
    group: 'silhouette',
    label,
    neutral: 0,
    natural: NAT_UNI,
    extended: EXT_UNI,
    neg: [],
    pos: [`bodyshapes/${target}`],
  });
}

// ------------------------------------------------------------------ Macro Traits
macro('age', 'general', L('Idade', 'Age'), { neutral: 25, natural: [25, 70], extended: [25, 80], unit: 'anos', step: 1 });
macro('weight', 'general', L('Peso corporal', 'Body weight'), { neutral: 0.5, natural: [0, 1], extended: [-0.1, 1.25] });
macro('muscle', 'general', L('Massa muscular', 'Muscle mass'), { neutral: 0.5, natural: [0, 1], extended: [-0.1, 1.25] });
macro('height', 'general', L('Altura', 'Height'), { neutral: 0.5, natural: [0, 1], extended: [-0.25, 1.3] });
macro('proportions', 'general', L('Proporções (comuns ↔ ideais)', 'Proportions (common ↔ ideal)'), {
  neutral: 0.5,
  natural: [0, 1],
  extended: [-0.2, 1.3],
});
macro('ancestry.african', 'general', L('Morfologia africana', 'African morphology'), { neutral: 1 / 3, natural: [0, 1], extended: [0, 1], ancestry: true });
macro('ancestry.asian', 'general', L('Morfologia asiática', 'Asian morphology'), { neutral: 1 / 3, natural: [0, 1], extended: [0, 1], ancestry: true });
macro('ancestry.caucasian', 'general', L('Morfologia caucasiana', 'Caucasian morphology'), { neutral: 1 / 3, natural: [0, 1], extended: [0, 1], ancestry: true });
macro('bust.size', 'bust', L('Copa (forma-base do busto)', 'Cup (base bust shape)'), { region: 'bust', neutral: 0.5, natural: [0, 1], extended: [0, 1.3] });
macro('bust.firmness', 'bust', L('Firmeza do busto', 'Bust firmness'), { region: 'bust', neutral: 0.5, natural: [0, 1], extended: [0, 1.3] });

// ------------------------------------------------------------------ Silhouette
silhouette('silhouette.hourglassFull', L('Ampulheta cheia', 'Full hourglass'), 'bodyshapes-elvs-fem-full-hourglass');
silhouette('silhouette.hourglassNeat', L('Ampulheta delicada', 'Neat hourglass'), 'bodyshapes-elvs-fem-neat-hourglass');
silhouette('silhouette.pear', L('Pera (triângulo)', 'Pear (triangle)'), 'bodyshapes-elvs-fem-triangle');
silhouette('silhouette.apple', L('Maçã', 'Apple'), 'bodyshapes-elvs-fem-apple');
silhouette('silhouette.rectangle', L('Retângulo', 'Rectangle'), 'bodyshapes-elvs-fem-rectangle');
silhouette('silhouette.invertedTriangle', L('Triângulo invertido', 'Inverted triangle'), 'bodyshapes-elvs-fem-invert-triangle');
silhouette('silhouette.diamond', L('Diamante', 'Diamond'), 'bodyshapes-elvs-fem-diamond');
silhouette('silhouette.column', L('Coluna esguia', 'Lean column'), 'bodyshapes-elvs-fem-lean-column');

// ------------------------------------------------------------------ Bust
detail('bust.height', 'bust', L('Altura do busto', 'Bust height'), between('breast', 'breast-trans', 'down', 'up'));
detail('bust.spacing', 'bust', L('Separação', 'Spacing'), dec('breast', 'breast-dist'));
detail('bust.projection', 'bust', L('Projeção / ponta', 'Projection / point'), dec('breast', 'breast-point'));
detail('bust.upperFullness', 'bust', L('Volume superior', 'Upper fullness'), between('breast', 'breast-volume-vert', 'down', 'up'));
detail('bust.extraVolume', 'bust', L('Volume extra do busto', 'Extra bust volume'), { neg: ['custom/bust-volume-decr'], pos: ['custom/bust-volume-incr'] }, { natural: [-0.6, 1], extended: [-1, 1.8] });
detail('bust.circumference', 'bust', L('Contorno do busto', 'Bust circumference'), dec('measure', 'measure-bust-circ'));
detail('bust.underbust', 'bust', L('Contorno sob o busto', 'Underbust circumference'), dec('measure', 'measure-underbust-circ'));
// Contato entre os seios: 1 = encostam-se e formam o sulco sem se atravessar; 0 = livres
detail('bust.contact', 'bust', L('Seios encostados (sulco)', 'Touching breasts (cleavage)'), { neg: [], pos: [] }, { natural: [0, 1], extended: [0, 1], neutral: 1, runtime: 'bustContact' });
detail('bust.asymmetry', 'bust', L('Assimetria', 'Asymmetry'), { neg: ['asym/asymm-breast-1-l'], pos: ['asym/asymm-breast-1-r'] }, { natural: [-0.6, 0.6], extended: [-1, 1] });

// ------------------------------------------------------------------ Neck & shoulders
detail('neck.length', 'neck', L('Comprimento do pescoço', 'Neck length'), dec('measure', 'measure-neck-height'));
detail('neck.thickness', 'neck', L('Espessura do pescoço', 'Neck thickness'), dec('measure', 'measure-neck-circ'));
detail('neck.forward', 'neck', L('Projeção do pescoço', 'Neck forward'), between('neck', 'neck-trans', 'backward', 'forward'));
detail('shoulders.width', 'shoulders', L('Largura dos ombros', 'Shoulder width'), dec('measure', 'measure-shoulder-dist'));

// ------------------------------------------------------------------ Torso
detail('torso.width', 'torso', L('Largura do tronco', 'Torso width'), dec('torso', 'torso-scale-horiz'));
detail('torso.depth', 'torso', L('Profundidade do tronco', 'Torso depth'), dec('torso', 'torso-scale-depth'));
detail('torso.length', 'torso', L('Comprimento do tronco', 'Torso length'), dec('torso', 'torso-scale-vert'));
detail('torso.vshape', 'torso', L('Costas em V', 'V-shaped back'), dec('torso', 'torso-vshape'));
detail('torso.back', 'torso', L('Dorsais', 'Back muscles'), dec('torso', 'torso-muscle-dorsi'));
detail('torso.chestMuscle', 'torso', L('Peitoral', 'Pectorals'), dec('torso', 'torso-muscle-pectoral'));
detail('torso.chestWidth', 'torso', L('Largura do peito', 'Chest width'), dec('measure', 'measure-frontchest-dist'));
detail('torso.posture', 'torso', L('Postura (arquear)', 'Posture (arch)'), between('torso', 'torso-trans', 'backward', 'forward'));

// ------------------------------------------------------------------ Waist & belly
detail('waist.width', 'waist', L('Largura da cintura', 'Waist width'), dec('measure', 'measure-waist-circ'));
detail('waist.height', 'waist', L('Altura da cintura', 'Waist height'), between('hip', 'hip-waist', 'down', 'up'));
detail('waist.torsoLength', 'waist', L('Nuca → cintura', 'Nape to waist'), dec('measure', 'measure-napetowaist-dist'));
detail('waist.toHip', 'waist', L('Cintura → quadril', 'Waist to hip'), dec('measure', 'measure-waisttohip-dist'));
detail('belly.volume', 'belly', L('Volume da barriga', 'Belly volume'), dec('stomach', 'stomach-pregnant'), { natural: [-0.8, 0.6], extended: [-1.2, 1.6] });
detail('belly.tone', 'belly', L('Definição abdominal', 'Abdominal tone'), dec('stomach', 'stomach-tone'));
detail('belly.navelHeight', 'belly', L('Altura do umbigo', 'Navel height'), between('stomach', 'stomach-navel', 'down', 'up'), { natural: [-0.8, 0.8] });
detail('belly.navelDepth', 'belly', L('Profundidade do umbigo', 'Navel depth'), between('stomach', 'stomach-navel', 'in', 'out'), { natural: [-0.8, 0.8] });

// ------------------------------------------------------------------ Hips & glutes
detail('hips.width', 'hips', L('Largura da pelve (base)', 'Pelvis width (base)'), dec('hip', 'hip-scale-horiz'));
detail('hips.depth', 'hips', L('Profundidade do quadril', 'Hip depth'), dec('hip', 'hip-scale-depth'));
detail('hips.height', 'hips', L('Altura do quadril', 'Hip height'), dec('hip', 'hip-scale-vert'));
detail('hips.circumference', 'hips', L('Contorno do quadril', 'Hip circumference'), dec('measure', 'measure-hips-circ'));
detail('hips.forward', 'hips', L('Inclinação pélvica', 'Pelvic tilt'), between('hip', 'hip-trans', 'backward', 'forward'));
detail('hips.lift', 'hips', L('Posição vertical', 'Vertical position'), between('hip', 'hip-trans', 'down', 'up'));
detail('hips.tone', 'hips', L('Definição pélvica', 'Pelvic tone'), dec('pelvis', 'pelvis-tone'));
detail('glutes.volume', 'glutes', L('Volume-base dos glúteos', 'Glute base volume'), dec('buttocks', 'buttocks-volume'), { natural: [-1, 1], extended: [-1.4, 1.7] });
// formas dos glúteos (morphs procedurais): Lift, dobra infraglútea e sulco central
detail('glutes.lift', 'glutes', L('Posição (relaxado ↔ empinado)', 'Lift (relaxed ↔ perky)'), {
  neg: [['custom/glutes-lift-decr', 1], ['custom/glutes-fold-incr', 0.45]],
  pos: [['custom/glutes-lift-incr', 1], ['custom/glutes-fold-decr', 0.3]],
}, { natural: [-1, 1], extended: [-1.4, 1.5], hint: L('Relaxado = macio e mais pesado embaixo, sem aparência envelhecida', 'Relaxed = soft and fuller below, never aged-looking') });
detail('glutes.fold', 'glutes', L('Dobra sob o glúteo', 'Gluteal fold'), { neg: ['custom/glutes-fold-decr'], pos: ['custom/glutes-fold-incr'] }, { natural: [-0.6, 1], extended: [-1, 1.7] });
detail('glutes.cleft', 'glutes', L('Sulco central', 'Central cleft'), { neg: ['custom/glutes-cleft-decr'], pos: ['custom/glutes-cleft-incr'] }, { natural: [-0.6, 1], extended: [-1, 1.7] });
detail('glutes.extraVolume', 'glutes', L('Volume extra (arredondar)', 'Extra volume (rounder)'), { neg: ['custom/glutes-volume-decr'], pos: ['custom/glutes-volume-incr'] }, { natural: [-0.6, 1], extended: [-1, 1.8] });

// ------------------------------------------------------------------ Legs
detail('thighs.extraVolume', 'thighs', L('Volume extra das coxas', 'Extra thigh volume'), { neg: ['custom/thighs-volume-decr'], pos: ['custom/thighs-volume-incr'] }, { natural: [-0.6, 1], extended: [-1, 1.8] });
detail('thighs.upperVolume', 'thighs', L('Parte alta das coxas (pera)', 'Upper thighs (pear)'), { neg: ['custom/thighs-upper-volume-decr'], pos: ['custom/thighs-upper-volume-incr'] }, { natural: [-0.6, 1], extended: [-1, 1.8] });
// Contato entre as coxas: 0 = livres; 1 = se encostam ao longo de toda a perna, sem se atravessar (sem vão)
detail('thighs.contact', 'thighs', L('Coxas juntas (sem vão)', 'Touching thighs (no gap)'), { neg: [], pos: [] }, { natural: [0, 1], extended: [0, 1], neutral: 0, runtime: 'thighContact' });
detail('thighs.fullness', 'thighs', L('Volume das coxas', 'Thigh fullness'), lr('upperleg-fat'));
detail('thighs.muscle', 'thighs', L('Definição das coxas', 'Thigh muscle'), lr('upperleg-muscle'));
detail('thighs.width', 'thighs', L('Largura das coxas', 'Thigh width'), lr('upperleg-scale-horiz'));
detail('thighs.depth', 'thighs', L('Profundidade das coxas', 'Thigh depth'), lr('upperleg-scale-depth'));
detail('thighs.circumference', 'thighs', L('Contorno da coxa', 'Thigh circumference'), dec('measure', 'measure-thigh-circ'));
detail('thighs.length', 'thighs', L('Comprimento da coxa', 'Thigh length'), dec('measure', 'measure-upperleg-height'));
detail('thighs.valgus', 'thighs', L('Eixo das pernas (X ↔ O)', 'Leg axis (X ↔ O)'), lr('leg-valgus'), { natural: [-0.7, 0.7] });
detail('knees.size', 'knees', L('Tamanho dos joelhos', 'Knee size'), dec('measure', 'measure-knee-circ'));
detail('calves.fullness', 'calves', L('Volume das panturrilhas', 'Calf fullness'), lr('lowerleg-fat'));
detail('calves.muscle', 'calves', L('Definição das panturrilhas', 'Calf muscle'), lr('lowerleg-muscle'));
detail('calves.width', 'calves', L('Largura das panturrilhas', 'Calf width'), lr('lowerleg-scale-horiz'));
detail('calves.circumference', 'calves', L('Contorno da panturrilha', 'Calf circumference'), dec('measure', 'measure-calf-circ'));
detail('calves.length', 'calves', L('Comprimento da perna inferior', 'Lower leg length'), dec('measure', 'measure-lowerleg-height'));
detail('ankles.size', 'ankles', L('Tamanho dos tornozelos', 'Ankle size'), dec('measure', 'measure-ankle-circ'));
detail('feet.size', 'feet', L('Tamanho dos pés', 'Foot size'), lr('foot-scale'));
detail('feet.width', 'feet', L('Largura dos pés', 'Foot width'), lr('foot-scale-horiz'));
detail('feet.length', 'feet', L('Comprimento dos pés', 'Foot length'), lr('foot-scale-depth'));
detail('feet.arch', 'feet', L('Altura do peito do pé', 'Instep height'), lr('foot-scale-vert'));

// ------------------------------------------------------------------ índices
export const TRAIT_BY_ID = Object.fromEntries(TRAITS.map((t) => [t.id, t]));
export const TRAIT_GROUPS = [
  { id: 'general', pt: 'Geral', en: 'General' },
  { id: 'silhouette', pt: 'Silhueta', en: 'Silhouette' },
  { id: 'bust', pt: 'Busto', en: 'Bust' },
  { id: 'shoulders', pt: 'Ombros', en: 'Shoulders' },
  { id: 'neck', pt: 'Pescoço', en: 'Neck' },
  { id: 'torso', pt: 'Torso', en: 'Torso' },
  { id: 'waist', pt: 'Cintura', en: 'Waist' },
  { id: 'belly', pt: 'Barriga', en: 'Belly' },
  { id: 'hips', pt: 'Quadril', en: 'Hips' },
  { id: 'glutes', pt: 'Glúteos', en: 'Glutes' },
  { id: 'thighs', pt: 'Coxas', en: 'Thighs' },
  { id: 'knees', pt: 'Joelhos', en: 'Knees' },
  { id: 'calves', pt: 'Panturrilhas', en: 'Calves' },
  { id: 'ankles', pt: 'Tornozelos', en: 'Ankles' },
  { id: 'feet', pt: 'Pés', en: 'Feet' },
];

/** Todos os nomes de Morph Target citados pelos Detail Traits (para validar contra o pacote). */
export function detailTargetNames() {
  const s = new Set();
  for (const t of TRAITS) if (t.kind === 'detail') for (const n of [...t.neg, ...t.pos]) s.add(typeof n === 'string' ? n : n[0]);
  return [...s];
}

export function neutralValues() {
  const v = {};
  for (const t of TRAITS) v[t.id] = t.neutral;
  return v;
}

/** Aplica a regra de domínio: pesos de Ancestry somam 1. */
export function normalizeAncestry(values, changedId) {
  const ids = ['ancestry.african', 'ancestry.asian', 'ancestry.caucasian'];
  const out = { ...values };
  const changed = changedId && ids.includes(changedId) ? changedId : null;
  const total = ids.reduce((a, id) => a + Math.max(0, out[id]), 0);
  if (total <= 0) {
    ids.forEach((id) => (out[id] = 1 / 3));
    return out;
  }
  if (!changed) {
    ids.forEach((id) => (out[id] = Math.max(0, out[id]) / total));
    return out;
  }
  const keep = Math.min(1, Math.max(0, out[changed]));
  const others = ids.filter((id) => id !== changed);
  const oTotal = others.reduce((a, id) => a + Math.max(0, out[id]), 0);
  out[changed] = keep;
  others.forEach((id) => {
    out[id] = oTotal > 0 ? ((1 - keep) * Math.max(0, out[id])) / oTotal : (1 - keep) / 2;
  });
  return out;
}

/** Conversão do Trait Age (anos) para o valor interno do MakeHuman (0.5 = 25 anos … 1 = 90 anos). */
export const ageYearsToMacro = (years) => 0.5 + ((Math.min(90, Math.max(25, years)) - 25) / 65) * 0.5;
