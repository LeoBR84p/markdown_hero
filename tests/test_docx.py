from pathlib import Path

import pytest

docx = pytest.importorskip("docx")

from markdown_hero import word_format


SAMPLE = """# Título

Parágrafo com **negrito**, *itálico* e `inline code`.

## Subtítulo

- item 1
- item 2

1. um
2. dois

> citação

```python
print("hi")
```

| Col A | Col B |
|:------|------:|
| 1     | 2     |
| 3     | 4     |

Table: legenda da tabela
"""


def test_word_format_creates_docx(tmp_path: Path):
    out = tmp_path / "out.docx"
    word_format(SAMPLE, out)
    assert out.exists() and out.stat().st_size > 0
    d = docx.Document(str(out))
    texts = [p.text for p in d.paragraphs]
    assert any("Título" in t for t in texts)
    assert any("citação" in t for t in texts)
    # Tabela renderizada.
    assert len(d.tables) == 1
    table = d.tables[0]
    assert table.rows[0].cells[0].text.strip().lower().startswith("col a")


def test_word_format_with_overrides(tmp_path: Path):
    out = tmp_path / "out.docx"
    word_format(SAMPLE, out, style_overrides={"body_size": 12})
    assert out.exists()


def test_word_format_with_template(tmp_path: Path):
    template = tmp_path / "template.docx"
    docx.Document().save(str(template))
    out = tmp_path / "out.docx"
    word_format(SAMPLE, out, template=template)
    assert out.exists() and out.stat().st_size > 0


def test_word_format_reads_from_path(tmp_path: Path):
    src = tmp_path / "source.md"
    src.write_text(SAMPLE, encoding="utf-8")
    out = tmp_path / "out.docx"
    word_format(src, out)
    d = docx.Document(str(out))
    assert any("Título" in p.text for p in d.paragraphs)
