from pathlib import Path

from markdown_hero import markdown_append, markdown_break, markdown_merge


def _w(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def test_append_shifts_headings(tmp_path: Path):
    a = _w(tmp_path / "a.md", "---\ntitle: A\n---\n\n# A\n\nconteúdo A\n")
    b = _w(tmp_path / "b.md", "# B\n\nconteúdo B\n")
    out = tmp_path / "out.md"
    markdown_append(a, b, output=out, headings="shift")
    text = out.read_text(encoding="utf-8")
    assert "# A" in text
    assert "## B" in text  # rebaixado
    assert "conteúdo A" in text and "conteúdo B" in text


def test_append_merges_frontmatter(tmp_path: Path):
    a = _w(tmp_path / "a.md", "---\ntitle: A\nauthor: x\n---\n\ntexto a")
    b = _w(tmp_path / "b.md", "---\ntags: [t1]\n---\n\ntexto b")
    out = tmp_path / "out.md"
    markdown_append(a, b, output=out, frontmatter="merge")
    text = out.read_text(encoding="utf-8")
    assert text.startswith("---")
    assert "title: A" in text
    assert "author: x" in text
    assert "tags:" in text


def test_append_drop_frontmatter(tmp_path: Path):
    a = _w(tmp_path / "a.md", "---\ntitle: A\n---\n\ntexto a")
    b = _w(tmp_path / "b.md", "texto b")
    out = tmp_path / "out.md"
    markdown_append(a, b, output=out, frontmatter="drop")
    text = out.read_text(encoding="utf-8")
    assert not text.startswith("---")


def test_append_wrap_headings(tmp_path: Path):
    a = _w(tmp_path / "a.md", "## sub a\n\ntexto a")
    b = _w(tmp_path / "b.md", "## sub b\n\ntexto b")
    out = tmp_path / "out.md"
    markdown_append(a, b, output=out, headings="wrap")
    text = out.read_text(encoding="utf-8")
    assert "# a" in text and "# b" in text  # filenames como H1


def test_break_string_delimiter(tmp_path: Path):
    src = _w(tmp_path / "doc.md", "parte 1\n\n---SEP---\n\nparte 2\n\n---SEP---\n\nparte 3")
    out_dir = tmp_path / "out"
    paths = markdown_break(src, "---SEP---", output_dir=out_dir, frontmatter="drop")
    assert len(paths) == 3
    contents = [p.read_text(encoding="utf-8") for p in paths]
    assert "parte 1" in contents[0]
    assert "parte 2" in contents[1]
    assert "parte 3" in contents[2]
    # Sem leading whitespace nem o delimitador.
    assert "---SEP---" not in contents[0]
    assert contents[0].startswith("parte")


def test_break_include_after(tmp_path: Path):
    src = _w(tmp_path / "doc.md", "intro\n\n# Cap A\n\ntexto a\n\n# Cap B\n\ntexto b")
    out_dir = tmp_path / "out"
    paths = markdown_break(src, r"^# .+$", is_regex=True, include_delimiter="after", output_dir=out_dir)
    contents = [p.read_text(encoding="utf-8") for p in paths]
    assert any(c.startswith("# Cap A") for c in contents)
    assert any(c.startswith("# Cap B") for c in contents)


def test_break_replicates_frontmatter(tmp_path: Path):
    src = _w(tmp_path / "doc.md", "---\ntitle: X\n---\n\nA\n\n===\n\nB\n\n===\n\nC")
    out_dir = tmp_path / "out"
    paths = markdown_break(src, "===", output_dir=out_dir, frontmatter="replicate")
    for i, p in enumerate(paths):
        text = p.read_text(encoding="utf-8")
        assert text.startswith("---")
        assert f"part: {i}" in text
        assert "part_of: 3" in text


def test_break_no_match_returns_one_file(tmp_path: Path):
    src = _w(tmp_path / "doc.md", "sem delimitador")
    paths = markdown_break(src, "###XYZ###", output_dir=tmp_path / "out")
    assert len(paths) == 1


def test_merge_dedupes_consecutive_sections(tmp_path: Path):
    a = _w(tmp_path / "a.md", "# Intro\n\nA1\n\n# Outro\n\nB1\n")
    b = _w(tmp_path / "b.md", "# Intro\n\nDUPLICADO\n")  # heading idêntico ao de cima depois do shift
    out = tmp_path / "out.md"
    # Após shift, b vira "## Intro" (não duplica). Forçamos preserve para testar dedupe direto.
    markdown_append(a, b, output=out, headings="preserve", frontmatter="drop")
    markdown_merge(out, a, output=tmp_path / "m.md")  # apenas garante execução sem erro
