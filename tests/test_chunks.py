from markdown_hero import extract_chunks


def test_structural_split():
    md = (
        "# Intro\n\npequeno texto\n\n"
        "# Capítulo 1\n\ntexto do capítulo 1\n\n"
        "## Seção 1.1\n\nsubseção\n\n"
        "# Capítulo 2\n\noutro texto\n"
    )
    chunks = extract_chunks(md, strategy="structural", max_tokens=500)
    titles = [c.heading_path[-1] if c.heading_path else None for c in chunks]
    # Garantir que cada heading principal vira (pelo menos) um chunk com path correto.
    assert "Intro" in titles
    assert "Capítulo 1" in titles
    assert "Seção 1.1" in titles
    assert "Capítulo 2" in titles


def test_heading_path_breadcrumb():
    md = "# A\n\n## B\n\ntexto longo\n\n### C\n\nmais texto\n"
    chunks = extract_chunks(md, strategy="structural", max_tokens=500)
    paths = [c.heading_path for c in chunks]
    # 'C' deve ter A → B → C
    assert ["A", "B", "C"] in paths


def test_oversized_chunk_flagged():
    big = "palavra " * 5000
    md = f"# Big\n\n{big}\n"
    chunks = extract_chunks(md, strategy="structural", max_tokens=10)
    assert any(c.oversized for c in chunks)


def test_hybrid_subsplits_large_section():
    big = ("Frase. " * 50 + "\n\n") * 20
    md = f"# Doc\n\n{big}"
    chunks = extract_chunks(md, strategy="hybrid", max_tokens=80, overlap=10)
    assert len(chunks) > 1
    assert all(c.heading_path == ["Doc"] for c in chunks)


def test_purpose_rag_uses_overlap():
    md = "# T\n\n" + "\n\n".join("Parágrafo " + str(i) for i in range(50))
    chunks = extract_chunks(md, purpose="rag", max_tokens=40)
    assert len(chunks) > 1


def test_indices_are_assigned():
    md = "# A\n\nx\n\n# B\n\ny\n"
    chunks = extract_chunks(md)
    assert [c.index for c in chunks] == list(range(len(chunks)))
