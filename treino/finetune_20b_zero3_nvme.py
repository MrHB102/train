#!/usr/bin/env python3
"""LoRA de modelos 20B+ com 4 GB de VRAM — DeepSpeed ZeRO-3 + offload RAM/NVMe.

O caminho "limítrofe mas real" do doc 05 §3: os pesos-base (BF16) e os estados
do otimizador moram na RAM/NVMe (ZeRO-Infinity); a GPU recebe camada por camada
apenas durante a computação. Só os adaptadores LoRA acumulam gradiente.

Requisitos duros (leia o doc 05 antes de rodar):
  - 64 GB de RAM  OU  NVMe com ~90 GB livres (para um 20B em BF16);
  - deepspeed instalado (pip install deepspeed; exige libaio-dev);
  - paciência: segundos a dezenas de segundos POR PASSO. Dimensione o dataset
    (1-10 mil exemplos, 1-2 épocas = uma noite de treino).

Exemplo (gpt-oss-20b; para teste rápido use --modelo Qwen/Qwen3-1.7B):
  deepspeed treino/finetune_20b_zero3_nvme.py \
      --modelo openai/gpt-oss-20b --dataset meus_dados.jsonl \
      --nvme /mnt/nvme/ds_offload --saida ./lora20b_saida

Dica de sanidade: rode primeiro com --max-passos 3 para validar o pipeline
inteiro (download, offload, um passo de treino) antes do treino de verdade.
"""
import argparse
import json
import os
from pathlib import Path

import torch
from datasets import load_dataset
from peft import LoraConfig, get_peft_model
from transformers import (AutoModelForCausalLM, AutoTokenizer,
                          DataCollatorForLanguageModeling, Trainer,
                          TrainingArguments)

AQUI = Path(__file__).resolve().parent


def carregar_config_ds(nvme: str | None) -> dict:
    cfg = json.loads((AQUI / "ds_zero3_nvme.json").read_text())
    cfg.pop("_comentario", None)
    for chave in ("offload_param", "offload_optimizer"):
        of = cfg["zero_optimization"][chave]
        if nvme:
            of["device"], of["nvme_path"] = "nvme", nvme
        else:  # sem --nvme: offload para RAM (precisa ~64 GB p/ 20B)
            of["device"] = "cpu"
            of.pop("nvme_path", None)
            of.pop("buffer_count", None)
            of.pop("buffer_size", None)
    return cfg


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--modelo", default="openai/gpt-oss-20b")
    ap.add_argument("--dataset", required=True, help="arquivo .jsonl (campo 'text' ou instruction/output)")
    ap.add_argument("--saida", default="./lora20b_saida")
    ap.add_argument("--nvme", default=None,
                    help="diretório em NVMe p/ offload; omita para offload em RAM (64 GB+)")
    ap.add_argument("--seq", type=int, default=512, help="seq curta = menos ativação (doc 05)")
    ap.add_argument("--rank", type=int, default=8)
    ap.add_argument("--epocas", type=float, default=1.0)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--acum", type=int, default=16)
    ap.add_argument("--max-passos", type=int, default=-1, help="limite p/ teste de sanidade")
    ap.add_argument("--local_rank", type=int, default=-1)  # injetado pelo launcher deepspeed
    args = ap.parse_args()

    if args.nvme:
        os.makedirs(args.nvme, exist_ok=True)

    # IMPORTANTE: TrainingArguments com deepspeed=... deve existir ANTES do
    # from_pretrained — é isso que ativa o zero.Init e evita materializar os
    # 40 GB do modelo na RAM/GPU de uma vez.
    treino_args = TrainingArguments(
        output_dir=args.saida,
        deepspeed=carregar_config_ds(args.nvme),
        num_train_epochs=args.epocas,
        max_steps=args.max_passos,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=args.acum,
        gradient_checkpointing=True,
        learning_rate=args.lr,
        lr_scheduler_type="cosine", warmup_ratio=0.03,
        bf16=torch.cuda.is_available() and torch.cuda.is_bf16_supported(),
        logging_steps=1, save_strategy="no",  # salvamos o adaptador manualmente
        report_to=[],
    )

    tokenizer = AutoTokenizer.from_pretrained(args.modelo)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    modelo = AutoModelForCausalLM.from_pretrained(
        args.modelo, torch_dtype=torch.bfloat16, attn_implementation="sdpa")
    modelo.config.use_cache = False  # incompatível com checkpointing
    modelo.enable_input_require_grads()

    lora = LoraConfig(r=args.rank, lora_alpha=2 * args.rank, lora_dropout=0.05,
                      bias="none", task_type="CAUSAL_LM",
                      target_modules=["q_proj", "k_proj", "v_proj", "o_proj"])
    modelo = get_peft_model(modelo, lora)
    modelo.print_trainable_parameters()

    def formatar(ex):
        if ex.get("text"):
            return ex["text"]
        msgs = [{"role": "user", "content": ex.get("instruction", "")},
                {"role": "assistant", "content": ex.get("output", "")}]
        return tokenizer.apply_chat_template(msgs, tokenize=False)

    ds = load_dataset("json", data_files=args.dataset, split="train")
    ds = ds.map(lambda ex: tokenizer(formatar(ex), truncation=True,
                                     max_length=args.seq),
                remove_columns=ds.column_names)

    Trainer(model=modelo, args=treino_args, train_dataset=ds,
            data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False)
            ).train()

    modelo.save_pretrained(args.saida)   # só o adaptador (MBs) — pesos-base intactos
    tokenizer.save_pretrained(args.saida)
    print(f"\nAdaptador LoRA de {args.modelo} salvo em {args.saida}/")
    print("Sirva localmente: converta p/ GGUF e aplique no llama.cpp (doc 06 §5).")


if __name__ == "__main__":
    main()
