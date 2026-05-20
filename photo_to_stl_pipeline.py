import sys
import os
import json
import re
import base64
import numpy as np
import trimesh
import google.generativeai as genai
from pathlib import Path


def configure_api():
    key = os.environ.get("GOOGLE_API_KEY")
    if not key:
        print("ERRO: GOOGLE_API_KEY nao configurada.")
        print("Execute: export GOOGLE_API_KEY='sua_chave'")
        sys.exit(1)
    genai.configure(api_key=key)
    return genai.GenerativeModel("gemini-2.0-flash")


def parse_json_response(text):
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
    if match:
        text = match.group(1).strip()
    return json.loads(text)


def analyze_photo(model, image_path):
    suffix = Path(image_path).suffix.lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    mime_type = mime_map.get(suffix, "image/jpeg")

    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode()

    prompt = (
        "Analise esta imagem e identifique o objeto. "
        "Retorne SOMENTE um JSON valido, sem texto adicional, com esta estrutura:\n"
        "{\n"
        '  "nome": "nome do objeto",\n'
        '  "tipo": "categoria do objeto",\n'
        '  "dimensoes_estimadas": {"comprimento": valor_em_mm, "largura": valor_em_mm, "altura": valor_em_mm},\n'
        '  "forma_base": "box|cylinder|sphere",\n'
        '  "tem_furos": true|false,\n'
        '  "material_sugerido": "PLA|PETG|ABS",\n'
        '  "detalhes": ["detalhe1", "detalhe2"],\n'
        '  "termos_busca": "termos para buscar especificacoes tecnicas"\n'
        "}"
    )

    response = model.generate_content([
        prompt,
        {"mime_type": mime_type, "data": image_data}
    ])
    return parse_json_response(response.text)


def search_specifications(model, analysis):
    object_name = analysis.get("nome", "objeto desconhecido")
    search_terms = analysis.get("termos_busca", object_name)
    dims_est = analysis.get("dimensoes_estimadas", {})

    prompt = (
        f"Voce e um especialista em especificacoes tecnicas de produtos.\n"
        f"Objeto: {object_name}\n"
        f"Contexto de busca: {search_terms}\n"
        f"Dimensoes estimadas pela visao: {dims_est}\n\n"
        "Com base no seu conhecimento tecnico, refine as dimensoes e especificacoes.\n"
        "Retorne SOMENTE um JSON valido:\n"
        "{\n"
        '  "dimensoes_precisas": {"comprimento": valor_em_mm, "largura": valor_em_mm, "altura": valor_em_mm},\n'
        '  "material_recomendado": "PLA|PETG|ABS",\n'
        '  "espessura_parede": valor_em_mm,\n'
        '  "detalhes_tecnicos": ["detalhe1", "detalhe2"],\n'
        '  "fonte": "descricao da fonte de referencia"\n'
        "}"
    )

    response = model.generate_content(prompt)
    return parse_json_response(response.text)


def generate_stl(analysis, specs, output_name):
    dims = specs.get("dimensoes_precisas") or analysis.get("dimensoes_estimadas", {})
    comprimento = float(dims.get("comprimento", 50))
    largura = float(dims.get("largura", 30))
    altura = float(dims.get("altura", 20))
    espessura = float(specs.get("espessura_parede", 2.0))
    forma = analysis.get("forma_base", "box")
    tem_furos = analysis.get("tem_furos", False)

    if forma == "cylinder":
        radius = min(comprimento, largura) / 2
        mesh = trimesh.creation.cylinder(radius=radius, height=altura, sections=64)
    elif forma == "sphere":
        radius = min(comprimento, largura, altura) / 2
        mesh = trimesh.creation.icosphere(subdivisions=4, radius=radius)
    else:
        outer = trimesh.creation.box([comprimento, largura, altura])
        if espessura > 0 and espessura < min(comprimento, largura, altura) / 2:
            inner = trimesh.creation.box([
                comprimento - espessura * 2,
                largura - espessura * 2,
                altura
            ])
            inner.apply_translation([0, 0, espessura])
            try:
                mesh = trimesh.boolean.difference([outer, inner])
                if mesh is None or not mesh.is_valid:
                    mesh = outer
            except Exception:
                mesh = outer
        else:
            mesh = outer

    if tem_furos and forma == "box":
        try:
            hole_radius = min(comprimento, largura) * 0.08
            hole = trimesh.creation.cylinder(radius=hole_radius, height=altura + 2, sections=32)
            hole.apply_translation([comprimento * 0.3, largura * 0.3, 0])
            mesh = trimesh.boolean.difference([mesh, hole])
            if mesh is None or not mesh.is_valid:
                mesh = trimesh.creation.box([comprimento, largura, altura])
        except Exception:
            pass

    output_path = f"{output_name}.stl"
    mesh.export(output_path)
    return output_path, mesh


def main():
    if len(sys.argv) < 3:
        print("Uso: python3 photo_to_stl_pipeline.py <foto.jpg> <nome_objeto>")
        sys.exit(1)

    image_path = sys.argv[1]
    output_name = sys.argv[2]

    if not os.path.exists(image_path):
        print(f"ERRO: Arquivo nao encontrado: {image_path}")
        sys.exit(1)

    model = configure_api()

    print("\n[1/4] Analisando foto com Gemini Vision...")
    analysis = analyze_photo(model, image_path)
    dims_est = analysis.get("dimensoes_estimadas", {})
    print(f"      -> Objeto identificado: {analysis.get('nome')}")
    print(f"      -> Dimensoes estimadas: {dims_est}")
    print(f"      -> Detalhes: {', '.join(analysis.get('detalhes', []))}")

    print("\n[2/4] Buscando especificacoes precisas na web...")
    specs = search_specifications(model, analysis)
    dims_prec = specs.get("dimensoes_precisas", {})
    print(f"      -> Dimensoes refinadas: {dims_prec}")
    print(f"      -> Material recomendado: {specs.get('material_recomendado')}")
    print(f"      -> Detalhes tecnicos: {', '.join(specs.get('detalhes_tecnicos', []))}")

    print("\n[3/4] Gerando STL parametrizado...")
    stl_path, mesh = generate_stl(analysis, specs, output_name)
    dims_final = specs.get("dimensoes_precisas") or dims_est
    print(f"      -> Modelo 3D criado  ({mesh.vertices.shape[0]} vertices)")
    print(f"      -> Dimensoes aplicadas: {dims_final}")
    print(f"      -> Arquivo salvo: {os.path.abspath(stl_path)}")

    print("\n[4/4] Resumo do processo...")
    print("\n====================================================")
    print(f"Objeto: {analysis.get('nome', output_name)}")
    print(f"Dimensoes: {dims_final}")
    print(f"Material sugerido: {specs.get('material_recomendado', analysis.get('material_sugerido', 'PLA'))}")
    print(f"Arquivo: {os.path.abspath(stl_path)}")
    print("\nProximos passos:")
    print("  1. Abra o STL no Fusion 360")
    print("  2. Refine detalhes/furos/angulos")
    print("  3. Fatie no Bambu Studio")
    print("  4. Imprima na Bambu Lab A1")
    print("====================================================\n")


if __name__ == "__main__":
    main()
