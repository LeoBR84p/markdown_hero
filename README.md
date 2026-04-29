# markdown_hero

Biblioteca Python para tratamento de Markdown — limpeza, chunking, exportação
para Word (.docx), concatenação, divisão por delimitadores e validação.

Compatível com Python 3.10+. Dialeto-alvo: GitHub Flavored Markdown (GFM).

## Instalação

```bash
pip install markdown_hero
# com tokenizer real (tiktoken) para chunking preciso:
pip install "markdown_hero[tokenizers]"
```

## Funções principais

| Função | O que faz |
|---|---|
| `strip(md, ...)` | Reduz Markdown a texto plano normalizado (sem acentos, pontuação, em minúsculas). |
| `extract_chunks(md, purpose=...)` | Divide o documento respeitando hierarquia de headings, com metadados ricos. |
| `word_format(md, output)` | Exporta para .docx aplicando um conjunto fixo de estilos profissionais. |
| `markdown_append(*paths, output)` | Concatena arquivos com shift de headings e merge de frontmatter. |
| `markdown_break(path, delimiter, ...)` | Divide um arquivo em N+1 partes. Aceita string, regex ou lista. |
| `markdown_merge(*paths, output)` | Append “inteligente” com dedupe de seções e geração de TOC. |
| `extract_*` | Frontmatter, links, imagens, tabelas, blocos de código, headings, TOC. |
| `lint(md)` | Detecta headings pulados, anchors duplicados, fences abertos. |
| CLI `markdown-hero` | Acesso pela linha de comando. |

Veja `docs/reference.md` para a referência técnica completa.

## Exemplo rápido

```python
from markdown_hero import strip, extract_chunks, word_format

text = "**Olá!** Veja [docs](https://x). p=2 captura ambos."
print(strip(text))
# "ola veja docs p2 captura ambos"

chunks = extract_chunks(open("doc.md").read(), purpose="rag", max_tokens=512)
word_format("doc.md", "doc.docx")
```

## CLI

```bash
markdown-hero strip doc.md -o doc.txt
markdown-hero chunk doc.md --purpose rag --max-tokens 512 -o chunks.json
markdown-hero word doc.md -o doc.docx
markdown-hero append a.md b.md -o merged.md
markdown-hero break doc.md "---" --output-dir parts/
markdown-hero lint doc.md
```

## Licença

MIT
