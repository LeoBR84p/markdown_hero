from markdown_hero import strip


def test_strip_example_from_spec():
    md = (
        "**Compromisso entre média e máximo.** \n"
        "p=1 (média aritmética ponderada) ignora concentração de risco em uma dimensão; \n"
        "p=∞ (máximo) ignora as demais. \n"
        "p=2 captura ambos: penaliza concentração mas não descarta o conjunto."
    )
    expected = (
        "compromisso entre media e maximo p1 media aritmetica ponderada "
        "ignora concentracao de risco em uma dimensao p maximo ignora as "
        "demais p2 captura ambos penaliza concentracao mas nao descarta o conjunto"
    )
    assert strip(md) == expected


def test_strip_preserves_math_when_requested():
    md = "p=1, p=2, p<=3 são valores válidos."
    out = strip(md, keep_math=True)
    assert "p=1" in out
    assert "p=2" in out
    assert "<=3" in out


def test_strip_removes_numbers_when_requested():
    md = "Em 2024 tivemos 15% de crescimento."
    out = strip(md, keep_numbers=False)
    assert "2024" not in out
    assert "15" not in out
    assert "crescimento" in out


def test_strip_handles_links_images_code_html():
    md = (
        "Veja [docs](https://example.com) e ![alt](img.png).\n"
        "Use `os.path` ou\n"
        "```python\nprint('x')\n```\n"
        "<b>HTML</b> também."
    )
    out = strip(md)
    assert "docs" in out
    assert "https" not in out
    assert "alt" in out
    assert "html" in out
    assert "print" not in out  # bloco de código removido
    assert "os" not in out or "path" not in out  # inline code removido (tornado espaço)


def test_strip_removes_diacritics_for_any_language():
    assert strip("Crème brûlée — Zürich naïve") == "creme brulee zurich naive"


def test_strip_keeps_latex_text_when_requested():
    out = strip("A formula $x = y + 1$ aqui", keep_latex_text=True)
    assert "y" in out and "1" in out


def test_strip_handles_headings_lists_quotes():
    md = "# Título\n\n- item 1\n- item 2\n\n> citação"
    out = strip(md)
    assert "titulo" in out
    assert "item 1" in out and "item 2" in out
    assert "citacao" in out


def test_strip_empty():
    assert strip("") == ""
    assert strip("   \n\n  ") == ""
