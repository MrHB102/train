# 01 — Fundamentos e limites: por que "dizem que é impossível" e onde o argumento falha

## 1. A aritmética de memória de um LLM

Um modelo de linguagem é, para fins de inferência, três blocos de memória:

1. **Pesos** — `N_params × bytes_por_parâmetro`
2. **Cache KV** — cresce com o contexto: `2 × n_camadas × n_kv_heads × head_dim × bytes × n_tokens`
3. **Buffers de computação** — ativações intermediárias, workspace de kernels (centenas de MB a ~2 GB)

Para um denso de 20B parâmetros:

| Precisão | bits/peso | Tamanho dos pesos |
|---|---|---|
| FP16 | 16 | 40 GB |
| Q8_0 | ~8,5 | ~21 GB |
| Q4_K_M | ~4,8 | ~12 GB |
| IQ3_XXS | ~3,1 | ~7,7 GB |
| IQ2_XXS | ~2,1 | ~5,2 GB |
| IQ1_S | ~1,6 | ~3,9 GB |

**A leitura ingênua**: mesmo na quantização mais agressiva utilizável, um denso de 20B não cabe em
4 GB de VRAM junto com KV cache e buffers. Logo, "impossível". Essa é a conta que fundamenta o
consenso de que 4 GB limita você a modelos de 3–4B.

## 2. Onde o argumento falha (as três premissas ocultas)

O argumento da impossibilidade assume três coisas, todas falsas:

**Premissa oculta 1: "os pesos precisam estar na VRAM".**
Falso. A VRAM é o topo de uma hierarquia: VRAM (~100–450 GB/s em GPUs antigas) → RAM
(~25–50 GB/s DDR4 dual-channel) → NVMe (~3–7 GB/s) → SATA SSD (~0,5 GB/s). Inferência é
possível a partir de *qualquer* nível — o custo é velocidade, não viabilidade (FlexGen, AirLLM,
"LLM in a flash"; ver doc 03).

**Premissa oculta 2: "todo peso é tocado a cada token".**
Falso para modelos esparsos. Em um MoE como o gpt-oss-20b, dos 21B parâmetros totais apenas
**3,6B são ativados por token** (4 de 128 experts por camada). Em modelos densos com ativações
ReLU-like, PowerInfer mostrou que a ativação de neurônios segue lei de potência: um pequeno
conjunto de neurônios "quentes" responde pela maioria das ativações. O tráfego de memória real
por token pode ser 5–10× menor que o tamanho do modelo (ver doc 04).

**Premissa oculta 3: "a GPU faz todo o trabalho".**
Falso. Na fase de *decode* (geração token a token), a inferência é limitada por **largura de
banda de memória**, não por FLOPs. Uma CPU antiga tem FLOPs de sobra para batch=1; o que falta
é banda. Isso muda completamente o papel da GPU de 4 GB: ela não precisa hospedar o modelo,
precisa hospedar **a parte densa em banda** (atenção + KV cache) enquanto a RAM hospeda a parte
esparsa (FFN/experts).

## 3. O modelo de desempenho que governa tudo

A equação central desta pesquisa. Velocidade de geração em batch=1:

```
tok/s ≈ B_efetiva / bytes_tocados_por_token
```

onde `bytes_tocados_por_token` = pesos *ativos* (na quantização usada) + leitura do KV cache, e
`B_efetiva` é a banda do nível de memória onde esses bytes moram (ou uma média harmônica ponderada,
quando os bytes estão divididos entre níveis).

Exemplos numéricos (DDR4 dual-channel ≈ 40 GB/s úteis):

| Modelo | Bytes ativos/token (Q4) | tok/s teórico em RAM | Verificado na prática |
|---|---|---|---|
| Denso 20B | ~11 GB | ~3,6 | 2–5 tok/s ✔ |
| Denso 70B | ~38 GB | ~1,0 | 0,5–1,5 tok/s ✔ |
| MoE 21B (3,6B ativos, MXFP4) | ~2,3 GB | ~17 | 10–30 tok/s ✔ |
| MoE 30B-A3B (3B ativos, Q4) | ~1,9 GB | ~21 | 12–25 tok/s ✔ |

Três consequências práticas imediatas:

1. **Dual-channel dobra a velocidade.** Dois pentes de RAM em canais distintos ≈ 2× a banda de um
   pente único. É o upgrade mais barato e mais impactante em um PC antigo.
2. **Quantizar é ganhar banda, não só espaço.** Q4 vs FP16 = 4× menos bytes/token = ~4× mais tok/s
   no mesmo hardware.
3. **MoE é a arbitragem perfeita para hardware antigo**: capacidade de 20–30B com o tráfego de
   memória de um 3B.

## 4. Prefill vs decode: as duas fases têm gargalos opostos

- **Prefill** (processar o prompt): paralelo sobre todos os tokens → limitado por **FLOPs**. Aqui a
  GPU de 4 GB ajuda muito mesmo sem hospedar pesos: camadas podem ser transferidas sob demanda e o
  custo de transferência se amortiza sobre o batch de tokens do prompt.
- **Decode** (gerar): sequencial, um token por vez → limitado por **banda**. Transferir pesos
  PCIe→GPU a cada token seria mais lento que computar na CPU (PCIe 3.0 x16 ≈ 12–16 GB/s < banda da
  RAM). Por isso a regra: **no decode, o peso computa onde mora**.

Essa assimetria fundamenta a divisão de trabalho ótima do doc 06: GPU = atenção + KV cache +
prefill; CPU/RAM = FFN/experts no decode.

## 5. O gargalo do cache KV em contexto longo

Com 4 GB de VRAM, o KV cache compete com tudo. Para um 20B típico
(48 camadas, GQA com 8 kv-heads de 128 dim), FP16:

```
bytes/token = 2 × 48 × 8 × 128 × 2 ≈ 196 KB/token  →  8K tokens ≈ 1,6 GB
```

Mitigações (todas usadas no guia prático): quantização do KV para Q8/Q4 (2–4× menos),
FlashAttention (elimina a materialização da matriz de atenção), GQA/MLA nativos do modelo, e
janela de contexto disciplinada.

## 6. Síntese: o espaço de projeto

Rodar 20B+ com 4 GB de VRAM é escolher um ponto neste espaço de quatro eixos:

| Eixo | Alavanca | Custo |
|---|---|---|
| **Precisão** | quantização 4→2→1,58 bits | perda de qualidade (não-linear; ver doc 02) |
| **Localidade** | offload VRAM→RAM→SSD | latência (ver doc 03) |
| **Esparsidade** | MoE / preditores de ativação | escolha de modelo / preditor (ver doc 04) |
| **Redundância temporal** | decodificação especulativa, cache de prompt | complexidade de sistema |

A proposta de pesquisa original deste projeto (doc 07) combina os quatro eixos em um sistema único
para a classe "4 GB VRAM + 16–32 GB RAM + SSD".
