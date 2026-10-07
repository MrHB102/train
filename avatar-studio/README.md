# Avatar Studio

Personalizador de avatar feminino adulto (**torso e pernas, sem cabeça e sem braços**) que roda no navegador com three.js (WebGL2). Corpo anatomicamente fiel, proporções que vão do natural ao exagerado com **repique elástico**, roupas (bunny girl, maid, colegial…), pele com anatomia visível e física (carne, saia, avental, rabo).

> Vocabulário do projeto em [GLOSSARY.md](GLOSSARY.md); decisões em [docs/adr](docs/adr).

## Rodar

```bash
npm install
npm run dev        # http://localhost:5173
npm run build      # dist/ (JS ≈ 940 kB, 255 kB gzip; dados 3 MB)
npm run preview    # serve dist/
```

Qualquer navegador moderno com WebGL2. Em celulares e máquinas fracas use *Pose e cena → Qualidade gráfica → Leve*.

## O que dá para fazer

| Aba | Conteúdo |
|---|---|
| **Corpo** | Regiões (geral, busto, cintura, quadril, glúteos, coxas, pernas, ombros). Sliders de 0 a 100 sobre a faixa estendida: a marca laranja é o limite natural, além dela é o modo exagerado. Dials de tamanho (busto, glúteos, quadril, coxas), estilos rápidos (Curvas, Proporções anime, Malhada ↔ Macia), caído ↔ empinado, dobra e sulco dos glúteos, silhuetas, mistura de morfologias, painel 2D da posição do busto. |
| **Pele** | Tons, subtom, **pele perfeita** (remove poros, manchas, sardas, pintas, veias, vermelhidão e penugem de uma vez ou uma a uma), brilho, translucidez, glitter, esmalte, **anatomia** (clavículas, tendões do pescoço, abdômen, umbigo, ossos do quadril, costelas, costas). |
| **Roupas** | Conjuntos prontos, biquíni-base (triângulo ou bandeau, calcinha clássica ou boyshort), peças com tecido, cor, padrão, acabamento, costuras e medidas editáveis. Enchimento do busto: 0 = tecido fino que marca o contorno. |
| **Dinâmica** | Repique elástico (liga/desliga e intensidade), Jiggle por região, amortecimento e firmeza, vento e rigidez dos tecidos. |
| **Pose e cena** | Poses (pés e coxas juntos, contrapeso, passarela…), movimentos (respirar, caminhar, desfilar, dançar, saltitar, girar), altura do salto, foco de câmera, qualidade gráfica, exposição. |
| **Presets** | Personagens prontos (Natural, Anime curvilínea, Atlética, Delicada, Coxas grossas, Exagerada, Gigante), salvar/carregar no navegador, **código para compartilhar**, JSON, captura de tela. |

Atalhos: `Ctrl+Z` desfaz, `Ctrl+Y` refaz. Duplo clique no nome de um slider volta ao neutro.

## Como é feito

- **Corpo**: malha base CC0 do MakeHuman (torso e pernas, cortada no pescoço e nos ombros), subdividida (Catmull-Clark) e morfada por alvos CC0 mais morfes procedurais (volumes, caído/empinado, dobra, sulco). Rig de 64 ossos com juntas virtuais para busto, glúteos, coxas e barriga. `tools/build-assets.mjs` gera o pacote binário.
- **Roupas**: *Shells* recortados da superfície do corpo por campos escalares (seguem qualquer morph e pose), *Ribbons* (cordões e alças presos à superfície), *Drapes* (saia e avental em PBD com colisão; o avental nunca atravessa a saia e o peitilho passa por cima do corpete com enchimento), objetos rígidos (laço, salto), o bico do sapato (casco procedural) e o rabo de pelo (cascas instanciadas + mola). Padrões (bolinhas, xadrez, tartan) são medidos em metros sobre o tecido.
- **Shaders**: pele com espalhamento subsuperficial pré-integrado, imperfeições procedurais ancoradas no corpo e anatomia por campo de altura; tecidos procedurais (cetim, látex, couro, jeans, veludo, renda, arrastão, meia fina).
- **Repique**: cada Trait/Dial segue o alvo por uma mola subamortecida e dá um impulso no Jiggle (ADR 0008).
- **Física**: Jiggle (massa-mola 3D por região), saia/avental PBD, rabo com mola.

## Verificação

```bash
npm run validate   # modelo (15 verificações), catálogo de Traits e roupas (59 verificações)
npm run build && npm run preview &   # e depois:
npm run e2e        # 25 verificações no navegador (Chromium headless)
```

`tools/validate-model.mjs`, `validate-garments.mjs` e `check-domain.mjs` seguem os princípios do skill `3d-modeling` (unidades em metros, orientação Y para cima/frente +Z, topologia sem arestas non-manifold, normais para fora, pesos de skinning, simetria, orçamento de triângulos, camadas de roupa, densidade de padrão em metros). `tools/e2e.mjs` percorre a interface e falha com qualquer erro de console.

## Estrutura

```
src/avatar     corpo, morph, rig, anatomia, repique, animação, cápsulas
src/domain     catálogos: Traits, Dials, pele, roupas, presets
src/garments   contexto, Shell, Ribbon, Dresser, construtores, saia/avental, objetos, sapatos
src/physics    Jiggle, tecido PBD, colisores
src/shaders    pele, tecidos, texturas procedurais
src/engine     renderer, câmera, luzes, palco
src/app        App (estado, histórico, compartilhar), src/ui interface
tools          pipeline de dados, validações, e2e, captura de tela, empacotamento
```

## Licenças e origem dos dados

- Malha, alvos, pesos e rig: **MakeHuman** (assets CC0).
- three.js: MIT. O resto do código e as roupas procedurais são deste projeto.
- As roupas (bunny girl, maid…) são **modeladas proceduralmente**; não existe repositório CC0 delas.

## Decisões e limites

- Torso e pernas apenas: sem cabeça, braços, orelhas, cabelo, punhos ou rosto. Os cortes são fechados por cápsulas de manequim.
- Só mulher adulta (idade de 25 a 80) e a camada-base sempre presente; o corpo nunca é mostrado nu.
- O skill `3d-modeling` foi instalado sem as pastas `references/`; foram aplicados os princípios do texto principal.
- O bico dos sapatos é um volume estilizado (não a forma dos dedos). A anatomia da pele é relevo e sombra, não muda a silhueta.
