"""Structural chunking for Markdown documents.

The public entry point is :func:`extract_chunks`. The output is a list
of :class:`Chunk` objects with rich metadata that downstream consumers
(RAG indexers, fine-tuning pipelines, summarizers) can use directly.
"""
from __future__ import annotations

import re
from dataclasses import replace
from typing import Any, Callable, Literal

from .extract import remove_frontmatter
from .models import Chunk

Purpose = Literal["rag", "finetune", "summary", "generic"]
Strategy = Literal["structural", "semantic", "fixed", "hybrid"]
ChunkType = Literal["prose", "code", "table", "list", "mixed"]
Tokenizer = Callable[[str], int]

_RE_FENCED = re.compile(r"^(```|~~~)[^\n]*\n.*?^\1\s*$", re.MULTILINE | re.DOTALL)
_RE_HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$", re.MULTILINE)


def _default_tokenizer() -> Callable[[str], int]:
    """Tokenizer padrão: tiktoken se instalado, caso contrário aproximação."""
    try:
        import tiktoken  # type: ignore

        enc = tiktoken.get_encoding("cl100k_base")
        return lambda s: len(enc.encode(s))
    except Exception:
        # ~4 chars/token em inglês, ~3 em português; usamos 3.5 como média.
        return lambda s: max(1, int(len(s) / 3.5))


def _purpose_defaults(purpose: Purpose, max_tokens: int, overlap: int) -> tuple[int, int, Strategy]:
    """Ajusta defaults conforme o propósito."""
    if purpose == "rag":
        return max_tokens or 512, overlap or 64, "hybrid"
    if purpose == "finetune":
        return max_tokens or 1024, 0, "structural"
    if purpose == "summary":
        return max_tokens or 2048, 0, "structural"
    return max_tokens or 512, overlap or 0, "structural"


def extract_chunks(
    md: str,
    *,
    strategy: Strategy | None = None,
    purpose: Purpose = "generic",
    max_tokens: int = 0,
    overlap: int = 0,
    tokenizer: Callable[[str], int] | None = None,
    source: str | None = None,
    min_tokens: int = 0,
) -> list[Chunk]:
    """Split a Markdown document into chunks with rich structural metadata.

    The default behavior is selected by ``purpose``: ``rag`` uses a
    hybrid strategy with overlap (good for retrieval), ``finetune`` and
    ``summary`` keep section-aligned chunks without overlap, and
    ``generic`` defaults to a plain structural split. Pass ``strategy``
    to override.

    Strategies:
        - ``structural``: split by heading hierarchy; each section
          becomes one chunk and the breadcrumb is preserved.
        - ``semantic``: group paragraphs up to ``max_tokens`` regardless
          of headings.
        - ``fixed``: hard token-based slicing (rarely useful by itself).
        - ``hybrid``: structural split, then sub-divide oversized
          sections by paragraph while keeping overlap inside the same
          section only.

    Fenced code blocks and tables are never split mid-content. A single
    block that exceeds ``max_tokens`` becomes a chunk with
    ``oversized=True``.

    Args:
        md: Full Markdown content as text.
        strategy: Override the strategy chosen by ``purpose``.
        purpose: Default profile. One of ``rag``, ``finetune``,
            ``summary``, ``generic``.
        max_tokens: Override the default token budget per chunk. Pass
            ``0`` to use the default for the selected ``purpose``.
        overlap: Token overlap between adjacent chunks of the same
            section. Ignored across heading boundaries.
        tokenizer: Custom token-counting function. When omitted, uses
            ``tiktoken`` (cl100k_base) if installed, otherwise an
            approximation of ``len(text) / 3.5`` tokens.
        source: Optional identifier (e.g. file path) recorded on every
            returned chunk for downstream traceability.
        min_tokens: When greater than zero, structural sections smaller
            than this threshold are merged into the previous chunk.

    Returns:
        A list of ``Chunk`` instances, each with ``heading_path``,
        offsets, token count, and a content type classification.

    Raises:
        FrontmatterError: When the document's frontmatter is malformed.
    """
    if not md.strip():
        return []

    tok = tokenizer or _default_tokenizer()
    body, _ = remove_frontmatter(md)
    max_tokens, overlap, default_strategy = _purpose_defaults(purpose, max_tokens, overlap)
    strategy = strategy or default_strategy

    chunks: list[Chunk]
    if strategy == "fixed":
        chunks = _chunk_fixed(body, max_tokens, overlap, tok)
    elif strategy == "semantic":
        chunks = _chunk_semantic(body, max_tokens, overlap, tok)
    else:
        sections = _split_sections(body)
        chunks = []
        for sec in sections:
            sec_text = sec["text"]
            sec_tokens = tok(sec_text)
            base = Chunk(
                text=sec_text.strip(),
                heading_path=sec["path"],
                char_start=sec["start"],
                char_end=sec["end"],
                token_count=sec_tokens,
                type=_classify(sec_text),
                source=source,
            )
            if strategy == "structural" or sec_tokens <= max_tokens:
                if sec_tokens > max_tokens:
                    base = replace(base, oversized=True)
                if sec_tokens >= min_tokens or not chunks:
                    chunks.append(base)
                else:
                    # mescla seções minúsculas com a anterior.
                    prev = chunks[-1]
                    chunks[-1] = replace(
                        prev,
                        text=(prev.text + "\n\n" + base.text).strip(),
                        char_end=base.char_end,
                        token_count=prev.token_count + sec_tokens,
                        type="mixed",
                    )
            else:
                chunks.extend(
                    _subsplit_section(base, max_tokens, overlap, tok)
                )

    for i, c in enumerate(chunks):
        chunks[i] = replace(c, index=i)
    return chunks


def _classify(text: str) -> ChunkType:
    if _RE_FENCED.search(text):
        return "code"
    stripped = text.strip()
    if stripped.startswith("|") and "|" in stripped:
        return "table"
    if re.match(r"^\s*(?:[-*+]|\d+[.)])\s+", stripped):
        return "list"
    return "prose"


def _split_sections(body: str) -> list[dict[str, Any]]:
    """Split the body into per-heading sections preserving the hierarchical path."""
    headings = list(_RE_HEADING.finditer(_mask_code(body)))
    if not headings:
        return [{"text": body, "path": [], "start": 0, "end": len(body)}]

    sections: list[dict[str, Any]] = []
    path: list[tuple[int, str]] = []  # (level, text)
    # Texto antes do primeiro heading.
    if headings[0].start() > 0:
        intro = body[: headings[0].start()].strip()
        if intro:
            sections.append({"text": intro, "path": [], "start": 0, "end": headings[0].start()})

    for i, m in enumerate(headings):
        level = len(m.group(1))
        title = m.group(2).strip()
        path = [(lvl, t) for lvl, t in path if lvl < level]
        path.append((level, title))
        end = headings[i + 1].start() if i + 1 < len(headings) else len(body)
        text = body[m.start():end]
        sections.append({
            "text": text,
            "path": [t for _, t in path],
            "start": m.start(),
            "end": end,
        })
    return sections


def _mask_code(body: str) -> str:
    """Substitui blocos de código por linhas em branco preservando offsets."""
    out = []
    last = 0
    for m in _RE_FENCED.finditer(body):
        out.append(body[last:m.start()])
        out.append("\n" * m.group(0).count("\n"))
        last = m.end()
    out.append(body[last:])
    return "".join(out)


def _subsplit_section(
    base: Chunk, max_tokens: int, overlap: int, tok: Tokenizer
) -> list[Chunk]:
    """Sub-divide uma seção grande por parágrafo, respeitando blocos de código."""
    pieces = _split_preserving_blocks(base.text)
    chunks: list[Chunk] = []
    buf: list[str] = []
    buf_tokens = 0
    cursor = base.char_start
    for piece in pieces:
        ptok = tok(piece)
        if buf and buf_tokens + ptok > max_tokens:
            text = "\n\n".join(buf).strip()
            chunks.append(replace(
                base,
                text=text,
                char_start=cursor,
                char_end=cursor + len(text),
                token_count=buf_tokens,
                type=_classify(text),
            ))
            cursor += len(text)
            if overlap > 0 and chunks:
                buf, buf_tokens = _make_overlap(buf, overlap, tok)
            else:
                buf, buf_tokens = [], 0
        if ptok > max_tokens:
            # bloco isolado maior que o máximo: vira chunk único oversized.
            if buf:
                text = "\n\n".join(buf).strip()
                chunks.append(replace(
                    base, text=text, char_start=cursor,
                    char_end=cursor + len(text),
                    token_count=buf_tokens, type=_classify(text),
                ))
                cursor += len(text)
                buf, buf_tokens = [], 0
            chunks.append(replace(
                base, text=piece.strip(), char_start=cursor,
                char_end=cursor + len(piece),
                token_count=ptok, type=_classify(piece), oversized=True,
            ))
            cursor += len(piece)
            continue
        buf.append(piece)
        buf_tokens += ptok
    if buf:
        text = "\n\n".join(buf).strip()
        chunks.append(replace(
            base, text=text, char_start=cursor,
            char_end=cursor + len(text),
            token_count=buf_tokens, type=_classify(text),
        ))
    return chunks


def _make_overlap(
    buf: list[str], overlap_tokens: int, tok: Tokenizer
) -> tuple[list[str], int]:
    """Mantém o final do buffer anterior como overlap."""
    keep: list[str] = []
    total = 0
    for piece in reversed(buf):
        ptok = tok(piece)
        if total + ptok > overlap_tokens:
            break
        keep.insert(0, piece)
        total += ptok
    return keep, total


def _split_preserving_blocks(text: str) -> list[str]:
    """Split por parágrafo preservando blocos fenced e tabelas."""
    parts: list[str] = []
    last = 0
    for m in _RE_FENCED.finditer(text):
        before = text[last:m.start()]
        parts.extend(p for p in re.split(r"\n\s*\n", before) if p.strip())
        parts.append(m.group(0))
        last = m.end()
    tail = text[last:]
    parts.extend(p for p in re.split(r"\n\s*\n", tail) if p.strip())
    return parts


def _chunk_fixed(body: str, max_tokens: int, overlap: int, tok: Tokenizer) -> list[Chunk]:
    """Corte rígido por tokens (palavras, na ausência de tokenizer real)."""
    words = body.split()
    chunks: list[Chunk] = []
    i = 0
    while i < len(words):
        text = ""
        j = i
        while j < len(words):
            candidate = (text + " " + words[j]).strip()
            if tok(candidate) > max_tokens and text:
                break
            text = candidate
            j += 1
        chunks.append(Chunk(
            text=text,
            heading_path=[],
            char_start=0,
            char_end=len(text),
            token_count=tok(text),
            type="prose",
        ))
        if j == i:
            j = i + 1
        if overlap > 0:
            i = max(j - max(1, overlap // 4), i + 1)
        else:
            i = j
    return chunks


def _chunk_semantic(body: str, max_tokens: int, overlap: int, tok: Tokenizer) -> list[Chunk]:
    pieces = _split_preserving_blocks(body)
    chunks: list[Chunk] = []
    buf: list[str] = []
    total = 0
    for p in pieces:
        ptok = tok(p)
        if buf and total + ptok > max_tokens:
            text = "\n\n".join(buf).strip()
            chunks.append(Chunk(
                text=text, token_count=total, type=_classify(text),
                char_start=0, char_end=len(text),
            ))
            if overlap > 0:
                buf, total = _make_overlap(buf, overlap, tok)
            else:
                buf, total = [], 0
        buf.append(p)
        total += ptok
    if buf:
        text = "\n\n".join(buf).strip()
        chunks.append(Chunk(
            text=text, token_count=total, type=_classify(text),
            char_start=0, char_end=len(text),
        ))
    return chunks
