# Session Handoff — Photo to STL Pipeline

**Repo:** https://github.com/pedrocamposlive/OBJECT_STL  
**Branch:** `main`  
**Last commit:** `d6c1a5b`  
**Stack:** Python 3.13 · PyTorch · HuggingFace Transformers · Trimesh · macOS (Apple MPS) → Ubuntu + RTX 4090

---

## O que é este projeto

Pipeline que converte uma foto de produto em um arquivo `.stl` para impressão 3D (Bambu Lab A1).  
Fluxo: `INPUT/<foto>` → motor de reconstrução 3D → `OUTPUT/<nome>.stl` → Fusion 360 → Bambu Studio → impressora.

---

## Estado atual — o que funciona

```
.venv/bin/python3 photo_to_stl_pipeline.py
```

Mostra um menu com 3 motores:

| Opção | Motor | Plataforma | Status |
|---|---|---|---|
| 1 | TripoSR | Mac MPS / CPU / CUDA | Funciona, qualidade baixa |
| 2 | InstantMesh | CUDA apenas (Ubuntu + RTX 4090) | Implementado, não testado em CUDA |
| 3 | DepthAnything v2 | Mac MPS / CPU / CUDA | Funciona, qualidade mediana |

**Problema em aberto:** nenhum dos três motores gera STL com qualidade aceitável para impressão real.

- **TripoSR**: alucinação de geometria, resultado achatado com "ranhuras" na superfície. Objeto normalizado em ~1mm, precisa escalar 200× no Fusion 360.
- **DepthAnything v2**: melhor relevo (desvio Z 10× maior que TripoSR), mas é superfície aberta — só o lado visível na foto. Não é sólido fechado. Gera em 100×100×38 mm. Ainda não é printável diretamente.
- **InstantMesh**: arquitetura correta (Zero123++ multi-view → LRM reconstruction), mas só roda em CUDA. Não testado ainda no Ubuntu + RTX 4090.

---

## Estrutura de arquivos

```
GIT_OBJECT_STL/
├── photo_to_stl_pipeline.py     # entrypoint principal
├── setup.sh                     # instala venv + deps + clona vendors
├── engines/
│   ├── __init__.py              # registra ENGINES = {1: TripoSR, 2: InstantMesh, 3: Depth}
│   ├── triposr_engine.py        # TripoSR via vendor/TripoSR
│   ├── instantmesh_engine.py    # Zero123++ + InstantMesh LRM (CUDA)
│   └── depth_engine.py          # DepthAnything V2 Small (HuggingFace pipeline)
├── patches/
│   ├── tsr/system.py            # patch do TripoSR: remapeia keys do ViT + weights_only=True
│   └── tsr/models/isosurface.py # patch: substitui torchmcubes por scikit-image
├── INPUT/                       # coloque .jpg/.png/.webp aqui
├── OUTPUT/                      # STLs gerados
├── vendor/                      # gitignored — populado pelo setup.sh
│   ├── TripoSR/                 # clonado de VAST-AI-Research/TripoSR
│   └── InstantMesh/             # clonado de TencentARC/InstantMesh (só linux-cuda)
└── .venv/                       # gitignored — Python 3.13
```

---

## Como rodar do zero (Mac)

```bash
git clone git@github.com:pedrocamposlive/OBJECT_STL.git
cd OBJECT_STL
bash setup.sh
# coloque uma foto em INPUT/
.venv/bin/python3 photo_to_stl_pipeline.py
```

**Importante:** `setup.sh` espera Python 3.13 em `/opt/homebrew/bin/python3.13` (Homebrew).  
Python 3.14 não é compatível com vários pacotes ML (tokenizers, Pillow antigo, etc.).

---

## Como rodar no Ubuntu + RTX 4090

```bash
git clone git@github.com:pedrocamposlive/OBJECT_STL.git
cd OBJECT_STL
bash setup.sh   # detecta nvidia-smi, clona InstantMesh, instala xformers
.venv/bin/python3 photo_to_stl_pipeline.py   # escolher opção 2 (InstantMesh)
```

---

## Decisões técnicas e por quê

### Python 3.13, não 3.14
Python 3.14 quebra `tokenizers` (Rust extension), `Pillow 10.x` e outros pacotes de ML. Usar sempre 3.13.

### vendor/ + patches/ para TripoSR
TripoSR não tem `setup.py`, não é instalável via pip. Estratégia: clonar em `vendor/TripoSR/`, adicionar ao `sys.path`. Os patches são rastreados no git e aplicados pelo `setup.sh` depois do clone:

- **`patches/tsr/system.py`** — dois problemas corrigidos:
  1. `transformers >= 4.37` renomeou as chaves do ViT (`encoder.layer.N.attention.attention.query` → `layers.N.attention.q_proj`). A função `_remap_vit_keys()` faz o mapeamento no load.
  2. `torch.load()` agora exige `weights_only=True` para segurança.

- **`patches/tsr/models/isosurface.py`** — `torchmcubes` falha ao compilar no Python 3.13/3.14 (CMake/ninja/lipo issues). Substituído por `skimage.measure.marching_cubes`.

### TripoSR: RGBA → RGB antes do modelo
`rembg` retorna RGBA (fundo removido). O modelo ViT espera 3 canais. Solução: compositar o RGBA sobre fundo branco antes de passar ao modelo:
```python
background = Image.new("RGB", image_rgba.size, (255, 255, 255))
background.paste(image_rgba, mask=image_rgba.split()[3])
```

### extract_mesh com has_vertex_color=False
A API do TripoSR mudou — passar `has_vertex_color=True` quebra em versões novas. Usar sempre `False`.

---

## O problema fundamental que ainda não foi resolvido

Reconstrução 3D de foto única é um problema **matematicamente mal-posto** (ill-posed). A geometria oculta (lado de trás, laterais) precisa ser "alucinada" pelo modelo.

**Resultados obtidos com vent.png (ventilador):**

| Motor | Triângulos | Dimensões | Desvio Z | Impressionável? |
|---|---|---|---|---|
| TripoSR | 163K | ~1mm (normalizado) | 0.20 | Não |
| DepthAnything v2 | 465K | 100×100×38mm | 10.58 | Não (superfície aberta) |

---

## Próximo passo proposto (interrompido na sessão)

O usuário propôs uma abordagem completamente diferente:

> **Fornecer a URL de uma página de produto** (ex: Amazon, fabricante) onde o produto tem dimensões reais especificadas e múltiplas fotos (frente, lado, 3/4).

Ideia:
1. Scraping da página → extrai dimensões reais + múltiplas imagens do produto
2. Usa múltiplas vistas para reconstrução (em vez de foto única)
3. Escala o modelo com dimensões reais (ex: 215mm × 215mm × 260mm)
4. Opcionalmente: identifica o produto, busca modelo 3D existente em GrabCAD/Thingiverse

Este caminho tem muito mais chance de gerar resultado printável.

**O que estava sendo perguntado quando a sessão foi interrompida:** qual tipo de URL o usuário quer fornecer (página de produto completa vs link direto de imagem). O usuário respondeu: "qualquer URL — o sistema decide".

**Próxima ação concreta:** implementar `engines/web_product_engine.py` que:
1. Recebe uma URL
2. Detecta se é página de produto ou imagem direta
3. Se página: faz scraping de dimensões + imagens com `requests` + `BeautifulSoup`
4. Se imagem direta: baixa e processa com DepthAnything ou TripoSR
5. Se página com múltiplas vistas: passa para InstantMesh (quando em CUDA) ou TripoSR com melhor vista

---

## Dependências instaladas no .venv

```
torch torchvision          # PyTorch (MPS no Mac, cu124 no Linux)
transformers               # HuggingFace — DepthAnything, ViT
rembg onnxruntime          # remoção de fundo
Pillow trimesh numpy scipy # processamento de imagem e mesh
huggingface_hub            # download de modelos
omegaconf==2.3.0           # config do TripoSR e InstantMesh
einops==0.7.0              # operações de tensor
scikit-image               # marching cubes (substituto do torchmcubes)
imageio                    # I/O de imagens
diffusers accelerate       # Zero123++ (linux-cuda apenas)
xformers                   # atenção eficiente (linux-cuda apenas)
```

---

## Comandos úteis

```bash
# Rodar pipeline
.venv/bin/python3 photo_to_stl_pipeline.py

# Testar um motor específico diretamente
.venv/bin/python3 -c "
from pathlib import Path
from engines.depth_engine import DepthEngine
DepthEngine().reconstruct(Path('INPUT/vent.png'), Path('OUTPUT/test.stl'))
"

# Ver estatísticas de um STL
python3 -c "
import struct, numpy as np
with open('OUTPUT/vent_depth.stl','rb') as f:
    f.read(80); n=struct.unpack('<I',f.read(4))[0]
    v=[]
    for _ in range(n):
        f.read(12)
        for _ in range(3): v.append(struct.unpack('<3f',f.read(12)))
        f.read(2)
v=np.array(v)
print(f'tris={n:,}  X={v[:,0].ptp():.1f}mm  Y={v[:,1].ptp():.1f}mm  Z={v[:,2].ptp():.1f}mm  Zstd={v[:,2].std():.2f}')
"

# Push
git add -A && git commit -m 'mensagem' && git push origin main
```

---

## Hardware do usuário

- **Mac atual:** Apple Silicon (MPS disponível) — desenvolvimento e testes
- **PC em casa:** Ubuntu + RTX 4090 — produção, InstantMesh, modelos grandes
- **Impressora:** Bambu Lab A1
- **Workflow final:** STL → Fusion 360 (refinamento) → Bambu Studio (fatiamento) → impressão
