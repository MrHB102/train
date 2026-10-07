// Idioma da interface: pt-BR (padrão) e inglês. Os catálogos de domínio já trazem { pt, en }.
let lang = 'pt';
try {
  const saved = localStorage.getItem('avatar-studio.lang');
  if (saved === 'en' || saved === 'pt') lang = saved;
  else if (navigator.language && !navigator.language.toLowerCase().startsWith('pt')) lang = 'en';
} catch {}

const listeners = new Set();
export const getLang = () => lang;
export function setLang(l) {
  lang = l;
  try {
    localStorage.setItem('avatar-studio.lang', l);
  } catch {}
  listeners.forEach((fn) => fn(l));
}
export const onLang = (fn) => (listeners.add(fn), () => listeners.delete(fn));

/** Texto no idioma atual: aceita { pt, en } ou string. */
export const tr = (x) => (x && typeof x === 'object' ? x[lang] ?? x.pt ?? '' : x ?? '');

const S = {
  tabs: {
    body: { pt: 'Corpo', en: 'Body' },
    skin: { pt: 'Pele', en: 'Skin' },
    outfit: { pt: 'Roupas', en: 'Outfit' },
    extras: { pt: 'Acessórios', en: 'Extras' },
    dynamics: { pt: 'Dinâmica', en: 'Dynamics' },
    scene: { pt: 'Pose e cena', en: 'Pose & scene' },
    presets: { pt: 'Presets', en: 'Presets' },
  },
  regions: {
    general: { pt: 'Geral', en: 'General' },
    bust: { pt: 'Busto', en: 'Bust' },
    waist: { pt: 'Cintura', en: 'Waist' },
    hips: { pt: 'Quadril', en: 'Hips' },
    glutes: { pt: 'Glúteos', en: 'Glutes' },
    thighs: { pt: 'Coxas', en: 'Thighs' },
    legs: { pt: 'Pernas', en: 'Legs' },
    upper: { pt: 'Ombros e pescoço', en: 'Shoulders & neck' },
  },
  ui: {
    undo: { pt: 'Desfazer', en: 'Undo' },
    redo: { pt: 'Refazer', en: 'Redo' },
    random: { pt: 'Aleatório', en: 'Random' },
    reset: { pt: 'Restaurar', en: 'Reset' },
    resetAll: { pt: 'Restaurar tudo', en: 'Reset everything' },
    quickStyles: { pt: 'Estilos rápidos', en: 'Quick styles' },
    sizes: { pt: 'Tamanhos', en: 'Sizes' },
    details: { pt: 'Detalhes', en: 'Details' },
    silhouette: { pt: 'Silhueta', en: 'Silhouette' },
    ancestry: { pt: 'Morfologia (mistura)', en: 'Morphology (mix)' },
    natural: { pt: 'limite natural', en: 'natural limit' },
    neutral: { pt: 'neutro', en: 'neutral' },
    save: { pt: 'Salvar', en: 'Save' },
    load: { pt: 'Carregar', en: 'Load' },
    share: { pt: 'Compartilhar', en: 'Share' },
    copyCode: { pt: 'Copiar código', en: 'Copy code' },
    pasteCode: { pt: 'Colar código', en: 'Paste code' },
    screenshot: { pt: 'Captura de tela', en: 'Screenshot' },
    export: { pt: 'Exportar GLB', en: 'Export GLB' },
    language: { pt: 'Idioma', en: 'Language' },
    focus: { pt: 'Foco da câmera', en: 'Camera focus' },
    recoil: { pt: 'Repique elástico', en: 'Elastic recoil' },
    recoilAmount: { pt: 'Intensidade do repique', en: 'Recoil strength' },
    years: { pt: 'anos', en: 'yrs' },
    on: { pt: 'ligado', en: 'on' },
    off: { pt: 'desligado', en: 'off' },
  },
};

/** s('tabs.body') → texto no idioma atual. */
export function s(path) {
  let o = S;
  for (const k of path.split('.')) o = o?.[k];
  return tr(o);
}
export const STRINGS = S;
