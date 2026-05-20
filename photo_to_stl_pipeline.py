import sys
import os
import json
import re
import numpy as np
import trimesh
from pathlib import Path
from google import genai
from google.genai import types

SCRIPT_DIR = Path(__file__).parent
INPUT_DIR  = SCRIPT_DIR / "INPUT"
OUTPUT_DIR = SCRIPT_DIR / "OUTPUT"
SUPPORTED  = {".jpg", ".jpeg", ".png", ".webp"}
MIME_MAP   = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
MODEL      = "gemini-2.5-flash"


def configure_api():
    key = os.environ.get("GOOGLE_API_KEY")
    if not key:
        print("ERRO: GOOGLE_API_KEY nao configurada.")
        print("Execute: export GOOGLE_API_KEY='sua_chave'")
        sys.exit(1)
    return genai.Client(api_key=key)


def find_images():
    INPUT_DIR.mkdir(exist_ok=True)
    images = [f for f in INPUT_DIR.iterdir() if f.suffix.lower() in SUPPORTED]
    if not images:
        print(f"Nenhuma imagem encontrada em {INPUT_DIR}/")
        print("Coloque um arquivo .jpg, .jpeg, .png ou .webp na pasta INPUT/ e rode novamente.")
        sys.exit(0)
    images.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return images


def select_image(images):
    if len(images) == 1:
        print(f"Imagem encontrada: {images[0].name}")
        return images[0]
    print("\nImagens encontradas na pasta INPUT:")
    for i, img in enumerate(images, 1):
        print(f"  [{i}] {img.name}")
    while True:
        choice = input("\nQual processar? (numero ou ENTER para a mais recente): ").strip()
        if choice == "":
            return images[0]
        if choice.isdigit() and 1 <= int(choice) <= len(images):
            return images[int(choice) - 1]
        print("Opcao invalida. Tente novamente.")


def parse_json_response(text):
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
    if match:
        text = match.group(1).strip()
    return json.loads(text)


def analyze_photo(client, image_path):
    mime_type = MIME_MAP.get(image_path.suffix.lower(), "image/jpeg")
    image_bytes = image_path.read_bytes()

    prompt = (
        "Analise esta imagem e identifique o objeto. "
        "Retorne SOMENTE um JSON valido, sem texto adicional:\n"
        "{\n"
        '  "nome": "nome do objeto",\n'
        '  "tipo": "categoria do objeto",\n'
        '  "dimensoes_estimadas": {"comprimento": valor_mm, "largura": valor_mm, "altura": valor_mm},\n'
        '  "forma_base": "box|cylinder|sphere",\n'
        '  "tem_furos": true|false,\n'
        '  "material_sugerido": "PLA|PETG|ABS",\n'
        '  "detalhes": ["detalhe1", "detalhe2"],\n'
        '  "termos_busca": "termos para buscar especificacoes tecnicas"\n'
        "}"
    )

    response = client.models.generate_content(
        model=MODEL,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            prompt,
        ],
    )
    return parse_json_response(response.text)


def search_specifications(client, analysis):
    object_name = analysis.get("nome", "objeto desconhecido")
    search_terms = analysis.get("termos_busca", object_name)
    dims_est = analysis.get("dimensoes_estimadas", {})

    prompt = (
        f"Voce e um especialista em especificacoes tecnicas de produtos.\n"
        f"Objeto: {object_name}\n"
        f"Contexto: {search_terms}\n"
        f"Dimensoes estimadas pela visao: {dims_est}\n\n"
        "Refine as dimensoes e especificacoes com base no seu conhecimento tecnico.\n"
        "Retorne SOMENTE um JSON valido:\n"
        "{\n"
        '  "dimensoes_precisas": {"comprimento": valor_mm, "largura": valor_mm, "altura": valor_mm},\n'
        '  "material_recomendado": "PLA|PETG|ABS",\n'
        '  "espessura_parede": valor_mm,\n'
        '  "detalhes_tecnicos": ["detalhe1", "detalhe2"],\n'
        '  "fonte": "descricao da fonte de referencia"\n'
        "}"
    )

    response = client.models.generate_content(model=MODEL, contents=prompt)
    return parse_json_response(response.text)


def generate_stl(analysis, specs, output_stem):
    OUTPUT_DIR.mkdir(exist_ok=True)
    dims = specs.get("dimensoes_precisas") or analysis.get("dimensoes_estimadas", {})
    comprimento = float(dims.get("comprimento", 50))
    largura     = float(dims.get("largura", 30))
    altura      = float(dims.get("altura", 20))
    espessura   = float(specs.get("espessura_parede", 2.0))
    forma       = analysis.get("forma_base", "box")
    tem_furos   = analysis.get("tem_furos", False)

    if forma == "cylinder":
        mesh = trimesh.creation.cylinder(radius=min(comprimento, largura) / 2, height=altura, sections=64)
    elif forma == "sphere":
        mesh = trimesh.creation.icosphere(subdivisions=4, radius=min(comprimento, largura, altura) / 2)
    else:
        outer = trimesh.creation.box([comprimento, largura, altura])
        if 0 < espessura < min(comprimento, largura) / 2:
            inner = trimesh.creation.box([comprimento - espessura * 2, largura - espessura * 2, altura])
            inner.apply_translation([0, 0, espessura])
            try:
                result = trimesh.boolean.difference([outer, inner])
                mesh = result if (result is not None and result.is_valid) else outer
            except Exception:
                mesh = outer
        else:
            mesh = outer

        if tem_furos:
            try:
                hole_r = min(comprimento, largura) * 0.08
                hole = trimesh.creation.cylinder(radius=hole_r, height=altura + 2, sections=32)
                hole.apply_translation([comprimento * 0.3, largura * 0.3, 0])
                result = trimesh.boolean.difference([mesh, hole])
                if result is not None and result.is_valid:
                    mesh = result
            except Exception:
                pass

    output_path = OUTPUT_DIR / f"{output_stem}.stl"
    mesh.export(str(output_path))
    return output_path, mesh


def main():
    client = configure_api()

    images = find_images()
    image_path = select_image(images)
    output_stem = image_path.stem

    print(f"\nProcessando: {image_path.name}  ->  OUTPUT/{output_stem}.stl")

    print("\n[1/4] Analisando foto com Gemini Vision...")
    analysis = analyze_photo(client, image_path)
    print(f"      -> Objeto: {analysis.get('nome')}")
    print(f"      -> Dimensoes estimadas: {analysis.get('dimensoes_estimadas')}")
    print(f"      -> Detalhes: {', '.join(analysis.get('detalhes', []))}")

    print("\n[2/4] Buscando especificacoes precisas...")
    specs = search_specifications(client, analysis)
    print(f"      -> Dimensoes refinadas: {specs.get('dimensoes_precisas')}")
    print(f"      -> Material: {specs.get('material_recomendado')}")
    print(f"      -> Detalhes tecnicos: {', '.join(specs.get('detalhes_tecnicos', []))}")

    print("\n[3/4] Gerando STL parametrizado...")
    stl_path, mesh = generate_stl(analysis, specs, output_stem)
    dims_final = specs.get("dimensoes_precisas") or analysis.get("dimensoes_estimadas", {})
    print(f"      -> {mesh.vertices.shape[0]} vertices gerados")
    print(f"      -> Dimensoes aplicadas: {dims_final}")
    print(f"      -> Arquivo: {stl_path}")

    print("\n[4/4] Resumo do processo...")
    print("\n====================================================")
    print(f"Objeto: {analysis.get('nome', output_stem)}")
    print(f"Dimensoes: {dims_final}")
    print(f"Material sugerido: {specs.get('material_recomendado', analysis.get('material_sugerido', 'PLA'))}")
    print(f"STL: {stl_path.resolve()}")
    print("\nProximos passos:")
    print("  1. Abra o STL no Fusion 360")
    print("  2. Refine detalhes/furos/angulos")
    print("  3. Fatie no Bambu Studio")
    print("  4. Imprima na Bambu Lab A1")
    print("====================================================\n")


if __name__ == "__main__":
    main()
