// Motor de morph: converte valores de Traits em pesos de Morph Targets e mistura os alvos.
//
// - Macro Traits combinam-se multiplicativamente (idade × músculo × peso × altura × …), seguindo
//   exatamente as regras do MakeHuman (cada Morph Target tem as suas variáveis no nome do arquivo).
// - Detail Traits somam-se (neg/pos conforme o sinal do valor).
import { TRAITS, ageYearsToMacro } from '../domain/traits.js';

const MACRO_TOKENS = new Set([
  'female', 'young', 'old', 'minmuscle', 'averagemuscle', 'maxmuscle', 'minweight', 'averageweight', 'maxweight',
  'minheight', 'maxheight', 'idealproportions', 'uncommonproportions', 'mincup', 'averagecup', 'maxcup',
  'minfirmness', 'averagefirmness', 'maxfirmness', 'african', 'asian', 'caucasian',
]);

/** Variáveis macro (valores já extrapolados nos limites) a partir dos valores dos Traits. */
export function macroVariables(v) {
  const a = ageYearsToMacro(v.age);
  const old = Math.max(0, a * 2 - 1);
  const tri = (x) => {
    const max = Math.max(0, x * 2 - 1);
    const min = Math.max(0, 1 - x * 2);
    return [min, 1 - (max + min), max];
  };
  const [minW, avgW, maxW] = tri(v.weight);
  const [minM, avgM, maxM] = tri(v.muscle);
  const [minC, , maxC] = tri(v['bust.size']);
  const [minF, , maxF] = tri(v['bust.firmness']);
  const avgOf = (min, max) => 1 - Math.max(min, max);
  return {
    female: 1,
    young: 1 - old,
    old,
    minweight: minW, averageweight: avgW, maxweight: maxW,
    minmuscle: minM, averagemuscle: avgM, maxmuscle: maxM,
    minheight: Math.max(0, 1 - v.height * 2), maxheight: Math.max(0, v.height * 2 - 1),
    uncommonproportions: Math.max(0, 1 - v.proportions * 2), idealproportions: Math.max(0, v.proportions * 2 - 1),
    mincup: minC, maxcup: maxC, averagecup: avgOf(minC, maxC),
    minfirmness: minF, maxfirmness: maxF, averagefirmness: avgOf(minF, maxF),
    african: v['ancestry.african'], asian: v['ancestry.asian'], caucasian: v['ancestry.caucasian'],
  };
}

export class MorphEngine {
  constructor(pkg) {
    this.pkg = pkg;
    this.T = pkg.targets;
    this.nb = pkg.meta.baseCount;
    this.base = pkg.basePos;
    this.positions = new Float32Array(this.base); // posições base morfadas (m)
    const n = this.T.names.length;
    this.index = new Map(this.T.names.map((name, i) => [name, i]));
    // alvos macro: lista de variáveis pelo nome do arquivo
    this.macroVars = new Array(n).fill(null);
    for (let i = 0; i < n; i++) {
      const bn = this.T.names[i].split('/').pop();
      const toks = bn.split('-').filter((t) => MACRO_TOKENS.has(t));
      if (toks.length && toks.includes('female')) this.macroVars[i] = toks.filter((t) => t !== 'female');
    }
    this.weights = new Float32Array(n);
    this.detailTraits = TRAITS.filter((t) => t.kind === 'detail');
  }

  computeWeights(values) {
    const w = this.weights;
    w.fill(0);
    const mv = macroVariables(values);
    for (let i = 0; i < w.length; i++) {
      const toks = this.macroVars[i];
      if (!toks) continue;
      let p = 1;
      for (const t of toks) p *= mv[t];
      w[i] = p;
    }
    for (const t of this.detailTraits) {
      const v = values[t.id];
      if (!v) continue;
      const list = v < 0 ? t.neg : t.pos;
      const f = Math.abs(v);
      for (const name of list) {
        const i = this.index.get(name);
        if (i !== undefined) w[i] += f;
      }
    }
    return w;
  }

  /** Recalcula `positions` = base + Σ peso × alvo. */
  update(values) {
    const w = this.computeWeights(values);
    const P = this.positions;
    P.set(this.base);
    const { offset, count, scale, idx, delta } = this.T;
    for (let t = 0; t < w.length; t++) {
      const wt = w[t];
      if (wt > -1e-4 && wt < 1e-4) continue;
      const c = count[t];
      if (!c) continue;
      const k = wt * scale[t];
      let o = offset[t];
      for (let e = 0; e < c; e++, o++) {
        const v = idx[o] * 3;
        const d = o * 3;
        P[v] += delta[d] * k;
        P[v + 1] += delta[d + 1] * k;
        P[v + 2] += delta[d + 2] * k;
      }
    }
    return P;
  }
}
