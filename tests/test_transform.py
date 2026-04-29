from markdown_hero import (
    md_to_plain,
    normalize,
    shift_headings,
    slugify,
    strip_code_blocks,
    strip_html,
    strip_images,
    strip_links,
)


def test_slugify():
    assert slugify("Olá Mundo!") == "ola-mundo"
    assert slugify("Section 1.1") == "section-11"


def test_shift_headings_basic():
    md = "# A\n\n## B\n\ntext"
    assert shift_headings(md, 1) == "## A\n\n### B\n\ntext"
    assert shift_headings(md, -1) == "# A\n\n# B\n\ntext"


def test_shift_headings_skips_code():
    md = "# A\n\n```\n# fake\n```\n"
    out = shift_headings(md, 1)
    assert "## A" in out
    assert "# fake" in out  # não foi alterado dentro do bloco


def test_normalize_unifies_lists():
    md = "* a\n* b\n+ c"
    out = normalize(md)
    assert "- a" in out and "- b" in out and "- c" in out


def test_strip_html_links_images():
    md = "Hi <b>there</b> [x](u) ![a](u.png)"
    assert "<b>" not in strip_html(md)
    assert "[x](u)" not in strip_links(md)
    assert "x" in strip_links(md)
    assert "[a](u.png)" not in strip_images(md)
    assert "a" in strip_images(md)
    assert strip_images("![a](u.png)", keep_alt=False).strip() == ""


def test_strip_code_blocks():
    md = "before\n\n```\nx = 1\n```\n\nafter"
    out = strip_code_blocks(md)
    assert "x = 1" not in out
    assert "before" in out and "after" in out


def test_md_to_plain():
    md = "# Title\n\n**bold** and *italic* and [link](u)\n\n- item"
    out = md_to_plain(md)
    assert out.startswith("Title")
    assert "**" not in out and "*" not in out
    assert "[link]" not in out and "link" in out
    assert "- item" not in out
    assert "item" in out
