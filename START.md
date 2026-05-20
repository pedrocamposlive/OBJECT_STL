# Photo to STL Pipeline - START GUIDE

**Transforme uma foto em STL em 3 minutos**

---

## PRE-REQUISITOS

- Python 3.9+ instalado (`python3 --version`)
- API Key do Google Gemini
- Uma foto clara de um objeto

---

## STEP 1: CONFIGURE A API KEY

Abra o Terminal e cole:

```bash
export GOOGLE_API_KEY='sua_chave_aqui'
```

Para testar:
```bash
echo $GOOGLE_API_KEY
```

---

## STEP 2: INSTALE DEPENDENCIAS

```bash
pip install google-generativeai trimesh numpy --break-system-packages
```

---

## STEP 3: COLOQUE A FOTO NA PASTA INPUT

Copie ou mova sua foto para:

```
~/Desktop/GIT_OBJECT_STL/INPUT/
```

Formatos aceitos: `.jpg`, `.jpeg`, `.png`, `.webp`

O nome do arquivo sera usado como nome do objeto no STL.
Exemplo: `suporte_camera.jpg` gera `suporte_camera.stl`

---

## STEP 4: EXECUTE O PIPELINE

```bash
python3 ~/Desktop/GIT_OBJECT_STL/photo_to_stl_pipeline.py
```

Se houver mais de uma foto na pasta INPUT, o script pergunta qual processar.

---

## O QUE ACONTECE:

```
[1/4] Analisando foto com Gemini Vision...
      -> Identifica o objeto
      -> Extrai dimensoes aproximadas
      -> Detecta detalhes

[2/4] Buscando especificacoes precisas...
      -> Refina dimensoes com base no conhecimento tecnico
      -> Material recomendado
      -> Detalhes tecnicos

[3/4] Gerando STL parametrizado...
      -> Cria modelo 3D
      -> Aplica dimensoes reais
      -> Salva arquivo em OUTPUT/

[4/4] Resumo do processo...
      -> Mostra o que foi criado
      -> Proximos passos
```

Resultado esperado:

```
====================================================
Objeto: [nome identificado]
Dimensoes: {'comprimento': X, 'largura': Y, 'altura': Z}
Material sugerido: PLA/PETG/ABS
STL: /Users/.../OUTPUT/nome_objeto.stl

Proximos passos:
  1. Abra o STL no Fusion 360
  2. Refine detalhes/furos/angulos
  3. Fatie no Bambu Studio
  4. Imprima na Bambu Lab A1
====================================================
```

---

## ONDE ENCONTRAR O RESULTADO

O STL e salvo automaticamente em:

```
~/Desktop/GIT_OBJECT_STL/OUTPUT/nome_do_objeto.stl
```

Para listar os arquivos gerados:
```bash
ls ~/Desktop/GIT_OBJECT_STL/OUTPUT/
```

---

## ABRIR NO FUSION 360

1. Abra **Fusion 360**
2. File -> Open
3. Selecione o arquivo em `OUTPUT/`
4. Modelo aparece em 3D
5. Voce pode:
   - Refinar geometria
   - Adicionar furos (M3, M5, etc)
   - Ajustar dimensoes
   - Re-exportar se precisar

---

## ENVIAR PARA BAMBU

1. Fusion 360: File -> Export -> STL
2. Salve em local facil (Desktop)
3. Abra **Bambu Studio**
4. Plate -> Add -> Seu arquivo STL
5. Configure:
   - Rotacao/orientacao
   - Suportes
   - Infill (10-15% e suficiente)
   - Material (PLA, PETG)
6. Slice
7. Print

---

## TROUBLESHOOTING

### "GOOGLE_API_KEY nao configurada"
```bash
export GOOGLE_API_KEY='sua_chave'
echo $GOOGLE_API_KEY  # deve retornar a chave
```

### "Nenhuma imagem encontrada em INPUT/"
- Verifique se a foto esta dentro da pasta `INPUT/`
- Confirme que o formato e .jpg, .jpeg, .png ou .webp

### "Erro ao parsear JSON"
- Tente novamente (as vezes o Gemini retorna formato inesperado)
- Use uma foto mais clara com fundo neutro
- Prefira objetos comuns e bem documentados

### "ModuleNotFoundError"
```bash
pip install --upgrade google-generativeai trimesh numpy --break-system-packages
```

---

## DICAS PRO

### Foto melhor = STL melhor
- Boa iluminacao (luz natural)
- Angulo que mostre perspectiva 3D
- Fundo neutro (facilita identificacao)
- Objeto completo, nada cortado

### Nome do arquivo = nome do STL
Nomeie a foto de forma descritiva antes de colocar na INPUT:
```
suporte_monitor.jpg    ->  OUTPUT/suporte_monitor.stl
conector_usb_c.png     ->  OUTPUT/conector_usb_c.stl
```

---

## READY?

```bash
# 1. Configure a chave (uma vez por sessao de terminal)
export GOOGLE_API_KEY='sua_chave_aqui'

# 2. Coloque a foto em INPUT/ e rode:
python3 ~/Desktop/GIT_OBJECT_STL/photo_to_stl_pipeline.py
```

---

**Photo to STL Pipeline — pragmatismo e Python**
