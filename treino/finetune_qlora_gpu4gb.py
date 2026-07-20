#!/usr/bin/env python3
"""QLoRA em GPU de 4 GB — o caminho que cabe inteiro na VRAM.

Ajusta modelos de até ~3-4B de parâmetros (limite honesto de 4 GB; ver doc 05
§3) com todas as técnicas de economia: base congelada em NF4 com dupla
quantização, LoRA de posto baixo, gradient checkpointing e Adam 8-bit paginado.
O adaptador resultante (~dezenas de MB) pode ser mesclado num GGUF e servido
pelo llama.cpp (doc 06 §5).

Dataset: arquivo JSONL com um campo "text" por linha, ou pares
"instruction"/"output" (formatados automaticamente).

Exemplo:
  python3 treino/finetune_qlora_gpu4gb.py \
      --modelo Qwen/Qwen3-1.7B --dataset meus_dados.jsonl --saida ./lora_saida
"""
import argparse
import json
import os

import torch
from datasets import load_dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import (AutoModelForCausalLM, AutoTokenizer,
                          BitsAndBytesConfig, DataCollatorForLanguageModeling,
                          Trainer, TrainingArguments)


def formatar(exemplo, tokenizer):
    if "text" in exemplo and exemplo["text"]:
        return exemplo["text"]
    # pares instrução/resposta -> template de chat do próprio modelo
    msgs = [{"role": "user", "content": exemplo.get("instruction", "")},
            {"role": "assistant", "content": exemplo.get("output", "")}]
    return tokenizer.apply_chat_template(msgs, tokenize=False)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--modelo", default="Qwen/Qwen3-1.7B",
                    help="modelo-base HF (≤4B para caber em 4 GB)")
    ap.add_argument("--dataset", required=True, help="arquivo .jsonl")
    ap.add_argument("--saida", default="./lora_saida")
    ap.add_argument("--seq", type=int, default=1024, help="comprimento máx. (↓ se OOM)")
    ap.add_argument("--rank", type=int, default=16, help="posto do LoRA")
    ap.add_argument("--epocas", type=float, default=2.0)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--acum", type=int, default=16, help="acumulação de gradiente")
    args = ap.parse_args()

    if not torch.cuda.is_available():
        raise SystemExit("QLoRA/bitsandbytes exige GPU CUDA. Sem GPU, use o "
                         "caminho ZeRO-3 (finetune_20b_zero3_nvme.py) ou treine na nuvem (doc 05).")

    tokenizer = AutoTokenizer.from_pretrained(args.modelo)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Base congelada em NF4 + dupla quantização (QLoRA, doc 05 §2.2)
    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16
        if torch.cuda.is_bf16_supported() else torch.float16,
    )
    modelo = AutoModelForCausalLM.from_pretrained(
        args.modelo, quantization_config=bnb, device_map={"": 0},
        attn_implementation="sdpa")
    modelo = prepare_model_for_kbit_training(modelo)  # checkpointing + casts

    lora = LoraConfig(
        r=args.rank, lora_alpha=2 * args.rank, lora_dropout=0.05,
        bias="none", task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"])
    modelo = get_peft_model(modelo, lora)
    modelo.print_trainable_parameters()

    ds = load_dataset("json", data_files=args.dataset, split="train")
    ds = ds.map(lambda ex: tokenizer(formatar(ex, tokenizer),
                                     truncation=True, max_length=args.seq),
                remove_columns=ds.column_names)

    treino_args = TrainingArguments(
        output_dir=args.saida,
        num_train_epochs=args.epocas,
        per_device_train_batch_size=1,          # 4 GB: microbatch 1, sempre
        gradient_accumulation_steps=args.acum,  # batch efetivo = acum
        gradient_checkpointing=True,            # doc 05 §2.3
        optim="paged_adamw_8bit",               # doc 05 §2.2/2.5
        learning_rate=args.lr,
        lr_scheduler_type="cosine", warmup_ratio=0.03,
        bf16=torch.cuda.is_bf16_supported(),
        fp16=not torch.cuda.is_bf16_supported(),
        logging_steps=10, save_strategy="epoch", report_to=[],
    )
    Trainer(model=modelo, args=treino_args, train_dataset=ds,
            data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False)
            ).train()

    modelo.save_pretrained(args.saida)
    tokenizer.save_pretrained(args.saida)
    print(f"\nAdaptador LoRA salvo em {args.saida}/")
    print("Para servir no llama.cpp: converta com convert_lora_to_gguf.py e "
          "mescle com llama-export-lora (doc 06 §5).")


if __name__ == "__main__":
    main()
