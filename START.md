# Photo to STL Pipeline - START GUIDE

**Transforme uma foto em STL em 3 minutos**

---

## PRE-REQUISITOS (1 min)

- Ter Python 3.9+ instalado (`python3 --version`)
- Ter a API Key do Google (voce ja tem)
- Uma foto clara de um objeto
- 3 minutos de paciencia

---

## STEP 1: CONFIGURE A API KEY (1 min)

Abra seu Terminal no Mac e copie/cole isso:

```bash
export GOOGLE_API_KEY='sua_chave_aqui'
```

**Substitua `'sua_chave_aqui'` pela sua API Key real.**

Para testar se funcionou:
```bash
echo $GOOGLE_API_KEY
```

Deve retornar sua chave. Se retornar vazio, nao funcionou.

---

## STEP 2: PREPARE A FOTO (1 min)

### Opcao A: Tire uma foto agora (RECOMENDADO)
```bash
# No seu Mac, tire uma foto com iPhone/camera
# Nomeie como: objeto.jpg
# Coloque em: /home/claude/ ou ~/Desktop/
```

### Opcao B: Usa uma foto existente
Apenas renomeie pra algo simples:
```bash
# Exemplo: suporte.jpg, mouse.jpg, adaptador.jpg
```

---

## STEP 3: INSTALE DEPENDENCIAS (2 min)

Copie e cole no Terminal:

```bash
pip install google-generativeai trimesh numpy --break-system-packages
```

Aguarde ate aparecer "Successfully installed...".

---

## STEP 4: EXECUTE O PIPELINE (1 min)

Cole no Terminal (substitua os valores):

```bash
python3 ~/Desktop/GIT_OBJECT_STL/photo_to_stl_pipeline.py /caminho/para/sua/foto.jpg nome_do_objeto
```

### Exemplos reais:

**Se a foto esta no Desktop:**
```bash
python3 ~/Desktop/GIT_OBJECT_STL/photo_to_stl_pipeline.py ~/Desktop/suporte.jpg meu_suporte
```

**Se a foto esta em Downloads:**
```bash
python3 ~/Desktop/GIT_OBJECT_STL/photo_to_stl_pipeline.py ~/Downloads/objeto.jpg meu_objeto
```

---

## O QUE ACONTECE:

O script rodara em 4 etapas:

```
[1/4] Analisando foto com Gemini Vision...
      -> Identifica o objeto
      -> Extrai dimensoes aproximadas
      -> Detecta detalhes

[2/4] Buscando especificacoes precisas na web...
      -> Procura dimensoes exatas
      -> Material recomendado
      -> Detalhes tecnicos

[3/4] Gerando STL parametrizado...
      -> Cria modelo 3D
      -> Aplica dimensoes reais
      -> Salva arquivo

[4/4] Resumo do processo...
      -> Mostra o que foi criado
      -> Proximos passos
```

Se tudo der certo, voce vera:

```
====================================================
Objeto: [nome identificado]
Dimensoes: {'comprimento': X, 'largura': Y, 'altura': Z}
Material sugerido: PLA/PETG/ABS

Proximos passos:
  1. Abra o STL no Fusion 360
  2. Refine detalhes/furos/angulos
  3. Fatie no Bambu Studio
  4. Imprima na Bambu Lab A1
====================================================
```

---

## ONDE ENCONTRAR O RESULTADO

O arquivo STL sera criado **no mesmo lugar** onde voce rodou o comando.

O STL e gerado no diretorio de onde voce rodou o comando. O script mostra o caminho absoluto ao final.

### Para encontrar rapido:
```bash
# Mostra onde esta o arquivo criado
find ~ -name "*.stl" -type f -mmin -5
```

---

## ABRIR NO FUSION 360

1. Abra **Fusion 360**
2. File -> Open
3. Selecione seu `nome_do_objeto.stl`
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

### "API Key invalida"
```bash
# Confirme que configurou certo:
echo $GOOGLE_API_KEY

# Se retornar vazio, configure novamente:
export GOOGLE_API_KEY='sua_chave'
```

### "Arquivo nao encontrado"
```bash
# Verifique o caminho completo:
ls ~/Desktop/foto.jpg   # Se tiver no Desktop

# Ou copie pra /home/claude/:
cp ~/Desktop/foto.jpg /home/claude/
```

### "Erro ao parsear JSON"
- Tente novamente (as vezes a IA retorna formato errado)
- Use uma foto mais clara
- Objeto mais comum (nao muito estranho)

### "ModuleNotFoundError: No module named 'google.generativeai'"
```bash
# Reinstale as dependencias:
pip install --upgrade google-generativeai trimesh numpy --break-system-packages
```

### "Timeout / Gemini nao responde"
- Sua internet pode estar lenta
- Tente novamente em alguns minutos
- Use um objeto mais simples de reconhecer

---

## PROXIMOS TESTES

Depois de testar com um objeto, tente:

1. **Objeto simples**: Mouse, suporte, caixa
2. **Objeto medio**: Conector, adaptador, jig
3. **Objeto complexo**: Eletronico com multiplas partes

A qualidade melhora a medida que o objeto e mais comum/documentado online.

---

## DICAS PRO

### Foto melhor = STL melhor
- Boa iluminacao (luz natural)
- Angulo claro (mostra perspectiva)
- Fundo neutro (facilita identificacao)
- Nada cortado (mostra objeto completo)

### STL pronto para impressao
- A maioria dos modelos ja sai pronta
- Algumas vezes precisa ajustar suportes
- Sempre faca um teste pequeno primeiro

### Reusar specs
Se o resultado foi bom, voce pode:
```bash
# Rodar de novo com foto diferente do mesmo objeto
python3 ~/Desktop/GIT_OBJECT_STL/photo_to_stl_pipeline.py outra_foto.jpg mesmo_objeto_v2
```

---

## READY?

**Copie e cole agora:**

```bash
export GOOGLE_API_KEY='sua_chave_aqui'
pip install google-generativeai trimesh numpy --break-system-packages
python3 ~/Desktop/GIT_OBJECT_STL/photo_to_stl_pipeline.py ~/Desktop/sua_foto.jpg seu_objeto
```

---

**Photo to STL Pipeline — pragmatismo e Python**
