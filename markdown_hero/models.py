"""Public dataclasses returned by markdown_hero functions.

Only data containers live here. Logic and parsing belong to the modules
that produce these structures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class Link:
    """An inline, reference, or autolink reference found in Markdown."""

    text: str
    url: str
    title: str | None = None
    line: int = 0
    type: Literal["inline", "reference", "autolink"] = "inline"


@dataclass(frozen=True)
class Image:
    """An inline image reference found in Markdown."""

    alt: str
    url: str
    title: str | None = None
    line: int = 0


@dataclass(frozen=True)
class Table:
    """A GFM-style table, ready for rendering or row-by-row processing."""

    headers: list[str]
    rows: list[list[str]]
    line: int = 0
    alignments: list[Literal["left", "center", "right", "default"]] = field(default_factory=list)


@dataclass(frozen=True)
class CodeBlock:
    """A fenced code block with its info-string language tag."""

    code: str
    language: str | None = None
    line: int = 0
    fenced: bool = True


@dataclass(frozen=True)
class Heading:
    """An ATX heading with the slugified anchor used for linking."""

    level: int
    text: str
    line: int = 0
    anchor: str = ""


@dataclass
class Chunk:
    """A chunk produced by :func:`markdown_hero.extract_chunks`.

    Attributes:
        text: Chunk content as text.
        heading_path: Breadcrumb of headings the chunk lives under,
            from outermost to innermost.
        char_start: Inclusive character offset in the source document.
        char_end: Exclusive character offset in the source document.
        token_count: Token count according to the active tokenizer.
        type: Dominant content type of the chunk.
        source: Optional document identifier passed to ``extract_chunks``.
        index: Zero-based position in the returned list.
        oversized: True when the chunk exceeds the requested
            ``max_tokens`` and could not be subdivided further.
        metadata: Free-form mapping for downstream consumers.
    """

    text: str
    heading_path: list[str] = field(default_factory=list)
    char_start: int = 0
    char_end: int = 0
    token_count: int = 0
    type: Literal["prose", "code", "table", "list", "mixed"] = "prose"
    source: str | None = None
    index: int = 0
    oversized: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
