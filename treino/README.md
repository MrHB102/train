# Treinamento com 4 GB de VRAM — como usar estes arquivos

Fundamentação completa no [doc 05](../docs/05-treinamento-e-finetuning-4gb.md). Resumo operacional:

## Preparação (uma vez)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r treino/requirements.txt
# só para o caminho 20B+: sudo apt install libaio-dev && pip install deepspeed
```

Formato do dataset (`meus_dados.jsonl`, uma linha por exemplo):

```json
{"instruction": "Explique fotossíntese em uma frase.", "output": "É o processo..."}
{"text": "Texto livre também é aceito neste campo."}
```

## Caminho A — QLoRA que cabe na GPU (modelos ≤ ~4B) ✅ recomendado para começar

```bash
python3 treino/finetune_qlora_gpu4gb.py \
    --modelo Qwen/Qwen3-1.7B --dataset meus_dados.jsonl --saida ./lora_saida
```

Minutos a poucas horas. Se der OOM: `--seq 512 --rank 8`.

## Caminho B — LoRA de 20B+ com offload RAM/NVMe 🔶 limítrofe, mas real

```bash
# teste de sanidade primeiro (3 passos, valida o pipeline inteiro):
deepspeed treino/finetune_20b_zero3_nvme.py \
    --modelo openai/gpt-oss-20b --dataset meus_dados.jsonl \
    --nvme /mnt/nvme/ds_offload --max-passos 3

# treino de verdade (uma noite p/ 1-2 mil passos):
deepspeed treino/finetune_20b_zero3_nvme.py \
    --modelo openai/gpt-oss-20b --dataset meus_dados.jsonl \
    --nvme /mnt/nvme/ds_offload --saida ./lora20b_saida
```

Com 64 GB de RAM, omita `--nvme` (offload para RAM; bem mais rápido). Requisitos e expectativas
honestas de velocidade: doc 05 §3.

## Caminho C — treinar na nuvem, rodar local (a rota pragmática)

Algumas horas de uma GPU alugada treinam o QLoRA do 20B; o adaptador resultante tem só dezenas de
MB. Os mesmos scripts acima funcionam sem alteração na máquina alugada (sem `--nvme`, com
`--seq 2048`).

## Servir o resultado no llama.cpp (todos os caminhos)

```bash
python3 llama.cpp/convert_lora_to_gguf.py ./lora_saida --outfile lora.gguf
./llama.cpp/build/bin/llama-export-lora -m modelo_base.gguf --lora lora.gguf -o modelo_ajustado.gguf
./scripts/rodar_moe_20b_4gb.sh modelo_ajustado.gguf   # e converse via run/chat_cliente.py
```
