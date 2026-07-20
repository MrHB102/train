# 05 — Treinamento e fine-tuning de 20B+ com 4 GB de VRAM

Treinar é muito mais caro em memória do que inferir. Este documento faz a conta honesta, mapeia as
técnicas que derrubam cada termo dela, e conclui o que é realista com 4 GB — incluindo a rota
proposta por esta pesquisa para fine-tuning de 20B+ em hardware antigo.

## 1. A aritmética do treinamento (por que é 8–10× pior que inferência)

Fine-tuning completo de um 20B em precisão mista com Adam:

| Componente | Bytes/parâmetro | Total (20B) |
|---|---|---|
| Pesos (BF16) | 2 | 40 GB |
| Gradientes (BF16) | 2 | 40 GB |
| Estados do Adam (m, v em FP32) | 8 | 160 GB |
| Cópia mestre FP32 dos pesos | 4 | 80 GB |
| Ativações (seq 2K, batch 1, sem checkpointing) | — | dezenas de GB |
| **Total** | **~16+** | **≳320 GB** |

Contra 4 GB de VRAM: fator ~80× de déficit. Fine-tuning completo está descartado; a pesquisa
inteira em "treino barato" consiste em atacar cada linha da tabela.

## 2. As técnicas, linha por linha

### 2.1 PEFT/LoRA — elimina gradientes e otimizador dos pesos-base
Congela o modelo; treina só adaptadores de baixo posto A·B (posto 8–64) nas projeções. Parâmetros
treináveis caem para ~0,1–1% → gradientes + Adam passam de 280 GB para **<1 GB**. Restam os pesos
congelados (40 GB em BF16 → problema seguinte) e as ativações.

### 2.2 QLoRA — comprime os pesos congelados
QLoRA (Dettmers et al., 2023) congela a base quantizada em **NF4** (4 bits, informação-teórico
ótimo para pesos ~normais) com **dupla quantização** (quantiza as próprias constantes de
quantização) e retropropaga através dela para os adaptadores LoRA em BF16. Os 40 GB viram ~11 GB.
Adiciona **otimizadores paginados** (estados do Adam em memória unificada, paginados
VRAM↔RAM sob pressão) — precursor direto da nossa estratégia de offload. Resultado do paper:
65B ajustado em uma GPU de 48 GB sem perda vs. 16 bits. Para 20B: **~12–14 GB de VRAM** com
checkpointing — ainda 3× nosso limite. Precisamos dos itens seguintes.

### 2.3 Gradient checkpointing — troca ativações por recomputação
Guarda ativações só nas fronteiras de camadas; recomputa o resto no backward. Memória de ativações
cai de O(n_camadas) para O(√n_camadas) ao custo de ~30% mais computação. Unsloth soma kernels
fundidos (Triton) e checkpointing seletivo: ~2× mais rápido e até 70% menos VRAM que o baseline HF.

### 2.4 ZeRO-Offload / ZeRO-3 + NVMe — o otimizador mora na RAM/SSD
DeepSpeed particiona e despeja estados de otimizador (ZeRO-2/Offload) e até os próprios pesos
(ZeRO-3/Infinity, com estágio em NVMe) para fora da GPU; o passo do Adam roda **na CPU**. O passo
de otimização deixa de consumir VRAM; o custo é banda PCIe/RAM por passo — aceitável porque o passo
do otimizador é raro em relação aos microbatches com acumulação de gradiente.

### 2.5 Alternativas ao Adam que encolhem os estados
- **8-bit Adam (bitsandbytes)**: estados m,v em 8 bits → 4× menos.
- **GaLore**: projeta gradientes em subespaço de baixo posto antes do Adam → estados de otimizador
  de posto r; permitiu *pré-treinar* 7B em uma RTX 4090 (24 GB). Composição GaLore+offload é
  território pouco explorado (oportunidade de pesquisa).
- **Adafactor / SGD com momento**: menos estado, convergência mais delicada em LLMs.

### 2.6 Treino camada-a-camada em streaming (fronteira aberta)
O análogo de treino do AirLLM: manter uma janela de camadas na GPU, com pesos-base NF4 vindos do
SSD/RAM sob demanda. O backward exige as camadas em ordem reversa (duas varreduras de E/S por
passo) e os adaptadores LoRA — minúsculos — ficam residentes. Nenhum framework maduro faz isso
hoje de ponta a ponta; é o núcleo da proposta T1 do doc 07 ("StreamLoRA").

## 3. O que é realista com 4 GB de VRAM (avaliação honesta)

| Alvo | Viável? | Como |
|---|---|---|
| QLoRA de 1–4B | ✅ confortável | Unsloth/HF padrão, batch 1 + acumulação |
| QLoRA de 7–8B | ⚠️ limítrofe | seq curta (512–1024), checkpointing, 8-bit Adam, posto baixo |
| QLoRA de 20B+ inteiro na GPU | ❌ (~12–14 GB) | — |
| **LoRA de 20B+ híbrido GPU+RAM+SSD** | 🔶 possível, lento (horas–dias/época) | ZeRO-3+NVMe offload ou StreamLoRA (doc 07); exige 64 GB RAM ou NVMe rápido |
| **LoRA só nos experts ativos de um MoE** | 🔶 promissor, pouco explorado | proposta T2 do doc 07 |
| Pré-treinamento de 20B | ❌ em qualquer variante local | — |

Duas rotas pragmáticas que esta pesquisa endossa:

1. **Rota híbrida local**: treinar QLoRA de um 20B com DeepSpeed ZeRO-3 + offload NVMe *é*
   tecnicamente possível em 4 GB de VRAM + 64 GB de RAM — a throughput (segundos por passo) é o
   preço. Para datasets de instrução pequenos (1–10 mil exemplos, 1–3 épocas), "uma noite de
   treino" é aceitável.
2. **Rota assimétrica**: ajustar na nuvem por algumas horas (QLoRA de 20B em uma única GPU alugada
   custa pouco) e **inferir localmente para sempre** com as técnicas dos docs 02–04. Os artefatos
   LoRA são portáteis (MB, não GB) e o llama.cpp aplica/mescla adaptadores em GGUF.

## 4. Nota sobre "treinar do zero em hardware antigo"

Pré-treinar 20B exige ~10²²–10²³ FLOPs — décadas em uma CPU/GPU antiga; nenhuma engenharia de
memória contorna FLOPs. A resposta científica correta não é força bruta, e sim mudar o objetivo:
(a) fine-tuning eficiente (acima), (b) destilação de modelos grandes para pequenos, e (c) a aposta
BitNet: modelos ternários treinados nativamente, cuja *inferência* de 20B caberia integralmente
nos 4 GB de VRAM (doc 02, §2.5).
