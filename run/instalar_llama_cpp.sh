#!/usr/bin/env bash
# Instala e compila o llama.cpp com o backend certo para a sua GPU.
# Detecta automaticamente: CUDA (NVIDIA) -> Vulkan (AMD/Intel/NVIDIA antiga) -> CPU puro.
# Uso: ./run/instalar_llama_cpp.sh [diretorio_destino]   (padrão: ./llama.cpp)
set -euo pipefail

DEST="${1:-llama.cpp}"

echo "==> Verificando dependências de compilação..."
for cmd in git cmake make g++; do
  command -v "$cmd" >/dev/null 2>&1 || {
    echo "ERRO: '$cmd' não encontrado. Instale com:" >&2
    echo "  Debian/Ubuntu: sudo apt install -y git cmake build-essential" >&2
    echo "  Fedora:        sudo dnf install -y git cmake gcc-c++ make" >&2
    exit 1
  }
done

# --- Detecção de backend -----------------------------------------------------
BACKEND="CPU"
CMAKE_FLAGS=""
if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1; then
  if command -v nvcc >/dev/null 2>&1; then
    BACKEND="CUDA"
    CMAKE_FLAGS="-DGGML_CUDA=ON"
  else
    echo "AVISO: GPU NVIDIA detectada mas o CUDA Toolkit (nvcc) não está instalado."
    echo "       Instale-o (sudo apt install nvidia-cuda-toolkit) para o backend CUDA,"
    echo "       ou prosseguiremos com Vulkan/CPU."
  fi
fi
if [ "$BACKEND" = "CPU" ] && command -v vulkaninfo >/dev/null 2>&1 && vulkaninfo --summary >/dev/null 2>&1; then
  BACKEND="Vulkan"
  CMAKE_FLAGS="-DGGML_VULKAN=ON"
fi
echo "==> Backend selecionado: $BACKEND"
[ "$BACKEND" = "CPU" ] && echo "    (sem GPU utilizável: tudo rodará na CPU — MoE ainda é viável, doc 01)"

# --- Clone + build -----------------------------------------------------------
if [ ! -d "$DEST/.git" ]; then
  echo "==> Clonando llama.cpp em $DEST..."
  git clone --depth 1 https://github.com/ggml-org/llama.cpp "$DEST"
else
  echo "==> $DEST já existe; atualizando..."
  git -C "$DEST" pull --ff-only || true
fi

echo "==> Compilando (isso demora alguns minutos)..."
cmake -S "$DEST" -B "$DEST/build" $CMAKE_FLAGS -DCMAKE_BUILD_TYPE=Release
cmake --build "$DEST/build" --config Release -j"$(nproc)" \
  --target llama-server llama-cli llama-bench llama-speculative

echo
echo "==> Pronto. Binários em $DEST/build/bin/"
echo "    Próximo passo: ./run/baixar_modelo.sh  e depois  ./scripts/rodar_moe_20b_4gb.sh"
