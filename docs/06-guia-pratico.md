# 06 — Guia prático: receitas reproduzíveis para 4 GB de VRAM

Receitas completas, com flags explicados e desempenho esperado, para o hardware de referência
(CPU 4–6 núcleos, 16–32 GB RAM, GPU 4 GB, SSD). Use `scripts/estimar_memoria.py` para adaptar as
contas ao seu hardware exato.

## 0. Preparação do sistema (vale para todas as receitas)

```bash
# Compilar llama.cpp com o backend certo para GPU antiga:
git clone https://github.com/ggml-org/llama.cpp && cd llama.cpp
cmake -B build -DGGML_CUDA=ON      # NVIDIA (GTX 900+; para Kepler antigas, use Vulkan)
# cmake -B build -DGGML_VULKAN=ON  # AMD antigas, Intel, ou NVIDIA sem CUDA moderno
cmake --build build --config Release -j$(nproc)
```

Checklist de hardware que muda tudo (doc 01):
- [ ] **RAM em dual-channel** (2 pentes iguais em canais distintos) — ~2× a banda; verifique com
      `sudo dmidecode -t memory` ou `lshw -short -C memory`.
- [ ] Modelo armazenado em **SSD** (NVMe se possível); nunca depender de HD mecânico.
- [ ] Threads = núcleos *físicos* (`-t 4` num quad-core; SMT/hyperthreading geralmente atrapalha).
- [ ] Fechar navegador/electron durante a inferência (competem pela banda de RAM).

## 1. Receita principal — MoE ~20B interativo (gpt-oss-20b) ★

**Alvo**: 10–30 tok/s. **Requisitos**: 16 GB de RAM (justo) ou 24–32 GB (confortável).

```bash
./build/bin/llama-server \
  -m gpt-oss-20b-mxfp4.gguf \
  -ngl 99 \                       # "tudo na GPU"... exceto o que o -ot excluir:
  -ot "ffn_.*_exps=CPU" \         # experts (o grosso dos bytes) ficam na RAM, computados na CPU
  -fa on \                        # FlashAttention: menos VRAM e mais velocidade na atenção
  --cache-type-k q8_0 --cache-type-v q8_0 \  # KV quantizado: metade da VRAM de contexto
  -c 8192 \                       # contexto disciplinado (suba se sobrar VRAM)
  -t 4 --mlock                    # threads físicos; trava pesos na RAM
```

O que acontece: atenção + router + embeddings + normas (~2–3 GB) e o KV cache moram na VRAM; os
128 experts/camada moram na RAM via mmap; a cada token só 4 experts/camada (~2,3 GB efetivos) são
lidos — a banda da DDR4 sustenta 15–25 tok/s. A alternativa **Qwen3-30B-A3B-Instruct** (Q4_K_M,
~18 GB) usa a mesma linha de comando e rende 10–20 tok/s com 32 GB de RAM.

Se a VRAM estourar (OOM ao carregar): reduza `-c`, ou mova também a atenção das primeiras camadas
para a CPU: `-ot "blk\.[0-9]\.=CPU,ffn_.*_exps=CPU"`.

## 2. Receita — denso 20–24B utilizável (ex.: Mistral-Small-24B, Q4_K_M ~14 GB)

**Alvo**: 2–5 tok/s (leitura acompanhável). **Requisitos**: 24–32 GB RAM.

```bash
./build/bin/llama-cli -m mistral-small-24b-Q4_K_M.gguf \
  -ngl 99 -ot "ffn_.*=CPU" \      # FFN na RAM; atenção+KV na GPU
  -fa on --cache-type-k q8_0 --cache-type-v q8_0 -c 4096 -t 4
```

Denso não tem esparsidade a explorar: todos os ~14 GB são tocados por token → a banda da RAM é o
teto (doc 01, §3). Para subir de patamar, adicione decodificação especulativa (receita 4) ou troque
por IQ3_XXS (~9 GB → ~1,5× mais rápido, pequena perda de qualidade).

## 3. Receita — 70B em modo lote/offline (AirLLM)

**Alvo**: 0,5–2 tok/s; para tarefas sem exigência de latência. **Requisitos**: NVMe.

```python
from airllm import AutoModel
model = AutoModel.from_pretrained("unsloth/Meta-Llama-3.1-70B-Instruct",
                                  compression="4bit")   # camadas 4-bit: menos E/S por passada
out = model.generate("Explique a hipótese de Riemann em termos simples.", max_new_tokens=300)
```

Camada-a-camada do SSD (doc 03, regime D). Use para: avaliação noturna de um dataset, geração de
material em lote, destilação local. Não use para chat.

## 4. Receita — acelerador universal: decodificação especulativa

Soma-se às receitas 1–2. O rascunho mora **inteiro** na VRAM de 4 GB:

```bash
./build/bin/llama-speculative \
  -m  qwen3-32b-Q4_K_M.gguf   -ot "ffn_.*=CPU" -ngl 99 \   # alvo: pesado, FFN na RAM
  -md qwen3-0.6b-Q8_0.gguf    -ngld 99 \                    # rascunho: 100% na GPU
  --draft-max 8 --draft-min 1 -fa on -c 4096 -t 4
```

Regra de compatibilidade: alvo e rascunho da **mesma família/tokenizer**. Ganho esperado:
1,5–2,5× em texto normal; maior em código (rascunhos mais previsíveis → aceitação alta).

## 5. Receita — fine-tuning local de 20B (limítrofe; leia o doc 05 antes)

QLoRA + DeepSpeed ZeRO-3 com offload de otimizador/pesos para RAM+NVMe. Espere passos de treino
lentos (segundos–dezenas de segundos); dimensione o dataset de acordo (1–10 mil exemplos).

```yaml
# ds_config.json (essência)
zero_optimization:
  stage: 3
  offload_optimizer: { device: nvme, nvme_path: /mnt/nvme/ds_offload }
  offload_param:     { device: nvme, nvme_path: /mnt/nvme/ds_offload }
train_micro_batch_size_per_gpu: 1
gradient_accumulation_steps: 16
bf16: { enabled: true }
gradient_checkpointing: true
```

Com o modelo-base em NF4 (bitsandbytes `load_in_4bit=True`), LoRA r=8–16 só em `q_proj,v_proj`,
seq ≤1024. Rota alternativa recomendada: treinar o LoRA em nuvem por poucas horas e servir
localmente (`llama-export-lora` mescla o adaptador no GGUF).

## 6. Desempenho esperado — tabela de referência

| Receita | Modelo | RAM usada | VRAM usada | tok/s esperado |
|---|---|---|---|---|
| 1 | gpt-oss-20b MXFP4 | ~11 GB | ~3,5 GB | **10–30** |
| 1 | Qwen3-30B-A3B Q4_K_M | ~18 GB | ~3,5 GB | 10–20 |
| 2 | denso 24B Q4_K_M | ~14 GB | ~3 GB | 2–5 |
| 2+4 | denso 24B + rascunho 0.6B | ~14 GB | ~3,8 GB | 4–9 |
| 3 | 70B 4-bit via AirLLM | ~4 GB | ~3 GB | 0,5–2 |

## 7. Diagnóstico rápido

| Sintoma | Causa provável | Correção |
|---|---|---|
| OOM na GPU ao carregar | KV/contexto grande demais | ↓ `-c`; KV → q4_0; `-ot` mais agressivo |
| tok/s muito abaixo da tabela | RAM single-channel; threads errados; swap | dual-channel; `-t` = núcleos físicos; `--mlock` |
| 1º token demora minutos | leitura fria do SSD (mmap) | normal na 1ª execução; NVMe ajuda; execuções seguintes usam page cache |
| prefill lento com prompt longo | prefill na CPU | confirme `-ngl 99` (GPU acelera prefill mesmo com pesos na RAM, via lotes) |
| qualidade ruim | quantização abaixo de 3 bits sem imatrix | use Q4_K_M/IQ3+imatrix; confira template de chat |
