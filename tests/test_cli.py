import json
from pathlib import Path

from markdown_hero.cli import main


def test_cli_strip(tmp_path: Path, capsys):
    src = tmp_path / "in.md"
    src.write_text("**Olá**, mundo!", encoding="utf-8")
    rc = main(["strip", str(src)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "ola mundo" in out


def test_cli_chunk(tmp_path: Path, capsys):
    src = tmp_path / "in.md"
    src.write_text("# A\n\ntexto\n\n# B\n\noutro\n", encoding="utf-8")
    rc = main(["chunk", str(src), "--purpose", "rag"])
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert isinstance(payload, list) and len(payload) >= 2


def test_cli_append_and_break(tmp_path: Path, capsys):
    a = tmp_path / "a.md"
    b = tmp_path / "b.md"
    a.write_text("# A\n\ncontent a", encoding="utf-8")
    b.write_text("# B\n\ncontent b", encoding="utf-8")
    out = tmp_path / "merged.md"
    assert main(["append", str(a), str(b), "-o", str(out)]) == 0
    assert out.exists()
    capsys.readouterr()

    out_dir = tmp_path / "parts"
    assert main(["break", str(out), "## B", "--output-dir", str(out_dir), "--include", "after"]) == 0


def test_cli_lint_and_stats(tmp_path: Path, capsys):
    src = tmp_path / "in.md"
    src.write_text("# A\n\n### C\n\ntexto", encoding="utf-8")
    main(["lint", str(src)])
    out = capsys.readouterr().out
    assert "heading-skip" in out

    main(["stats", str(src)])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert "words" in payload and "reading_time_min" in payload
