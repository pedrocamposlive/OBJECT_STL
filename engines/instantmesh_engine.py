import sys
from pathlib import Path


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
            print("Este motor e otimizado para o Ubuntu + RTX 4090.")
            print("No Mac, use TripoSR (opcao 1).")
            sys.exit(1)

        missing = []
        for pkg in ("torch", "diffusers", "transformers", "rembg", "PIL"):
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

        print(f"      -> Dispositivo: {self.device_label()}")
        print(f"      -> Carregando InstantMesh (primeira vez baixa ~5 GB)...")

        # Multi-view generation + 3D reconstruction via InstantMesh pipeline
        # Referencia: https://github.com/TencentARC/InstantMesh
        from diffusers import DiffusionPipeline

        pipeline = DiffusionPipeline.from_pretrained(
            "TencentARC/InstantMesh",
            torch_dtype=torch.float16,
        ).to(self.device)

        print(f"      -> Removendo fundo...")
        image = Image.open(image_path).convert("RGB")
        rembg_session = rembg.new_session()
        image = rembg.remove(image, session=rembg_session)

        print(f"      -> Gerando multiplas vistas e reconstruindo mesh...")
        result = pipeline(image=image, num_inference_steps=75)
        mesh = result.meshes[0]
        mesh.export(str(output_path))

        return output_path
