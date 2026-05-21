import sys
from pathlib import Path

SCRIPT_DIR      = Path(__file__).parent.parent
INSTANTMESH_DIR = SCRIPT_DIR / "vendor" / "InstantMesh"

# Camera parameters for Zero123++ 6-view grid (azimuth, elevation in degrees)
# Row-major: top-left → top-right → mid-left → mid-right → bot-left → bot-right
_ZERO123PP_AZIMUTHS   = [30, 90, 150, 210, 270, 330]
_ZERO123PP_ELEVATIONS = [20, -10, 20, -10, 20, -10]


def _add_instantmesh_to_path():
    if not INSTANTMESH_DIR.exists():
        print(f"\nvendor/InstantMesh nao encontrado.")
        print("Execute: bash setup.sh  (em maquina com GPU CUDA)")
        sys.exit(1)
    p = str(INSTANTMESH_DIR)
    if p not in sys.path:
        sys.path.insert(0, p)


def _detect_device():
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
        if torch.backends.mps.is_available():
            return "mps"
    except ImportError:
        pass
    return "cpu"


class InstantMeshEngine:
    name = "InstantMesh"
    description = "alta qualidade, CUDA RTX — recomendado: Ubuntu + RTX 4090"

    def __init__(self):
        self.device = _detect_device()

    def device_label(self):
        labels = {"cuda": "CUDA GPU", "mps": "Apple MPS", "cpu": "CPU"}
        return labels.get(self.device, self.device)

    def check_dependencies(self):
        if self.device != "cuda":
            print("\nInstantMesh requer uma GPU NVIDIA com CUDA.")
            print(f"Dispositivo detectado: {self.device_label()}")
            print("Use TripoSR (opcao 1) ou DepthAnything v2 (opcao 3) no Mac.")
            sys.exit(1)

        _add_instantmesh_to_path()

        missing = []
        for pkg in ("torch", "diffusers", "transformers", "rembg", "PIL",
                    "omegaconf", "einops", "trimesh", "numpy"):
            try:
                __import__(pkg if pkg != "PIL" else "PIL.Image")
            except ImportError:
                missing.append(pkg)
        if missing:
            print(f"\nDependencias ausentes: {', '.join(missing)}")
            print("Execute: bash setup.sh")
            sys.exit(1)

    def reconstruct(self, image_path: Path, output_path: Path) -> Path:
        self.check_dependencies()

        import torch
        import numpy as np
        import rembg
        import trimesh
        from PIL import Image
        from diffusers import DiffusionPipeline, EulerAncestralDiscreteScheduler
        from omegaconf import OmegaConf
        from huggingface_hub import hf_hub_download

        dtype = torch.float16

        # ── Step 1: remove background ──────────────────────────────────────
        print(f"      -> Dispositivo: {self.device_label()}")
        print(f"      -> Removendo fundo...")
        image = Image.open(image_path).convert("RGB")
        rembg_session = rembg.new_session()
        image_rgba = rembg.remove(image, session=rembg_session)

        # Composite on white, resize to 320 for Zero123++
        bg = Image.new("RGB", image_rgba.size, (255, 255, 255))
        bg.paste(image_rgba, mask=image_rgba.split()[3])
        image_input = bg.resize((320, 320), Image.LANCZOS)

        # ── Step 2: multi-view synthesis with Zero123++ ────────────────────
        print(f"      -> Carregando Zero123++ (primeira vez ~3 GB)...")
        mv_pipe = DiffusionPipeline.from_pretrained(
            "sudo-ai/zero123plus-v1.2",
            custom_pipeline="zero123plus",
            torch_dtype=dtype,
        )
        mv_pipe.scheduler = EulerAncestralDiscreteScheduler.from_config(
            mv_pipe.scheduler.config,
            timestep_spacing="trailing",
        )
        mv_pipe.to(self.device)

        print(f"      -> Gerando 6 vistas com Zero123++ (75 steps)...")
        with torch.no_grad():
            mv_result = mv_pipe(image_input, num_inference_steps=75)
        mv_grid = mv_result.images[0]   # 960×640 (3 rows × 2 cols of 320×320)

        del mv_pipe
        torch.cuda.empty_cache()

        # ── Step 3: parse 6-view grid ──────────────────────────────────────
        mv_np = np.array(mv_grid)
        h, w  = mv_np.shape[:2]
        th, tw = h // 3, w // 2
        views = [
            Image.fromarray(mv_np[r * th:(r + 1) * th, c * tw:(c + 1) * tw])
            for r in range(3) for c in range(2)
        ]

        # ── Step 4: load InstantMesh reconstruction model ──────────────────
        print(f"      -> Carregando InstantMesh LRM (~2 GB)...")
        ckpt_path = hf_hub_download(
            repo_id="TencentARC/InstantMesh",
            filename="instant_mesh_large.ckpt",
        )
        config_path = INSTANTMESH_DIR / "configs" / "instant-mesh-large.yaml"
        config      = OmegaConf.load(config_path)

        from src.models.lrm_mesh import InstantMesh as LRM
        model = LRM(**config.model_config)
        state = torch.load(ckpt_path, map_location="cpu", weights_only=False)
        model.load_state_dict(state["state_dict"], strict=True)
        model = model.to(self.device, dtype=dtype)
        model.eval()

        # ── Step 5: build view tensors + camera embeddings ─────────────────
        from torchvision import transforms as T
        from einops import rearrange

        to_tensor = T.Compose([
            T.Resize((320, 320)),
            T.ToTensor(),
            T.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5]),
        ])
        views_t = torch.stack([to_tensor(v) for v in views])   # [6, 3, H, W]
        views_t = views_t.unsqueeze(0).to(self.device, dtype=dtype)  # [1, 6, 3, H, W]

        # Camera parameters expected by InstantMesh
        import math
        azimuths_rad   = [math.radians(a) for a in _ZERO123PP_AZIMUTHS]
        elevations_rad = [math.radians(e) for e in _ZERO123PP_ELEVATIONS]

        def _build_camera_embed(azimuths, elevations, radius=4.0):
            cameras = []
            for az, el in zip(azimuths, elevations):
                x = radius * math.cos(el) * math.sin(az)
                y = radius * math.sin(el)
                z = radius * math.cos(el) * math.cos(az)
                cameras.append([x, y, z])
            return torch.tensor(cameras, dtype=dtype).unsqueeze(0).to(self.device)

        camera_embeds = _build_camera_embed(azimuths_rad, elevations_rad)

        # ── Step 6: extract mesh ───────────────────────────────────────────
        print(f"      -> Reconstruindo mesh 3D (res=256)...")
        with torch.no_grad():
            mesh_v, mesh_f, _ = model.extract_mesh(
                views_t, camera_embeds, resolution=256
            )

        mesh = trimesh.Trimesh(
            vertices=mesh_v.cpu().float().numpy(),
            faces=mesh_f.cpu().numpy(),
        )
        output_path.parent.mkdir(exist_ok=True)
        mesh.export(str(output_path))
        return output_path
