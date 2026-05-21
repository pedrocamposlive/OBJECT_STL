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


class DepthEngine:
    name = "DepthAnything v2"
    description = "depth map -> mesh, CPU/MPS/CUDA, superficie visivel real"

    def __init__(self):
        self.device = _detect_device()

    def device_label(self):
        labels = {"cuda": "CUDA GPU", "mps": "Apple MPS", "cpu": "CPU"}
        return labels.get(self.device, self.device)

    def check_dependencies(self):
        missing = []
        for pkg in ("torch", "transformers", "PIL", "trimesh", "numpy", "scipy"):
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
        import trimesh
        from PIL import Image
        from transformers import pipeline as hf_pipeline
        from scipy.ndimage import gaussian_filter

        print(f"      -> Dispositivo: {self.device_label()}")
        print(f"      -> Carregando DepthAnything v2 (primeira vez baixa ~400 MB)...")

        depth_pipe = hf_pipeline(
            "depth-estimation",
            model="depth-anything/Depth-Anything-V2-Small-hf",
            device=0 if self.device == "cuda" else self.device,
        )

        print(f"      -> Estimando profundidade da imagem...")
        image = Image.open(image_path).convert("RGB")

        # Resize para processamento (manter proporcao)
        max_size = 518
        w, h = image.size
        scale = min(max_size / w, max_size / h)
        new_w, new_h = int(w * scale), int(h * scale)
        image_resized = image.resize((new_w, new_h), Image.LANCZOS)

        result = depth_pipe(image_resized)
        depth_map = np.array(result["depth"], dtype=np.float32)

        print(f"      -> Convertendo depth map para mesh 3D...")
        mesh = _depth_to_mesh(depth_map, image_resized)

        output_path.parent.mkdir(exist_ok=True)
        mesh.export(str(output_path))
        return output_path


def _depth_to_mesh(depth: "np.ndarray", image: "Image") -> "trimesh.Trimesh":
    import numpy as np
    import trimesh
    from scipy.ndimage import gaussian_filter

    # Normalizar depth para [0, 1]
    d_min, d_max = depth.min(), depth.max()
    depth_norm = (depth - d_min) / (d_max - d_min + 1e-8)

    # Suavizar para reduzir ruido
    depth_smooth = gaussian_filter(depth_norm, sigma=1.5)

    h, w = depth_smooth.shape

    # Criar grade de vertices (x, y, z)
    xs = np.linspace(0, 1, w)
    ys = np.linspace(0, 1, h)
    xv, yv = np.meshgrid(xs, ys)

    # z = profundidade invertida (objetos proximos tem z maior)
    zv = 1.0 - depth_smooth

    # Escala proporcional ao tamanho real tipico
    scale_xy = 100.0
    scale_z  = 40.0

    vertices = np.stack([
        xv.flatten() * scale_xy,
        yv.flatten() * scale_xy,
        zv.flatten() * scale_z,
    ], axis=1)

    # Criar faces (2 triangulos por celula da grade)
    faces = []
    for row in range(h - 1):
        for col in range(w - 1):
            i = row * w + col
            # Triangulo 1
            faces.append([i,     i + 1,     i + w])
            # Triangulo 2
            faces.append([i + 1, i + w + 1, i + w])

    faces = np.array(faces, dtype=np.int64)

    # Cor dos vertices a partir da imagem original (opcional — STL nao suporta cor mas trimesh guarda)
    img_arr = np.array(image.resize((w, h))).reshape(-1, 3) / 255.0
    vertex_colors = np.hstack([img_arr, np.ones((len(vertices), 1))])

    mesh = trimesh.Trimesh(
        vertices=vertices,
        faces=faces,
        vertex_colors=vertex_colors,
        process=True,
    )

    return mesh
