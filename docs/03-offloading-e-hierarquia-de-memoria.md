# 03 — Offloading e hierarquia de memória: VRAM → RAM → SSD

Se os pesos não cabem na VRAM, eles moram em outro lugar. Este documento sistematiza os quatro
regimes de offloading, os sistemas de referência de cada um, e as leis que decidem qual usar.

## 1. A hierarquia e suas bandas (hardware antigo típico)

| Nível | Banda típica | Latência | Capacidade |
|---|---|---|---|
| VRAM (GTX 1050 Ti / 970) | 112–224 GB/s | ~µs | 4 GB |
| RAM DDR4 dual-channel | 30–45 GB/s | ~100 ns | 16–64 GB |
| RAM DDR3 dual-channel | 17–25 GB/s | ~100 ns | 8–32 GB |
| PCIe 3.0 x16 (GPU↔RAM) | 12–16 GB/s | ~µs | — |
| NVMe SSD | 2–7 GB/s | ~80 µs | 0,5–2 TB |
| SATA SSD | ~0,55 GB/s | ~100 µs | 0,5–2 TB |

Duas observações estruturais:

1. **PCIe < RAM**: transferir um peso da RAM para a GPU para computá-lo é mais lento do que
   computá-lo na CPU diretamente. Corolário: **no decode, offload de *computação*, não de dados** —
   a camada que mora na RAM deve ser executada pela CPU.
2. **A exceção é o prefill**: com muitos tokens processados de uma vez, o custo de subir a camada
   pela PCIe se amortiza e a GPU compensa mesmo para camadas residentes na RAM (é o que o
   llama.cpp faz com lotes grandes).

## 2. Regime A — Offload parcial de camadas (llama.cpp `-ngl`)

O mecanismo clássico: as primeiras N camadas moram na VRAM e computam na GPU; o resto mora na RAM e
computa na CPU. O tempo por token é a soma dos dois estágios — governado pela **média harmônica**
das bandas, o que significa que a parte lenta domina rapidamente:

```
t_token ≈ bytes_gpu/B_vram + bytes_cpu/B_ram
```

Com 4 GB de VRAM e um denso de 20B (~12 GB em Q4), só ~25% cabe na GPU → ganho modesto (~1,2–1,4×)
sobre CPU pura. **Offload de camadas inteiras é a estratégia errada para VRAM pequena.** A
estratégia certa é o offload *seletivo por tipo de tensor* (regime B).

## 3. Regime B — Offload seletivo por tensor (a receita-chave)

Insight (formalizado nos sistemas MoE, mas válido em geral): os tensores de um transformer têm
papéis assimétricos:

- **Atenção + KV cache**: pequenos em bytes, mas acessados intensivamente e com padrões irregulares
  → **VRAM**.
- **FFN/experts**: 2/3+ dos bytes, acesso sequencial previsível → **RAM/CPU**.

No llama.cpp isso é expresso com `--n-gpu-layers 99` + `--override-tensor`:

```bash
-ngl 99 -ot "ffn_.*_exps=CPU"     # MoE: experts na RAM, resto na GPU
-ot "ffn_(up|down|gate).*=CPU"    # denso: FFN na RAM, atenção na GPU
```

Para um MoE 20B, "o resto" (atenção, embeddings, normas, router) ocupa ~2–3 GB → **cabe nos 4 GB**,
e o decode toca só os ~2 GB de experts ativos na RAM. É assim que 20B+ vira interativo com 4 GB.

## 4. Regime C — Agendamento com programação linear (FlexGen)

FlexGen (ICML 2023) formalizou o offloading como problema de otimização: dado um grafo de
computação e as capacidades/bandas de GPU, CPU e disco, um programa linear escolhe onde cada tensor
mora e em que ordem os lotes percorrem o grafo ("zig-zag block schedule"), agregando memória dos
três níveis. Com compressão de pesos e KV para 4 bits, rodou OPT-175B em uma única GPU de 16 GB.

Lição transferível: FlexGen otimiza **vazão** (tokens/s agregado sobre lotes grandes), não
latência. É o regime certo para cargas offline em lote (classificar 10 mil documentos de madrugada),
não para chat. Em 4 GB de VRAM, a mesma matemática se aplica com constantes piores.

## 5. Regime D — Streaming camada-a-camada do disco (AirLLM)

O extremo: nenhuma tentativa de residência. O modelo é fatiado em camadas no disco; a cada passada,
carrega-se a camada i na GPU, computa-se, descarta-se, carrega-se a i+1 (com prefetch assíncrono da
próxima camada sobrepondo E/S e computação). Pico de VRAM: uma camada (~1,5–2 GB para 70B) →
**70B roda em 4 GB de VRAM**, e até 405B em 8 GB.

Custo: cada token exige reler o modelo inteiro do disco → 0,5–2 tok/s com NVMe rápido; inviável em
SATA/HD. Uso legítimo: avaliação offline, geração em lote onde latência não importa, e como prova
de conceito de que "impossível" era, na verdade, "lento".

## 6. Regime E — SSD como memória de pesos com consciência de esparsidade ("LLM in a flash", Apple)

O paper da Apple (ICLR 2025) é a ponte entre offloading e esparsidade: mantém embeddings e atenção
na DRAM e **transmite da flash apenas os neurônios de FFN que o preditor diz que serão ativados**,
com duas técnicas específicas de flash:

- **Windowing**: reutiliza neurônios ativados nos últimos k tokens (localidade temporal de
  ativação), reduzindo o volume transferido.
- **Row-column bundling**: armazena a linha da projeção-up junto da coluna da projeção-down do
  mesmo neurônio, dobrando o tamanho das leituras contíguas (flash rende mais em leituras grandes).

Resultado: modelos 2× maiores que a DRAM disponível com 4–5× (CPU) a 20–25× (GPU) a velocidade da
carga ingênua. Este paper é a fundação direta da nossa proposta no doc 07: em um PC antigo, o SSD
NVMe é "a flash", a RAM é "a DRAM", e MoE nos dá a esparsidade *estruturada* que dispensa preditor.

## 7. mmap, páginas e o sistema operacional como aliado

O llama.cpp mapeia o GGUF com `mmap` por padrão: as páginas de pesos entram na RAM sob demanda e o
page cache do SO gerencia a residência. Consequências práticas:

- Um modelo *maior que a RAM* "roda" sem configuração extra — o SO paginará do SSD. Com MoE, o
  conjunto de trabalho (experts quentes) tende a caber na RAM e a paginação se estabiliza
  (é a versão "de graça" do regime E).
- `--mlock` trava o modelo na RAM (evita despejo por outras cargas) — usar quando o modelo cabe.
- No Linux, `MADV_WILLNEED`/readahead agressivo do NVMe ajuda o primeiro carregamento.
- **Swap em HD mecânico inviabiliza tudo** — SSD é requisito duro para os regimes D/E.

## 8. Árvore de decisão

```
O modelo é MoE?
├── SIM → Regime B (atenção na VRAM, experts na RAM; overflow de experts no SSD via mmap)
└── NÃO (denso)
    ├── Quantizado cabe na RAM? → Regime B (atenção na VRAM, FFN na RAM) — 2–5 tok/s p/ 20B
    └── Não cabe nem na RAM?
        ├── Preciso de latência? → modelo menor ou BitNet (doc 02)
        └── Carga em lote/offline? → Regime C/D (FlexGen/AirLLM) — 70B possível
```
