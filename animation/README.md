# @Mr_HB × Dummy — luta freestyle de 35 s (Roblox R6, 18 fps)

Animação vertical **1080×1920**, **18 fps reais**, **35,0 s (630 quadros)**, feita com a skill `r6-animator`
(DSL/FK do R6) e renderizada **fora do Blender** por um renderizador 3D offline (three.js em Chromium headless)
mais uma camada de pós-processamento 2D. Personagem do jogador e dummy usam o visual **padrão do Roblox R6**
(sem skin customizada); o nome `@Mr_HB` aparece flutuando sobre o personagem, como marca d'água e no título final.

> **Importante sobre a referência:** o YouTube bloqueou o download do Short (HTTP 429 / "confirme que você não é um robô")
> e a skill proíbe contornar isso. Só consegui metadados públicos e 4 miniaturas estáticas. **Não vi o movimento do vídeo**;
> o estilo (18 fps, dashes, efeitos, golpes rápidos e exagerados) vem da sua descrição + o que as miniaturas mostram
> (enquadramento vertical, câmera baixa, bloom, aberração cromática, efeitos desenhados à mão). Veja "Refinar com o vídeo".

## Arquivos

| Caminho | O que é |
|---|---|
| `out/@Mr_HB_fight_18fps.mp4` | vídeo final, 18 fps nativos, com áudio |
| `out/@Mr_HB_fight_18fps_silent.mp4` | mesmo vídeo sem áudio |
| `out/@Mr_HB_fight_36fps_compat.mp4` | cada quadro repetido 2× (36 fps) para plataformas que estragam 18 fps |
| `out/contact_sheet.jpg` | folha de contato do vídeo final (a cada 6 quadros) |
| `out/clips/mrhb.baked.json`, `dummy.baked.json` | clipes R6 (um key por quadro) do jogador e do dummy, exatamente o que foi renderizado — para importar no Blender depois (`r6.clip_from_json` / `r6.build`) |
| `animation-manifest.json` | brief, ferramentas, evidência da referência e seus limites, beat sheet, tabela de impactos, QA e pendências |
| `authoring/` | coreografia original (Python): `choreo.py` (beats 1–3), `beat_*.py` (beats 4–14), `direction*.py` (câmera/efeitos), `cam.py`, `fx.py`, `rig.py`, `actor.py` |
| `render/` | cena three.js (`scene.js`) e driver headless (`render.mjs`) |
| `post/post.py` | bloom, aberração cromática, vinheta, blur, estrelas/estilhaços/linhas de velocidade, quadros de impacto, títulos |
| `audio/synth.py` | trilha e SFX sintetizados (120 BPM = 9 quadros por batida) |
| `run_all.py` | pipeline completo |
| `../.claude/skills/r6-animator/` | a skill instalada no projeto |

## Como gerar de novo

```bash
pip install pillow numpy scipy matplotlib opencv-python-headless
cd animation/render && npm install three && cd ..
python run_all.py                          # make -> áudio -> render 3D -> pós -> encode
python run_all.py --stage render --from 120 --to 180   # só re-renderizar um trecho
python run_all.py --stage post && python run_all.py --stage encode
```

Revisão rápida de blocking (folha de contato em baixa resolução, qualquer trecho):
`python authoring/make.py --review 0 629 6 --scale 0.2 --cols 7 --name overview`

## Beat sheet (120 BPM, 1 batida = 9 quadros)

| s | beat | conteúdo |
|---|---|---|
| 0,0–1,6 | Hook | plano de herói, nome pop-in, preparação do dash |
| 1,7–3,0 | Dash strike | dash com afterimages, soco (f36), dummy arremessado, queda e deslize |
| 3,0–4,0 | Combo no chão | jab, cross, gancho, chute, uppercut (lançamento em f72) |
| 4,1–6,1 | Combo aéreo | salto, chutes, giro, flip kick, machado duplo, queda de meteoro (f102) |
| 6,2–6,9 | Calma | pouso heroico, provocação, dummy salta de pé |
| 6,9–9,8 | Chutes freestyle | rasteira, flip + axe kick, side kick, hook giratório, cartwheel, voadora dupla |
| 9,8–12,4 | Blink | 6 teletransportes, golpes de 6 lados, rajada de palma |
| 12,4–14,6 | Arremesso | agarra o tornozelo, 2,75 voltas, solta |
| 14,6–17,4 | Helicóptero | breakdance em parada de mão, uppercut-dragão, bicycle kick |
| 17,4–20,3 | Pilares | caminhada calma, pisão, 3 pilares de rocha |
| 20,3–22,5 | Malabarismo | joelho, peito do pé, cabeçada, coxa, joelho, lob |
| 22,5–27,2 | Carga | giro 540°, mortal, deslize, aura e rochas flutuando |
| 27,2–30,0 | Finalização | super salto, rajada de 14 socos, freeze, agarra o rosto, mergulho, cravada (f541) |
| 30,1–35,0 | Epílogo | cratera, caminhada, pose final e título |

## Refinar com o vídeo

Envie o `.mp4` do Short (ou um trecho). Com ele eu rodo `video_reference.py` da skill, **vejo os quadros em sequência** e
ajusto ritmo, espaçamento dos golpes, duração dos hit-stops, câmeras e efeitos — tudo está parametrizado
(`authoring/beat_*.py`, `direction*.py`, `fx.py`, `post/post.py`) e o re-render de um trecho leva poucos minutos.

## Limitações honestas

- Não executei Blender; nada foi verificado dentro do Blender. Os clipes `*.baked.json` são entrada pronta para o `r6.build()`.
- O movimento da referência não foi observado (ver acima).
- Deslizes de pé no mundo durante dashes/slides são intencionais; não declarei planos de apoio no `qa.py`.
- Há trechos de poses extremas com 1–3 quadros de sobreposição de membros (escondidos por efeitos de impacto).
