#!/usr/bin/env bash
# Receita 1 do doc 06: MoE ~20B interativo com 4 GB de VRAM (llama.cpp).
# Uso: ./rodar_moe_20b_4gb.sh caminho/para/modelo.gguf [contexto] [threads]
set -euo pipefail

MODELO="${1:?informe o caminho do .gguf (ex.: gpt-oss-20b-mxfp4.gguf)}"
CTX="${2:-8192}"
# threads = núcleos físicos (SMT costuma atrapalhar no decode limitado por banda)
THREADS="${3:-$(lscpu -p=Core,Socket 2>/dev/null | grep -v '^#' | sort -u | wc -l)}"
LLAMA_BIN="${LLAMA_BIN:-./llama.cpp/build/bin/llama-server}"

if [ ! -x "$LLAMA_BIN" ]; then
  echo "llama-server não encontrado em $LLAMA_BIN — compile o llama.cpp (doc 06 §0)" >&2
  echo "ou exporte LLAMA_BIN=/caminho/para/llama-server" >&2
  exit 1
fi

# Avisos de hardware que mudam tudo (doc 01):
if command -v dmidecode >/dev/null 2>&1 && [ "$(id -u)" = 0 ]; then
  CANAIS=$(dmidecode -t memory | grep -c "^\s*Locator:.*DIMM" || true)
  [ "$CANAIS" -lt 2 ] && echo "AVISO: possivelmente single-channel — dual-channel ~dobra o tok/s." >&2
fi

exec "$LLAMA_BIN" \
  -m "$MODELO" \
  -ngl 99 \
  -ot "ffn_.*_exps=CPU" \
  -fa on \
  --cache-type-k q8_0 \
  --cache-type-v q8_0 \
  -c "$CTX" \
  -t "$THREADS" \
  --mlock \
  --host 127.0.0.1 --port 8080
# Depois abra http://127.0.0.1:8080 no navegador (UI embutida do llama-server).
#
# Se der OOM de VRAM: reduza o contexto (arg 2) ou troque o -ot por:
#   -ot "blk\.[0-9]\.=CPU,ffn_.*_exps=CPU"   # empurra também as 10 primeiras camadas p/ CPU
# Se o modelo for denso (não-MoE): use -ot "ffn_.*=CPU" (espere 2-5 tok/s; doc 06 §2).
