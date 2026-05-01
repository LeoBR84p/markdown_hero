# markdown_hero

[![CI](https://github.com/leobr84p/markdown_hero/actions/workflows/ci.yml/badge.svg)](https://github.com/leobr84p/markdown_hero/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/markdown_hero.svg)](https://pypi.org/project/markdown_hero/)
[![Python versions](https://img.shields.io/pypi/pyversions/markdown_hero.svg)](https://pypi.org/project/markdown_hero/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Typed](https://img.shields.io/badge/typing-typed-brightgreen.svg)](https://peps.python.org/pep-0561/)

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

Veja `docs/reference.md` para a referência técnica completa e
`docs/helpers.md` para o índice de utilitários internos.

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

## Documentação

- Referência técnica: [`docs/reference.md`](docs/reference.md)
- Índice de utilitários internos: [`docs/helpers.md`](docs/helpers.md)
- Histórico de versões: [`CHANGELOG.md`](CHANGELOG.md)
- Como contribuir: [`CONTRIBUTING.md`](CONTRIBUTING.md)
- Política de segurança: [`SECURITY.md`](SECURITY.md)

## Contato

Dúvidas, sugestões e relatos:

- E-mail: [bernardo.leandro@gmail.com](mailto:bernardo.leandro@gmail.com)
- **Inclua sempre o prefixo `Markdown Hero:` no assunto** da mensagem para
  que ela seja roteada corretamente.

Para vulnerabilidades de segurança, siga as instruções de
[`SECURITY.md`](SECURITY.md) (mesmo e-mail, mesmo prefixo no assunto).

## Licença

[MIT](LICENSE) © 2026 Bernardo Leandro.
