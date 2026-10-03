# @Mr_HB × Dummy — luta freestyle v2 (120 fps / 60 fps, curvas do Blender, câmera cinematográfica)

Animação vertical **1080×1920** de um personagem Roblox R6 (visual padrão do Roblox, com o nome `@Mr_HB`) lutando com um dummy.
A v2 refaz a v1 (35 s @ 18 fps) com os pedidos:

| Pedido | O que foi feito |
|---|---|
| Bezier / ease do Blender | O movimento agora **é** um conjunto de Actions do Blender (F-curves Bezier, handles *Auto Clamped*, easings do Blender), criadas com o `bpy`. O vídeo, o `.blend` e a exportação Roblox são avaliados dessas mesmas curvas (`FCurve.evaluate`). |
| 120 fps e muito mais suave | Avaliação a **120 fps reais** (5.291 quadros). Versão **60 fps** com rastro leve de movimento (cada quadro = ¾ do quadro de 120 fps + ¼ do anterior). |
| Rigs entrando um no outro | Auditoria de colisão caixa-a-caixa (SAT) em todos os quadros + solver de poses nos impactos + afastamento suave do dummy. Ver "Verificações". |
| Preparação lenta, ação rápida (ex.: espada) | Dilatação de tempo por intervalo: preparação de cada golpe **×1,8 mais lenta**, golpe em *ease-in* (acelera até o contato), hit-stop por força do golpe, câmera lenta nos grandes momentos; pegadas/agarrões com alcance lento (arremesso, agarrar o rosto). |
| Duração livre para coesão | **44,1 s** (antes 35 s). |
| `.blend` com tudo | `blender/MrHB_fight_v2.blend` (Blender 5.x). |
| Trocar o avatar no Roblox Studio | `out/roblox/MrHB_fight.rbxmx` e `Dummy_fight.rbxmx` (KeyframeSequence R6, 60 keys/s, com marcadores). |
| Efeitos com qualidade | Rastros contínuos, faíscas, brilho de impacto com luz, aura de energia animada, poeira iluminada, after-images com borda luminosa, profundidade de campo, ondas de choque com refração, estrelas/estilhaços animados continuamente. |
| Câmera mais imersiva/cinematográfica | Operador com inércia (molas), câmera na mão, tremores senoidais de impacto, punch de lente, órbita "bullet-time" nas câmeras lentas, foco/profundidade de campo, enquadramento mais próximo e baixo. |

## Arquivos

| Caminho | O que é |
|---|---|
| `out/v2/@Mr_HB_fight_120fps.mp4` | vídeo final 120 fps, com áudio |
| `out/v2/@Mr_HB_fight_60fps.mp4` | vídeo 60 fps (para YouTube Shorts / TikTok, que exibem no máximo 60 fps) |
| `out/v2/contact_sheet.jpg` | folha de contato do vídeo final |
| `blender/MrHB_fight_v2.blend` | cena completa para Blender 5.x (ver abaixo) |
| `blender/overlay/` | camada 2D (efeitos desenhados, flashes, títulos) em PNG com alfa, usada pela cena "Edit" do `.blend` |
| `out/roblox/MrHB_fight.rbxmx`, `out/roblox/Dummy_fight.rbxmx` | animações para o Roblox Studio |
| `animation-manifest.json` | pedido, regras de tempo e interpolação, QA de colisão antes/depois, câmera, efeitos, verificações e pendências |
| `authoring/` | fonte: coreografia (v1, `choreo.py`, `beat_*.py`), `timeline.py` (dilatação de tempo), `blcurves.py` + `bl_map.py` (curvas do Blender), `posefix.py` + `spacing.py` (colisões), `camera2.py`, `export2.py`, `blend_build.py`, `rbx_export.py`, `make2.py` |
| `render/`, `post/post2.py`, `audio/synth2.py`, `run_all2.py` | renderizador 3D, pós 2D, áudio e pipeline v2 |
| `out/@Mr_HB_fight_18fps.mp4` etc. | a versão v1 (18 fps), mantida para comparação |

## Abrir no Blender (5.2)

- Cena **Fight3D**: 120 fps, quadros 0–5290, EEVEE, 1080×1920. Armatures `MrHB` e `Dummy` (ossos R6 canônicos, 1 unidade = 1 stud), partes com o visual padrão do Roblox.
  - As Actions `MrHB` e `Dummy` são as curvas que geraram o vídeo: Bezier com handles Auto Clamped, e nos golpes as interpolações do Blender (QUART/CUBIC *Ease In* na chegada do golpe, CONSTANT no alvo antes do toque, BACK *Ease Out* na reação). Os modos de rotação dos ossos são **ZYX** (membros) e **ZXY** (raiz/tronco/cabeça) — não troque, as curvas dependem disso.
  - Curva `location Z` do objeto (grupo **FloorLift**): a restrição de chão (nenhuma parte abaixo do piso) gravada por quadro onde atua.
  - `CAM_Cinematic`: a câmera v2 com chave em todo quadro (posição, rotação, distância focal, foco e f-stop); os cortes estão como chaves CONSTANT e os **marcadores** da timeline têm o nome de cada plano.
  - Coleções `FX` / `FX_Ghosts`: anéis de impacto e de choque, paredes de choque, rachaduras, pilares, faíscas/detritos/poeira (partículas), luzes de flash, arcos dos chutes, after-images (cópias do rig tocando a mesma Action via NLA com atraso) e aura; nome flutuante `@Mr_HB` preso à cabeça.
  - Compositor: bloom + leve dispersão cromática.
- Cena **Edit** (VSE): a cena Fight3D + a camada 2D (`blender/overlay/`, meia resolução) + a marca d'água + a trilha sonora (embutida no arquivo). Renderize a cena **Edit** para ter o vídeo com tudo.
- O visual do EEVEE não é idêntico ao do vídeo (o vídeo foi renderizado fora do Blender, em three.js, com pós 2D próprio): movimento, câmera e tempos são os mesmos.

## Usar no Roblox Studio com o seu avatar

1. Tenha dois rigs **R6** (o seu avatar e um dummy R6) com `HumanoidRootPart` **ancorado**, os dois no **mesmo CFrame** (a mesma origem e orientação).
2. Arraste `MrHB_fight.rbxmx` e `Dummy_fight.rbxmx` para o Studio (ou *Model → Import / Insert from File*). Cada um vira um `KeyframeSequence`.
3. Para editar/publicar no *Animation Editor*: coloque cada `KeyframeSequence` na pasta de salvamentos do editor (normalmente `ServerStorage → RBX_ANIMSAVES → <nome do rig>`, criada quando você salva algo nesse rig) e use *Load*; publique para obter o ID e toque com `Animator:LoadAnimation`. Toque as duas ao mesmo tempo.
4. O deslocamento do corpo pelo cenário está dentro do `RootJoint` (o Roblox não anima o HumanoidRootPart), por isso os dois rigs precisam da mesma origem.
5. Marcadores (`GetMarkerReachedSignal`): `Hit` (valor = força 1–4) em cada impacto; `Hide`/`Show` nos teletransportes do jogador — use para tocar sons/efeitos e esconder o personagem.

## Linha do tempo v2 (preparação lenta, ação rápida)

- Grade de autoria continua a de 18 fps (poses e contatos da v1); um *time-warp* leva cada quadro de história a um quadro inteiro de 120 fps.
- Cada golpe: intervalo de preparação ×1,8 (até +5 quadros de história), intervalo chamber→contato ×0,88 com *ease-in*; o corpo "assenta" na postura carregada (handle plano) e explode no golpe.
- Hit-stop: ×1,5 / ×2,0 / ×2,6 / ×3,2 conforme a força (1–4).
- Câmera lenta (com rampas): lançamento do uppercut, machado duplo + meteoro, chute machado, voadora dupla, rajada de palmas, soltura do arremesso, uppercut-dragão, bicicleta, pilares, lançamento final, super-salto, congelamento antes de agarrar o rosto, cravada final.
- Preparações sem golpe: carga do primeiro dash, alcançar o tornozelo (arremesso), pisão, agachamento do super-salto.
- Detalhes e números por golpe em `animation-manifest.json` (`timing_v2`).

## Como gerar de novo

```bash
pip install bpy==5.0.1 numpy scipy pillow "opencv-python-headless<4.11"
cd animation/render && npm install three && cd ..
python run_all2.py                               # tudo: make, áudio, render, pós, encode, camada 2D, roblox, .blend
python run_all2.py --stage make                  # curvas + solver de colisão (cache em out/v2/solved_keys.json) + câmera
python run_all2.py --stage render --from 0 --to 600   # re-renderizar um trecho (cor + profundidade)
python run_all2.py --stage post && python run_all2.py --stage encode
python run_all2.py --stage blend                 # .blend (+ verificação contra o movimento renderizado)
python run_all2.py --stage roblox                # .rbxmx (+ releitura e verificação)
python run_all2.py --stage manifest              # animation-manifest.json com as medições (colisão antes/depois, câmera)
```

## Verificações feitas (com evidência)

- **Curvas ↔ R6**: o mapeamento pose semântica → canais Euler/location do Blender foi conferido contra a FK do R6 da skill: erro máximo **1,1×10⁻⁶ stud**.
- **`.blend` = vídeo**: a cena salva foi avaliada pelo *depsgraph* do Blender (bpy 5.0.1) em 40 quadros espalhados e comparada com o movimento renderizado: diferença máxima **0,00013 stud** nos centros das partes (com a curva FloorLift; sem ela a diferença chegava a 2,9 studs — por isso a curva existe). Três quadros do `.blend` renderizados em Cycles batem com o enquadramento do vídeo.
- **Roblox**: os dois `.rbxmx` foram relidos com o parser da skill (`rbx.py`) e comparados com as curvas: erro máximo **0,0003 stud** (MrHB) e **0,0002 stud** (Dummy); 2.646 keyframes cada (44,08 s), 75 / 63 marcadores.
- **Determinismo**: refazer o solver de colisão do zero reproduz o movimento renderizado com diferença de **0,00005 stud**.
- **Colisão jogador × dummy** (caixas reais das partes, SAT, todos os quadros a 120 fps; contatos de golpe e agarrões permitidos): **antes** (tempo v2 sem correção) 2.478 quadros = **46,8 %**, até **1,63 stud** de penetração; **depois** 156 quadros = **2,95 %**, 12 trechos acima de 0,6 stud, o pior 1,15 stud (lista em `animation-manifest.json` → `interpenetration_v2`).
- **Contatos**: a ponta de cada golpe toca o alvo no quadro do impacto (≈0,1 stud, incluindo a folga de "atravessar"); exceção: o 3º quadro do hit-stop do primeiro soco (0,30 stud).
- **Câmera**: 79 cortes; assunto parcialmente fora do quadro em 3,6 % dos quadros (pontas de membros em golpes rápidos); velocidade da câmera mediana 15,8 studs/s, máx. 301 (tremores de impacto); câmera nunca abaixo de 0,9 stud do chão; distância mínima a um centro de parte 2,4 studs.
- **Áudio**: 44,09 s, pico −1,0 dB, tempo de 120,22 BPM alinhado para que o 1º golpe e a cravada final caiam exatamente na batida.
- **Vídeos** inspecionados com `ffprobe`: 120 fps → 1080×1920, `120/1`, **5.291 quadros, 44,09 s**, H.264 High@5.2 (~13 Mb/s) + AAC 44,09 s, 71 MB; 60 fps → `60/1`, **2.646 quadros, 44,10 s**, 53 MB. Quadros decodificados dos próprios MP4 conferidos visualmente.
- Revisão visual: folhas de contato de sequências contínuas (combo no chão, quadros-chave de todas as cenas) e a folha final `out/v2/contact_sheet.jpg`. **Não** assisti ao vídeo em tempo real (não há player aqui); a suavidade foi checada por estatísticas de velocidade/aceleração das partes e da câmera.

## Limitações honestas

- O vídeo de referência do YouTube continua inacessível daqui (bloqueio anti-bot; a skill proíbe contornar). O estilo segue a sua descrição + miniaturas.
- **Blender 5.2 não estava disponível**: o `.blend` foi gerado e verificado com o `bpy` 5.0.1. O Blender abre arquivos de versões anteriores, então deve abrir no 5.2, mas não testei no 5.2.
- No `.blend`, os efeitos 3D são equivalentes nativos (objetos, partículas, luzes) — não idênticos aos do renderizador do vídeo: partículas de poeira/detritos/faíscas usam física em tempo real (não desaceleram na câmera lenta), e os rastros contínuos dos membros e os riscos do meteoro não foram recriados em 3D. Os efeitos 2D estão na cena **Edit** como camada de imagens (meia resolução); os quadros de impacto estilo mangá (imagem invertida), o bloom/DOF/aberração do pós e a pós-produção do vídeo não estão no `.blend` (o compositor tem bloom e dispersão próprios).
- **Sobreposições restantes** (curtas, todas em contatos de golpe): uppercut (f72, ~0,2 s incluindo o hit-stop), rasteira (f128), chutes aéreos (f84–94), uppercut-dragão (f285), bicicleta (f296), início da rajada (f497), braço na cabeça ao agarrar o rosto (f539). São membros/cabeças encostando além do ideal por alguns quadros; fora desses trechos sobram só toques leves (< 0,6 stud) em contatos.
- Roblox: o deslocamento pelo cenário está no `RootJoint`; os dois rigs precisam estar ancorados na mesma origem. O personagem não some sozinho nos teletransportes — use os marcadores `Hide`/`Show`.
- 120 fps: YouTube Shorts e TikTok exibem no máximo 60 fps — para postar use a versão de 60 fps; a de 120 fps é para players/monitores de alta taxa.
- A v1 (18 fps) foi mantida como estava renderizada. O código agora inclui dois ajustes de autoria da v2 (jogador mais afastado na rasteira; sub-keys no giro do arremesso), então rodar o pipeline v1 de novo não reproduz exatamente o vídeo v1.
