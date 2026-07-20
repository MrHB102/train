# LLMs de 20B+ parâmetros em hardware antigo com ≤4 GB de VRAM

**Projeto de pesquisa aplicada**: como executar (e até ajustar) modelos de linguagem com mais de
20 bilhões de parâmetros em um computador local antigo, com no máximo **4 GB de VRAM** — algo que
o senso comum diz ser impossível.

A tese central desta pesquisa: **"não cabe na VRAM" não significa "não roda"**. A VRAM é apenas o
nível mais rápido de uma hierarquia de memória (VRAM → RAM → SSD). O que determina a velocidade de
geração de um LLM não é onde os pesos *moram*, e sim **quantos bytes precisam ser tocados por token
gerado** e **a largura de banda do canal que os transporta**. Toda a engenharia deste projeto gira
em torno de reduzir esses dois números.

## Resultado-resumo (o que é realmente possível)

| Cenário | Hardware alvo | Velocidade esperada | Técnica principal |
|---|---|---|---|
| **MoE 20–30B (gpt-oss-20b, Qwen3-30B-A3B)** | CPU 4+ núcleos, 16–32 GB RAM, GPU 4 GB | **10–30 tok/s** ✅ uso interativo | MoE (só ~3–3,6B ativos/token) + offload de experts para RAM |
| Denso 20B (ex.: Mistral-Small quantizado) | 32 GB RAM DDR4 dual-channel, GPU 4 GB | 2–5 tok/s ⚠️ utilizável | Quantização Q3/Q4 + offload parcial de camadas |
| Denso 70B | 16 GB RAM + SSD NVMe, GPU 4 GB | 0,5–2 tok/s 🐢 batch/offline | AirLLM / inferência camada-a-camada do SSD |
| Fine-tuning de 20B+ | GPU 4 GB + 64 GB RAM | horas–dias por época | QLoRA + ZeRO-Offload (limítrofe; ver doc 05) |

## Estrutura do repositório

- [`docs/01-fundamentos-e-limites.md`](docs/01-fundamentos-e-limites.md) — a aritmética de memória e
  largura de banda: por que dizem que é impossível e onde exatamente o argumento falha.
- [`docs/02-quantizacao.md`](docs/02-quantizacao.md) — de FP16 a 1,58 bits: k-quants, i-quants com
  matriz de importância, MXFP4 e BitNet ternário.
- [`docs/03-offloading-e-hierarquia-de-memoria.md`](docs/03-offloading-e-hierarquia-de-memoria.md) —
  llama.cpp, FlexGen, AirLLM e "LLM in a flash": usar RAM e SSD como extensão da VRAM.
- [`docs/04-esparsidade-e-moe.md`](docs/04-esparsidade-e-moe.md) — a técnica mais importante de
  todas: esparsidade de ativação (PowerInfer) e Mixture-of-Experts (KTransformers, offload de
  experts), que tornam 20B+ *interativo* em hardware fraco.
- [`docs/05-treinamento-e-finetuning-4gb.md`](docs/05-treinamento-e-finetuning-4gb.md) — QLoRA,
  gradient checkpointing, otimizadores paginados e ZeRO-Offload: o que dá e o que não dá para
  treinar com 4 GB de VRAM.
- [`docs/06-guia-pratico.md`](docs/06-guia-pratico.md) — receitas prontas e reproduzíveis
  (comandos llama.cpp completos, flags, números esperados) para o hardware-alvo.
- [`docs/07-proposta-de-pesquisa-original.md`](docs/07-proposta-de-pesquisa-original.md) — **o
  núcleo do projeto**: a proposta de pesquisa nova ("TÉRMITA") — residência térmica de experts em
  três camadas com precisão mista, especulação hierárquica com rascunho gratuito em MoE, e
  "StreamLoRA" para fine-tuning de 20B+ por streaming — com hipóteses falsificáveis (H1–H4) e
  plano experimental para hardware antigo.
- [`scripts/estimar_memoria.py`](scripts/estimar_memoria.py) — calculadora: dado um modelo e uma
  quantização, estima VRAM/RAM necessárias e tok/s teórico do seu hardware.
- [`scripts/rodar_moe_20b_4gb.sh`](scripts/rodar_moe_20b_4gb.sh) — script pronto para rodar
  gpt-oss-20b / Qwen3-30B-A3B com 4 GB de VRAM via llama.cpp.
- [`REFERENCIAS.md`](REFERENCIAS.md) — bibliografia completa (papers arXiv, sistemas, benchmarks).

## Hardware de referência assumido nesta pesquisa

Um "computador antigo" típico de 2015–2019:

- CPU: 4–6 núcleos (ex.: i5-8400, Ryzen 5 2600, ou até i7-4790)
- RAM: 16–32 GB DDR3/DDR4 (dual-channel: **importa muito**, ver doc 01)
- GPU: 4 GB VRAM (ex.: GTX 1050 Ti, GTX 970, RX 570 4GB)
- Armazenamento: SSD SATA ou NVMe (HD mecânico inviabiliza os cenários de offload pesado)

## Execução de ponta a ponta (arquivos prontos)

```bash
# 1. Instalar o motor (detecta CUDA/Vulkan/CPU automaticamente e compila):
./run/instalar_llama_cpp.sh

# 2. Baixar um modelo 20B+ pronto para 4 GB de VRAM (~12 GB de download):
./run/baixar_modelo.sh gpt-oss          # ou: qwen3-30b | mistral-24b

# 3. Executar (atenção+KV na GPU, experts na RAM — a receita-chave):
./scripts/rodar_moe_20b_4gb.sh modelos/gpt-oss-20b-mxfp4.gguf

# 4. Conversar (em outro terminal; mostra o tok/s real do seu hardware):
python3 run/chat_cliente.py
```

A explicação de cada flag — e o desempenho esperado — está no
[guia prático](docs/06-guia-pratico.md).

## Treinamento (fine-tuning) com 4 GB de VRAM

Dois caminhos executáveis em [`treino/`](treino/README.md): **(A)** QLoRA que cabe inteiro na GPU
(modelos ≤4B, `treino/finetune_qlora_gpu4gb.py`) e **(B)** LoRA de 20B+ com DeepSpeed ZeRO-3 e
offload para RAM/NVMe (`treino/finetune_20b_zero3_nvme.py` + `treino/ds_zero3_nvme.json`) —
limítrofe porém real: uma noite de treino para 1–2 mil passos. O adaptador resultante (MBs) é
mesclado no GGUF e servido pelo mesmo pipeline de execução acima. Detalhes e limites honestos no
[doc 05](docs/05-treinamento-e-finetuning-4gb.md).
