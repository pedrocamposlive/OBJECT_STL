import sys
from pathlib import Path

SCRIPT_DIR  = Path(__file__).parent.parent
TRIPOSR_DIR = SCRIPT_DIR / "vendor" / "TripoSR"


def _add_triposr_to_path():
    if not TRIPOSR_DIR.exists():
        print(f"\nvendor/TripoSR nao encontrado.")
        print("Execute: bash setup.sh")
        sys.exit(1)
    triposr_str = str(TRIPOSR_DIR)
    if triposr_str not in sys.path:
        sys.path.insert(0, triposr_str)


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


class TripoSREngine:
    name = "TripoSR"
    description = "rapido, CPU / MPS / CUDA"

    def __init__(self):
        self.device = _detect_device()

    def device_label(self):
        labels = {"cuda": "CUDA GPU", "mps": "Apple MPS", "cpu": "CPU"}
        return labels.get(self.device, self.device)

    def check_dependencies(self):
        _add_triposr_to_path()
        missing = []
        for pkg in ("torch", "rembg", "PIL", "tsr"):
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
        import rembg
        from PIL import Image
        from tsr.system import TSR
        from tsr.utils import remove_background, resize_foreground

        print(f"      -> Dispositivo: {self.device_label()}")
        print(f"      -> Carregando TripoSR (primeira vez baixa ~1.5 GB)...")

        model = TSR.from_pretrained(
            "stabilityai/TripoSR",
            config_name="config.yaml",
            weight_name="model.ckpt",
        )
        model.renderer.set_chunk_size(131072)
        model.to(self.device)

        print(f"      -> Removendo fundo...")
        image = Image.open(image_path).convert("RGB")
        rembg_session = rembg.new_session()
        image_rgba = remove_background(image, rembg_session)  # returns RGBA
        image_rgba = resize_foreground(image_rgba, 0.85)

        # Compositar RGBA sobre fundo branco -> RGB (modelo espera 3 canais)
        background = Image.new("RGB", image_rgba.size, (255, 255, 255))
        background.paste(image_rgba, mask=image_rgba.split()[3])
        image = background

        print(f"      -> Reconstruindo malha 3D (resolucao 256)...")
        with torch.no_grad():
            scene_codes = model([image], device=self.device)
            meshes = model.extract_mesh(scene_codes, has_vertex_color=False, resolution=256)

        meshes[0].export(str(output_path))
        return output_path
