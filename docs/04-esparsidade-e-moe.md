# 04 — Esparsidade e Mixture-of-Experts: a técnica que muda o jogo

Quantização e offloading tornam 20B+ *possível* em 4 GB de VRAM. Esparsidade é o que o torna
**interativo**. A ideia unificadora: se apenas uma fração dos parâmetros participa de cada token,
então o tráfego de memória por token — o que define tok/s (doc 01) — é proporcional à fração ativa,
não ao tamanho total.

## 1. Esparsidade de ativação em modelos densos (PowerInfer)

PowerInfer (SOSP 2024, SJTU) mediu que em FFNs com ativações ReLU-like a ativação de neurônios
segue **lei de potência**: um pequeno núcleo de neurônios "quentes" é ativado para quase qualquer
entrada, enquanto a longa cauda de neurônios "frios" é ativada raramente e dependendo da entrada.

Arquitetura resultante — diretamente aplicável à nossa classe de hardware:

- **Neurônios quentes → pré-carregados na GPU** (pequenos o suficiente para uma VRAM modesta);
- **Neurônios frios → computados na CPU** quando um preditor de ativação (MLP pequeno por camada)
  diz que serão necessários;
- Operadores esparsos "neuron-aware" evitam computar (e ler!) os neurônios não ativados.

Resultado: até ~11× sobre llama.cpp em GPU de consumo, com modelos maiores que a VRAM. Limitações
honestas: exige modelos com esparsidade de ativação real (famílias ReLU/ReGLU — LLaMA com SiLU tem
esparsidade fraca; derivados "Turbo Sparse"/ProSparse retreinam para recuperá-la) e um preditor por
camada que consome VRAM. É a ponte conceitual para o caso que realmente nos interessa: MoE, onde a
esparsidade é **estrutural e exata** (o router *declara* quem participa — não precisa de preditor).

## 2. MoE: esparsidade estruturada de fábrica

Em um transformer MoE, cada FFN é substituída por E experts; um router escolhe k por token
(k ≪ E). Parâmetros totais ≠ parâmetros ativos:

| Modelo | Total | Ativos/token | Experts | Bytes ativos (quant.) |
|---|---|---|---|---|
| **gpt-oss-20b** | 21B | **3,6B** (4/128) | 128/camada | ~2,3 GB (MXFP4) |
| **Qwen3-30B-A3B** | 30B | **3,3B** (8/128) | 128/camada | ~1,9 GB (Q4) |
| Mixtral-8x7B | 47B | 13B (2/8) | 8/camada | ~7 GB (Q4) |

A conta do doc 01 aplicada: 2 GB ativos/token ÷ 40 GB/s de DDR4 ≈ **20 tok/s no CPU** — confirmado
na prática (gpt-oss-20b: ~30 tok/s reportados em setups CPU-bound; Qwen3-30B-A3B: 12–25 tok/s em
CPUs de desktop). **Um PC de 2017 com 32 GB de RAM roda um modelo da classe 20–30B a velocidade de
conversa.** Este é o resultado central que invalida o "não é possível".

### Por que os MoE modernos são ideais para 4 GB de VRAM

A parte **não-expert** (atenção, embeddings, normas, router) do gpt-oss-20b soma ~2–3 GB
quantizada — cabe na VRAM. Os experts (o grosso dos bytes) têm acesso esparso → RAM. O KV cache
(GQA + sliding window attention no gpt-oss) é compacto → VRAM. A arquitetura MoE moderna parece
desenhada sob medida para a divisão VRAM-pequena/RAM-grande.

## 3. Sistemas de execução MoE em hardware limitado

### 3.1 Mixtral-offloading (Eliseev & Mazur, 2023)
Primeiro a explorar duas regularidades do roteamento para hardware de consumo:
**(a) localidade temporal** — tokens adjacentes tendem a reusar experts → cache LRU de experts na
VRAM funciona; **(b) previsibilidade antecipada** — o hidden state da camada i já indica os experts
da camada i+1 → **prefetch especulativo** esconde a latência de subir o expert. Com quantização
mista (HQQ), rodou Mixtral-8x7B interativo em GPUs de 11–16 GB e no Colab gratuito.

### 3.2 KTransformers (SOSP 2025, Tsinghua/MADSys)
O estado da arte em inferência híbrida CPU/GPU para MoE: kernels de CPU otimizados (AMX/AVX-512,
layout ciente de cache), agendamento assíncrono CPU-GPU com CUDA Graphs, e **expert deferral** —
adiar a computação de experts de baixa contribuição para sobrepor com a GPU, elevando a utilização
da CPU a ~100% (4,6–19,7× no prefill, 1,25–4× no decode vs. sistemas anteriores). Embora os kernels
AMX exijam Xeons recentes, o *princípio arquitetural* (CPU cuida dos experts, GPU do resto, com
sobreposição agressiva) é o que o llama.cpp implementa de forma portátil via `-ot`.

### 3.3 A linha de pesquisa de caching/prefetch de experts
ExpertFlow, OD-MoE, WiSP e os estudos de caching (arXiv 2511.05814) convergem em três achados:
(i) a distribuição de uso de experts é desbalanceada (uns poucos experts são "quentes") — caches
LRU/LFU pequenos têm hit rate alto; (ii) preditores de roteamento baseados no estado das camadas
anteriores atingem alta precisão de prefetch; (iii) com compensação de baixo posto (low-rank) para
experts comprimidos, o tráfego cai ainda mais (12–18 tok/s em Mixtral-8x7B offloaded vs 2,4 do
baseline). Estes três achados são os blocos de construção da nossa proposta no doc 07.

## 4. Decodificação especulativa: esparsidade no tempo

Ortogonal às anteriores: um **modelo-rascunho pequeno** (0,5–1B, residente inteiro na VRAM de 4 GB)
propõe k tokens; o modelo-alvo de 20B+ (na RAM) **verifica os k de uma vez em um único passe** —
que custa quase o mesmo que gerar 1 token, pois o custo é dominado pela leitura dos pesos (doc 01).
Com taxa de aceitação típica de 60–80%, multiplica-se o tok/s efetivo por ~1,5–2,5× **exatamente no
regime em que estamos: decode limitado por banda de memória**. A saída é *provadamente idêntica* à
do modelo-alvo (amostragem especulativa rejeita/corrige). No llama.cpp: `llama-speculative` /
`--draft-model`. Sinergia perfeita com a GPU de 4 GB: ela fica com o rascunho + atenção do alvo.

## 5. Síntese

| Técnica | Ganho | Requisito | Maturidade |
|---|---|---|---|
| MoE + offload seletivo de experts | 5–10× tok/s vs denso do mesmo tamanho | modelo MoE | ✅ produção (llama.cpp) |
| Cache LRU + prefetch de experts | 2–5× vs offload ingênuo | motor dedicado | 🔶 pesquisa/protótipos |
| Esparsidade de ativação (PowerInfer) | até 11× vs llama.cpp | modelo ReLU-like + preditor | 🔶 nicho |
| Decodificação especulativa | 1,5–2,5× | modelo-rascunho compatível | ✅ produção |
