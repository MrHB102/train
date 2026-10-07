// Regions do Body (ver GLOSSARY.md). Soft Tissue = regiões cuja carne se move (Jiggle).
export const REGIONS = [
  { id: 'neck', pt: 'Pescoço', en: 'Neck' },
  { id: 'shoulders', pt: 'Ombros', en: 'Shoulders' },
  { id: 'torso', pt: 'Torso', en: 'Torso' },
  { id: 'bust', pt: 'Busto', en: 'Bust', softTissue: true, joints: ['breast.L', 'breast.R'] },
  { id: 'waist', pt: 'Cintura', en: 'Waist' },
  { id: 'belly', pt: 'Barriga', en: 'Belly', softTissue: true, joints: ['belly'] },
  { id: 'hips', pt: 'Quadril', en: 'Hips' },
  { id: 'glutes', pt: 'Glúteos', en: 'Glutes', softTissue: true, joints: ['glute.L', 'glute.R'] },
  { id: 'thighs', pt: 'Coxas', en: 'Thighs', softTissue: true, joints: ['thigh.L', 'thigh.R'] },
  { id: 'knees', pt: 'Joelhos', en: 'Knees' },
  { id: 'calves', pt: 'Panturrilhas', en: 'Calves' },
  { id: 'ankles', pt: 'Tornozelos', en: 'Ankles' },
  { id: 'feet', pt: 'Pés', en: 'Feet' },
];

export const REGION_BY_ID = Object.fromEntries(REGIONS.map((r) => [r.id, r]));
export const SOFT_TISSUE = REGIONS.filter((r) => r.softTissue);
