#!/usr/bin/env python3
"""Estimador de memória e velocidade para LLMs em hardware limitado.

Dado um modelo (total/ativos, quantização) e um hardware (VRAM, RAM e suas
bandas), estima:
  - tamanho dos pesos e do KV cache;
  - se/como o modelo cabe na hierarquia VRAM->RAM->SSD;
  - tok/s teórico no decode (modelo do doc 01: banda / bytes ativos por token).

Uso:
  python3 estimar_memoria.py --params 21e9 --ativos 3.6e9 --quant mxfp4 \
      --vram 4 --ram 32 --banda-ram 40 --camadas 24 --kv-heads 8 --head-dim 64 \
      --contexto 8192

  python3 estimar_memoria.py --preset gpt-oss-20b --vram 4 --ram 32 --banda-ram 40
"""
import argparse
import sys

# bits efetivos por peso (inclui overhead de escalas/blocos)
QUANTS = {
    "fp16": 16.0, "q8_0": 8.5, "q6_k": 6.6, "q5_k_m": 5.7, "q4_k_m": 4.8,
    "mxfp4": 4.25, "nf4": 4.5, "iq3_xxs": 3.1, "q3_k_m": 3.9, "iq2_xxs": 2.06,
    "iq1_s": 1.56, "bitnet": 1.58,
}

PRESETS = {
    # nome: (params_totais, params_ativos, quant, camadas, kv_heads, head_dim)
    "gpt-oss-20b":    (20.9e9, 3.6e9, "mxfp4", 24, 8, 64),
    "qwen3-30b-a3b":  (30.5e9, 3.3e9, "q4_k_m", 48, 4, 128),
    "mistral-24b":    (23.6e9, 23.6e9, "q4_k_m", 40, 8, 128),
    "llama3-70b":     (70.6e9, 70.6e9, "iq2_xxs", 80, 8, 128),
    "mixtral-8x7b":   (46.7e9, 12.9e9, "q4_k_m", 32, 8, 128),
}

GB = 1024**3


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--preset", choices=PRESETS)
    ap.add_argument("--params", type=float, help="parâmetros totais (ex.: 21e9)")
    ap.add_argument("--ativos", type=float, help="parâmetros ativos/token (= totais se denso)")
    ap.add_argument("--quant", choices=QUANTS, default="q4_k_m")
    ap.add_argument("--camadas", type=int, default=40)
    ap.add_argument("--kv-heads", type=int, default=8)
    ap.add_argument("--head-dim", type=int, default=128)
    ap.add_argument("--contexto", type=int, default=8192)
    ap.add_argument("--kv-bits", type=float, default=8.5, help="bits do KV (16=fp16, 8.5=q8_0, 4.5=q4_0)")
    ap.add_argument("--vram", type=float, default=4.0, help="GB de VRAM")
    ap.add_argument("--ram", type=float, default=32.0, help="GB de RAM")
    ap.add_argument("--banda-ram", type=float, default=40.0, help="GB/s da RAM (DDR4 dual ~40, DDR3 dual ~20, single-channel: metade)")
    ap.add_argument("--banda-ssd", type=float, default=3.0, help="GB/s do SSD (NVMe ~3-7, SATA ~0.5)")
    args = ap.parse_args()

    if args.preset:
        p, a, q, cam, kvh, hd = PRESETS[args.preset]
        args.params = args.params or p
        args.ativos = args.ativos or a
        args.quant = q if "--quant" not in " ".join(sys.argv) else args.quant
        args.camadas, args.kv_heads, args.head_dim = cam, kvh, hd
    if not args.params:
        ap.error("informe --preset ou --params/--ativos")
    args.ativos = args.ativos or args.params

    bits = QUANTS[args.quant]
    pesos_gb = args.params * bits / 8 / GB
    ativos_gb = args.ativos * bits / 8 / GB

    # KV: 2 (K e V) x camadas x kv_heads x head_dim x bytes x contexto
    kv_por_token = 2 * args.camadas * args.kv_heads * args.head_dim * (args.kv_bits / 8)
    kv_gb = kv_por_token * args.contexto / GB

    buffers_gb = 0.8  # workspace típico do llama.cpp com FlashAttention
    # fração não-expert (atenção/embeds/normas) ~ proporcional aos ativos num MoE
    nao_expert_gb = min(pesos_gb, ativos_gb * 0.6)
    vram_necessaria = nao_expert_gb + kv_gb + buffers_gb

    print(f"Modelo: {args.params/1e9:.1f}B totais / {args.ativos/1e9:.1f}B ativos  "
          f"[{args.quant}, {bits} bits/peso]")
    print(f"  Pesos totais:        {pesos_gb:6.1f} GB")
    print(f"  Bytes ativos/token:  {ativos_gb:6.2f} GB")
    print(f"  KV cache ({args.contexto} tok): {kv_gb:6.2f} GB")
    print()
    print(f"Plano de alocação (VRAM {args.vram} GB / RAM {args.ram} GB):")
    if pesos_gb + kv_gb + buffers_gb <= args.vram:
        print("  ✅ Tudo na VRAM (raro nesta classe!)")
        banda = 120.0
    elif vram_necessaria <= args.vram and pesos_gb - nao_expert_gb <= args.ram * 0.85:
        print(f"  ✅ Split recomendado: atenção+KV+buffers na VRAM ({vram_necessaria:.1f} GB), "
              f"FFN/experts na RAM ({pesos_gb - nao_expert_gb:.1f} GB)")
        print("     llama.cpp: -ngl 99 -ot 'ffn_.*_exps=CPU' (MoE) ou -ot 'ffn_.*=CPU' (denso)")
        banda = args.banda_ram
    elif pesos_gb <= (args.ram + args.vram) * 0.9:
        print(f"  ⚠️  Cabe apertado em RAM+VRAM; reduza contexto/quantização se houver OOM")
        banda = args.banda_ram
    else:
        excesso = pesos_gb - args.ram * 0.85
        print(f"  🐢 Não cabe na RAM: ~{excesso:.1f} GB transbordam para o SSD (mmap/AirLLM)")
        frac_ssd = excesso / pesos_gb
        banda = 1 / ((1 - frac_ssd) / args.banda_ram + frac_ssd / args.banda_ssd)
    toks = banda / ativos_gb
    print()
    print(f"Velocidade teórica de decode: ~{toks:.1f} tok/s "
          f"(banda efetiva {banda:.0f} GB/s ÷ {ativos_gb:.2f} GB ativos/token)")
    print("Na prática espere 50–80% do teórico; especulação (doc 04 §4) pode dar 1,5–2,5×.")


if __name__ == "__main__":
    main()
