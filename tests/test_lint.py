from markdown_hero import lint, reading_time, word_count


def test_detects_heading_skip():
    md = "# A\n\n### C\n"
    issues = lint(md)
    assert any(i.rule == "heading-skip" for i in issues)


def test_detects_duplicate_anchor():
    md = "# Intro\n\n## Detalhes\n\n## Detalhes\n"
    issues = lint(md)
    assert any(i.rule == "duplicate-anchor" for i in issues)


def test_detects_unclosed_fence():
    md = "# T\n\n```python\nprint(1)\n"
    issues = lint(md)
    assert any(i.rule == "unclosed-fence" and i.severity == "error" for i in issues)


def test_word_count_ignores_code():
    md = "Hello world.\n\n```\ncode here\n```\n"
    assert word_count(md, ignore_code=True) == 2


def test_reading_time():
    md = " ".join(["palavra"] * 400)
    assert abs(reading_time(md, wpm=200) - 2.0) < 0.01


def test_detects_empty_link_text():
    md = "see [](https://x.com) for details"
    issues = lint(md)
    assert any(i.rule == "empty-link-text" for i in issues)


def test_detects_empty_link_url():
    md = "see [docs](#) and [more]() for details"
    issues = lint(md)
    rules = [i.rule for i in issues]
    assert rules.count("empty-link-url") >= 1
