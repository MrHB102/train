#!/usr/bin/env bash
# Baixa um modelo 20B+ quantizado (GGUF) pronto para 4 GB de VRAM.
# Uso: ./run/baixar_modelo.sh [gpt-oss|qwen3-30b|mistral-24b] [diretorio]  (padrão: gpt-oss ./modelos)
set -euo pipefail

ESCOLHA="${1:-gpt-oss}"
DIR="${2:-modelos}"
mkdir -p "$DIR"

case "$ESCOLHA" in
  gpt-oss)      # MoE 21B totais / 3,6B ativos — a recomendação principal (10-30 tok/s)
    REPO="ggml-org/gpt-oss-20b-GGUF"
    ARQUIVO="gpt-oss-20b-mxfp4.gguf"          # ~12 GB
    ;;
  qwen3-30b)    # MoE 30B totais / 3,3B ativos — alternativa (precisa ~32 GB de RAM)
    REPO="unsloth/Qwen3-30B-A3B-Instruct-2507-GGUF"
    ARQUIVO="Qwen3-30B-A3B-Instruct-2507-Q4_K_M.gguf"   # ~18 GB
    ;;
  mistral-24b)  # denso 24B — controle/comparação (2-5 tok/s; doc 06 receita 2)
    REPO="bartowski/mistralai_Mistral-Small-3.2-24B-Instruct-2506-GGUF"
    ARQUIVO="mistralai_Mistral-Small-3.2-24B-Instruct-2506-Q4_K_M.gguf"  # ~14 GB
    ;;
  *)
    echo "Uso: $0 [gpt-oss|qwen3-30b|mistral-24b] [diretorio]" >&2; exit 1 ;;
esac

if [ -f "$DIR/$ARQUIVO" ]; then
  echo "==> $DIR/$ARQUIVO já existe; nada a fazer."; exit 0
fi

echo "==> Baixando $ARQUIVO de $REPO (arquivo grande; retomável se cair)..."

# Preferência: CLI do Hugging Face (retoma downloads); fallback: curl direto.
if command -v hf >/dev/null 2>&1; then
  hf download "$REPO" "$ARQUIVO" --local-dir "$DIR"
elif command -v huggingface-cli >/dev/null 2>&1; then
  huggingface-cli download "$REPO" "$ARQUIVO" --local-dir "$DIR"
elif command -v pip3 >/dev/null 2>&1 && pip3 install -q -U "huggingface_hub[cli]" 2>/dev/null \
     && command -v huggingface-cli >/dev/null 2>&1; then
  huggingface-cli download "$REPO" "$ARQUIVO" --local-dir "$DIR"
else
  curl -L --fail --retry 5 --retry-delay 5 -C - \
    -o "$DIR/$ARQUIVO" \
    "https://huggingface.co/$REPO/resolve/main/$ARQUIVO"
fi

echo
echo "==> Modelo em $DIR/$ARQUIVO"
echo "    Executar: ./scripts/rodar_moe_20b_4gb.sh $DIR/$ARQUIVO"
