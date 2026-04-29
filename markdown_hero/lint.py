"""Lint, validação e métricas para Markdown."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from .extract import extract_headings, extract_links
from .transform import md_to_plain

Severity = Literal["info", "warning", "error"]


@dataclass
class Issue:
    rule: str
    message: str
    line: int
    severity: Severity = "warning"


def lint(md: str) -> list[Issue]:
    """Lista problemas estruturais comuns: headings pulados, anchors duplicados,
    links sem texto, blocos fenced não fechados."""
    issues: list[Issue] = []
    headings = extract_headings(md)

    # Headings pulados (ex.: H1 → H3).
    prev = 0
    for h in headings:
        if prev and h.level > prev + 1:
            issues.append(Issue(
                rule="heading-skip",
                message=f"heading nível H{h.level} após H{prev} (pulou níveis)",
                line=h.line,
                severity="warning",
            ))
        prev = h.level

    # Anchors duplicados.
    anchors: dict[str, int] = {}
    for h in headings:
        if h.anchor in anchors:
            issues.append(Issue(
                rule="duplicate-anchor",
                message=f"âncora duplicada '{h.anchor}' (também em linha {anchors[h.anchor]})",
                line=h.line,
                severity="warning",
            ))
        else:
            anchors[h.anchor] = h.line

    # Links com texto vazio ou URL faltante.
    for link in extract_links(md):
        if not link.text.strip():
            issues.append(Issue("empty-link-text", "link com texto vazio", link.line, "warning"))
        if not link.url.strip() or link.url.strip() == "#":
            issues.append(Issue("empty-link-url", "link com URL vazia ou apenas '#'", link.line, "warning"))

    # Blocos fenced não fechados.
    fences = re.findall(r"^(?:```|~~~)", md, re.MULTILINE)
    if len(fences) % 2 != 0:
        last = list(re.finditer(r"^(?:```|~~~)", md, re.MULTILINE))[-1]
        line = md.count("\n", 0, last.start()) + 1
        issues.append(Issue("unclosed-fence", "bloco de código não fechado", line, "error"))

    return issues


def word_count(md: str, *, ignore_code: bool = True) -> int:
    """Contagem de palavras do conteúdo textual."""
    text = md_to_plain(md) if ignore_code else md
    return len([w for w in re.split(r"\s+", text) if w])


def reading_time(md: str, *, wpm: int = 200) -> float:
    """Estimativa de leitura em minutos."""
    return word_count(md) / max(1, wpm)
