import sys
import os
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
INPUT_DIR  = SCRIPT_DIR / "INPUT"
OUTPUT_DIR = SCRIPT_DIR / "OUTPUT"
SUPPORTED  = {".jpg", ".jpeg", ".png", ".webp"}


def find_images():
    INPUT_DIR.mkdir(exist_ok=True)
    images = [f for f in INPUT_DIR.iterdir() if f.suffix.lower() in SUPPORTED]
    if not images:
        print(f"Nenhuma imagem encontrada em INPUT/")
        print("Coloque um arquivo .jpg, .jpeg, .png ou .webp na pasta INPUT/ e rode novamente.")
        sys.exit(0)
    images.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return images


def select_image(images):
    if len(images) == 1:
        print(f"Imagem: {images[0].name}")
        return images[0]
    print("\nImagens em INPUT/:")
    for i, img in enumerate(images, 1):
        print(f"  [{i}] {img.name}")
    while True:
        choice = input("\nQual processar? (numero ou ENTER para a mais recente): ").strip()
        if choice == "":
            return images[0]
        if choice.isdigit() and 1 <= int(choice) <= len(images):
            return images[int(choice) - 1]
        print("Opcao invalida.")


def select_engine():
    from engines import ENGINES

    try:
        import torch
        cuda = torch.cuda.is_available()
        mps  = torch.backends.mps.is_available()
    except ImportError:
        cuda = mps = False

    device_hint = "CUDA GPU" if cuda else ("Apple MPS" if mps else "CPU")

    print("\nMotor de reconstrucao 3D:")
    print(f"  Dispositivo detectado: {device_hint}\n")
    print("  [1] TripoSR       — rapido, CPU / MPS / CUDA")
    print("  [2] InstantMesh   — alta qualidade, CUDA RTX  (Ubuntu + RTX 4090)")
    print()

    while True:
        choice = input("Escolha o motor (ENTER para [1]): ").strip()
        if choice == "":
            choice = "1"
        if choice in ENGINES:
            engine = ENGINES[choice]()
            print(f"\nMotor selecionado: {engine.name}")
            return engine
        print("Opcao invalida. Digite 1 ou 2.")


def run_pipeline(engine, image_path):
    OUTPUT_DIR.mkdir(exist_ok=True)
    output_path = OUTPUT_DIR / f"{image_path.stem}.stl"

    print(f"\nProcessando : {image_path.name}")
    print(f"Saida       : OUTPUT/{output_path.name}")
    print(f"Motor       : {engine.name}\n")

    print("[1/3] Preparando imagem...")
    print(f"      -> {image_path.name}  ({image_path.stat().st_size // 1024} KB)")

    print("\n[2/3] Reconstruindo geometria 3D...")
    engine.reconstruct(image_path, output_path)

    print("\n[3/3] Finalizando...")
    size_kb = output_path.stat().st_size // 1024
    print(f"      -> STL gerado: {size_kb} KB")
    print(f"      -> Caminho: {output_path.resolve()}")

    print("\n====================================================")
    print(f"Arquivo : {output_path.name}")
    print(f"Motor   : {engine.name}")
    print(f"Local   : {output_path.resolve()}")
    print("\nProximos passos:")
    print("  1. Abra o STL no Fusion 360")
    print("  2. Refine detalhes/furos/angulos")
    print("  3. Fatie no Bambu Studio")
    print("  4. Imprima na Bambu Lab A1")
    print("====================================================\n")


def main():
    images = find_images()
    image_path = select_image(images)
    engine = select_engine()
    run_pipeline(engine, image_path)


if __name__ == "__main__":
    main()
