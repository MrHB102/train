#!/usr/bin/env node
// Teste de contrato: todo Morph Target citado pelo catálogo de Traits existe no pacote convertido.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { TRAITS, detailTargetNames } from '../src/domain/traits.js';

const dir = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'public', 'data');
const manifest = JSON.parse(fs.readFileSync(path.join(dir, 'targets.json'), 'utf8'));
const have = new Map(manifest.targets.map((t) => [t[0], t]));
let bad = 0;
for (const n of detailTargetNames()) {
  const t = have.get(n);
  if (!t) {
    console.error('FALTA no pacote:', n);
    bad++;
  } else if (t[2] === 0) {
    console.warn('vazio:', n);
  }
}
const ids = new Set();
for (const t of TRAITS) {
  if (ids.has(t.id)) {
    console.error('Trait duplicado:', t.id);
    bad++;
  }
  ids.add(t.id);
  if (!(t.natural[0] <= t.neutral && t.neutral <= t.natural[1])) {
    console.error('Neutral fora do Natural Range:', t.id);
    bad++;
  }
  if (!(t.extended[0] <= t.natural[0] && t.natural[1] <= t.extended[1])) {
    console.error('Extended Range não contém o Natural Range:', t.id);
    bad++;
  }
}
console.log(`${TRAITS.length} traits, ${detailTargetNames().length} morph targets citados, ${bad} problema(s)`);
process.exit(bad ? 1 : 0);
