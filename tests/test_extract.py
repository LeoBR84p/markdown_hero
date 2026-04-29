import pytest

from markdown_hero import (
    FrontmatterError,
    build_toc,
    extract_code_blocks,
    extract_frontmatter,
    extract_headings,
    extract_images,
    extract_links,
    extract_tables,
    remove_frontmatter,
)


SAMPLE = """---
title: Doc
tags: [a, b]
---

# Capítulo 1

Texto com [link](https://x.com) e ![logo](logo.png "t").

## Seção 1.1

```python
print("hi")
```

| Col A | Col B |
|:------|------:|
| 1     | 2     |
| 3     | 4     |
"""


def test_frontmatter():
    fm = extract_frontmatter(SAMPLE)
    assert fm["title"] == "Doc"
    assert fm["tags"] == ["a", "b"]


def test_remove_frontmatter():
    body, fm = remove_frontmatter(SAMPLE)
    assert body.lstrip().startswith("# Capítulo 1")
    assert fm["title"] == "Doc"


def test_headings():
    hs = extract_headings(SAMPLE)
    assert [h.level for h in hs] == [1, 2]
    assert hs[0].text == "Capítulo 1"
    assert hs[0].anchor == "capitulo-1"


def test_links_images():
    links = extract_links(SAMPLE)
    assert any(l.url == "https://x.com" for l in links)
    images = extract_images(SAMPLE)
    assert images[0].alt == "logo"
    assert images[0].url == "logo.png"


def test_code_blocks():
    blocks = extract_code_blocks(SAMPLE)
    assert blocks[0].language == "python"
    assert "print" in blocks[0].code

    py_only = extract_code_blocks(SAMPLE, language="python")
    assert len(py_only) == 1
    assert extract_code_blocks(SAMPLE, language="rust") == []


def test_tables():
    tables = extract_tables(SAMPLE)
    assert len(tables) == 1
    t = tables[0]
    assert t.headers == ["Col A", "Col B"]
    assert t.rows == [["1", "2"], ["3", "4"]]
    assert t.alignments == ["left", "right"]


def test_build_toc():
    toc = build_toc(SAMPLE)
    assert "[Capítulo 1](#capitulo-1)" in toc
    assert "[Seção 1.1](#secao-11)" in toc


def test_invalid_frontmatter_raises():
    bad = "---\nkey: : invalid : :\n---\n\nbody"
    with pytest.raises(FrontmatterError):
        extract_frontmatter(bad)


def test_non_mapping_frontmatter_raises():
    bad = "---\n- a\n- b\n---\n\nbody"
    with pytest.raises(FrontmatterError):
        extract_frontmatter(bad)


def test_empty_frontmatter_returns_empty_dict():
    assert extract_frontmatter("---\n---\n\nbody") == {}
