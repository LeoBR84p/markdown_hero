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


def test_word_format_renders_hyperlinks_and_hr(tmp_path: Path):
    md = "Visit [Anthropic](https://www.anthropic.com) today.\n\n---\n\nNext section.\n"
    out = tmp_path / "links.docx"
    word_format(md, out)
    d = docx.Document(str(out))
    xml = "\n".join(p._p.xml for p in d.paragraphs)
    assert "w:hyperlink" in xml
    rels = d.part.rels
    assert any("anthropic.com" in rel.target_ref for rel in rels.values())


def test_word_format_renders_image_alt_text(tmp_path: Path):
    md = "Diagram: ![architecture](diagram.png)\n"
    out = tmp_path / "img.docx"
    word_format(md, out)
    d = docx.Document(str(out))
    text = "\n".join(p.text for p in d.paragraphs)
    assert "architecture" in text or "diagram.png" in text


def test_word_format_renders_strikethrough_and_inline_code(tmp_path: Path):
    md = "This is ~~old~~ news with `code` inline.\n"
    out = tmp_path / "fmt.docx"
    word_format(md, out)
    d = docx.Document(str(out))
    runs = [r for p in d.paragraphs for r in p.runs]
    assert any(r.font.strike for r in runs)
    assert any(r.font.name == "Consolas" for r in runs)


def test_word_format_renders_ordered_list(tmp_path: Path):
    md = "1. one\n2. two\n3. three\n"
    out = tmp_path / "ol.docx"
    word_format(md, out)
    d = docx.Document(str(out))
    styles = [p.style.name for p in d.paragraphs if p.text.strip()]
    assert any("List Number" in s for s in styles)


def test_word_format_renders_table_caption(tmp_path: Path):
    md = "| a | b |\n|---|---|\n| 1 | 2 |\n\nTable: example caption\n"
    out = tmp_path / "cap.docx"
    word_format(md, out)
    d = docx.Document(str(out))
    text = "\n".join(p.text for p in d.paragraphs)
    assert "example caption" in text


def test_word_format_handles_unknown_block_kind(tmp_path: Path):
    """Reaching the MarkdownStructureError branch requires touching the
    private _render_block dispatch — testing internal invariants is the
    point, hence the pyright suppression on the import."""
    from markdown_hero import MarkdownStructureError
    from markdown_hero.docx import _render_block  # pyright: ignore[reportPrivateUsage]

    out = tmp_path / "x.docx"
    word_format("# T\n\nbody", out)
    d = docx.Document(str(out))
    with pytest.raises(MarkdownStructureError):
        _render_block(d, {"kind": "nonexistent"}, {})  # pyright: ignore[reportPrivateUsage]
