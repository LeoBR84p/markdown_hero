# markdown_hero

[![CI](https://github.com/leobr84p/markdown_hero/actions/workflows/ci.yml/badge.svg)](https://github.com/leobr84p/markdown_hero/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/markdown_hero.svg)](https://pypi.org/project/markdown_hero/)
[![Python versions](https://img.shields.io/pypi/pyversions/markdown_hero.svg)](https://pypi.org/project/markdown_hero/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Typed](https://img.shields.io/badge/typing-typed-brightgreen.svg)](https://peps.python.org/pep-0561/)

A Python library for processing Markdown — cleanup, chunking, Word
(.docx) export, concatenation, splitting by delimiters, and validation.

Compatible with Python 3.10+. Target dialect: GitHub Flavored Markdown (GFM).

## Installation

```bash
pip install markdown_hero
# with a real tokenizer (tiktoken) for accurate chunking:
pip install "markdown_hero[tokenizers]"
```

## Main functions

| Function | What it does |
|---|---|
| `strip(md, ...)` | Reduces Markdown to normalized plain text (no diacritics, no punctuation, lowercase). |
| `extract_chunks(md, purpose=...)` | Splits the document respecting heading hierarchy, with rich metadata. |
| `word_format(md, output)` | Exports to .docx with a fixed set of professional styles. |
| `markdown_append(*paths, output)` | Concatenates files with heading shift and frontmatter merge. |
| `markdown_break(path, delimiter, ...)` | Splits a file into N+1 parts. Accepts string, regex, or list. |
| `markdown_merge(*paths, output)` | Smart append with section dedupe and TOC generation. |
| `extract_*` | Frontmatter, links, images, tables, code blocks, headings, TOC. |
| `lint(md)` | Detects skipped headings, duplicate anchors, unclosed fences. |
| CLI `markdown-hero` | Command-line access. |

See `docs/reference.md` for the full technical reference and
`docs/helpers.md` for the index of internal utilities.

## Quick example

```python
from markdown_hero import strip, extract_chunks, word_format

text = "**Hello!** See [docs](https://x). p=2 captures both."
print(strip(text))
# "hello see docs p2 captures both"

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

## Documentation

- Technical reference: [`docs/reference.md`](docs/reference.md)
- Internal helpers index: [`docs/helpers.md`](docs/helpers.md)
- Release history: [`CHANGELOG.md`](CHANGELOG.md)
- How to contribute: [`CONTRIBUTING.md`](CONTRIBUTING.md)
- Security policy: [`SECURITY.md`](SECURITY.md)

## Contact

Questions, suggestions, and reports:

- Email: [bernardo.leandro@gmail.com](mailto:bernardo.leandro@gmail.com)
- **Always include the prefix `Markdown Hero:` in the subject line** so
  the message is routed correctly.

For security vulnerabilities follow the instructions in
[`SECURITY.md`](SECURITY.md) (same email, same subject prefix).

## License

[MIT](LICENSE) © 2026 Bernardo Leandro.
