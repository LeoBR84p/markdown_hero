"""Tipos de dados públicos."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class Link:
    text: str
    url: str
    title: str | None = None
    line: int = 0
    type: Literal["inline", "reference", "autolink"] = "inline"


@dataclass
class Image:
    alt: str
    url: str
    title: str | None = None
    line: int = 0


@dataclass
class Table:
    headers: list[str]
    rows: list[list[str]]
    line: int = 0
    alignments: list[Literal["left", "center", "right", "default"]] = field(default_factory=list)


@dataclass
class CodeBlock:
    code: str
    language: str | None = None
    line: int = 0
    fenced: bool = True


@dataclass
class Heading:
    level: int
    text: str
    line: int = 0
    anchor: str = ""


@dataclass
class Chunk:
    text: str
    heading_path: list[str] = field(default_factory=list)
    char_start: int = 0
    char_end: int = 0
    token_count: int = 0
    type: Literal["prose", "code", "table", "list", "mixed"] = "prose"
    source: str | None = None
    index: int = 0
    oversized: bool = False
    metadata: dict = field(default_factory=dict)
