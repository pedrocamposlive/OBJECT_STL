#!/bin/bash
set -e

VENV=".venv"

echo ""
echo "=== Photo to STL Pipeline — Setup ==="
echo ""

# Detect platform
if [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORM="mac"
    echo "Plataforma : macOS"
    echo "Motor      : TripoSR (MPS / CPU)"
elif command -v nvidia-smi &> /dev/null; then
    PLATFORM="linux-cuda"
    GPU=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)
    echo "Plataforma : Linux + CUDA"
    echo "GPU        : $GPU"
    echo "Motores    : TripoSR + InstantMesh disponiveis"
else
    PLATFORM="linux-cpu"
    echo "Plataforma : Linux (sem GPU CUDA detectada)"
    echo "Motor      : TripoSR (CPU)"
fi

echo ""

# Create venv if needed
if [ ! -d "$VENV" ]; then
    python3 -m venv $VENV
    echo "Venv criado em .venv/"
else
    echo "Venv existente encontrado."
fi

PIP="$VENV/bin/pip"
echo ""

# PyTorch
echo "--- Instalando PyTorch ---"
if [[ "$PLATFORM" == "mac" ]]; then
    $PIP install --upgrade torch torchvision
elif [[ "$PLATFORM" == "linux-cuda" ]]; then
    $PIP install --upgrade torch torchvision --index-url https://download.pytorch.org/whl/cu124
else
    $PIP install --upgrade torch torchvision --index-url https://download.pytorch.org/whl/cpu
fi

# Base deps
echo ""
echo "--- Instalando dependencias base ---"
$PIP install --upgrade \
    "rembg" \
    onnxruntime \
    Pillow \
    trimesh \
    numpy \
    huggingface_hub \
    omegaconf==2.3.0 \
    einops==0.7.0 \
    transformers \
    scikit-image \
    imageio

# TripoSR (clone em vendor/ — nao tem setup.py)
# Nota: torchmcubes foi substituido por scikit-image (isosurface.py patchado)
#       chaves do checkpoint remapeadas em system.py para compatibilidade com transformers>=4.37
echo ""
echo "--- Clonando TripoSR ---"
if [ ! -d "vendor/TripoSR" ]; then
    git clone --depth 1 https://github.com/VAST-AI-Research/TripoSR.git vendor/TripoSR
    echo "TripoSR clonado em vendor/TripoSR/"
else
    echo "vendor/TripoSR ja existe, pulando clone."
fi

# Aplicar patches de compatibilidade
echo "Aplicando patches..."
cp patches/tsr/system.py          vendor/TripoSR/tsr/system.py
cp patches/tsr/models/isosurface.py vendor/TripoSR/tsr/models/isosurface.py
echo "Patches aplicados."

# InstantMesh (apenas Linux + CUDA)
if [[ "$PLATFORM" == "linux-cuda" ]]; then
    echo ""
    echo "--- Instalando InstantMesh (CUDA) ---"
    $PIP install diffusers accelerate xformers
fi

echo ""
echo "=== Setup concluido ==="
echo ""
echo "Para rodar:"
echo "  .venv/bin/python3 photo_to_stl_pipeline.py"
echo ""
