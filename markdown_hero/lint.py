"""Lint rules and content metrics for Markdown documents.

This module produces structural diagnostics (skipped heading levels,
duplicate anchors, malformed code fences, empty links). It does not
attempt to validate prose or check link targets against the network.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from .extract import extract_headings, extract_links
from .transform import md_to_plain

Severity = Literal["info", "warning", "error"]


@dataclass(frozen=True)
class Issue:
    """A single lint diagnostic.

    Attributes:
        rule: Short identifier of the rule that produced the issue.
        message: Human-readable description of what was found.
        line: 1-based line number where the issue was detected.
        severity: One of ``"info"``, ``"warning"`` (default), or
            ``"error"``. Errors should typically fail CI pipelines.
    """

    rule: str
    message: str
    line: int
    severity: Severity = "warning"


def lint(md: str) -> list[Issue]:
    """Run structural lint rules over a Markdown document.

    Detected issues:

    - ``heading-skip``: a heading level jumps by more than one (e.g. H1
      directly to H3).
    - ``duplicate-anchor``: two headings produce the same anchor slug.
    - ``empty-link-text`` / ``empty-link-url``: malformed inline links.
    - ``unclosed-fence``: a code fence is opened but never closed.

    Args:
        md: Full Markdown content as text.

    Returns:
        A list of ``Issue`` objects in source order. Empty when the
        document passes every rule.
    """
    issues: list[Issue] = []
    headings = extract_headings(md)

    # Headings pulados (ex.: H1 → H3).
    prev = 0
    for h in headings:
        if prev and h.level > prev + 1:
            issues.append(
                Issue(
                    rule="heading-skip",
                    message=f"heading H{h.level} follows H{prev} (skipped one or more levels)",
                    line=h.line,
                    severity="warning",
                )
            )
        prev = h.level

    anchors: dict[str, int] = {}
    for h in headings:
        if h.anchor in anchors:
            issues.append(
                Issue(
                    rule="duplicate-anchor",
                    message=f"duplicate anchor '{h.anchor}' (also at line {anchors[h.anchor]})",
                    line=h.line,
                    severity="warning",
                )
            )
        else:
            anchors[h.anchor] = h.line

    for link in extract_links(md):
        if not link.text.strip():
            issues.append(Issue("empty-link-text", "link with empty text", link.line, "warning"))
        if not link.url.strip() or link.url.strip() == "#":
            issues.append(
                Issue("empty-link-url", "link with empty URL or only '#'", link.line, "warning")
            )

    fences = re.findall(r"^(?:```|~~~)", md, re.MULTILINE)
    if len(fences) % 2 != 0:
        last = list(re.finditer(r"^(?:```|~~~)", md, re.MULTILINE))[-1]
        line = md.count("\n", 0, last.start()) + 1
        issues.append(Issue("unclosed-fence", "fenced code block not closed", line, "error"))

    return issues


def word_count(md: str, *, ignore_code: bool = True) -> int:
    """Count textual words in a Markdown document.

    Args:
        md: Full Markdown content as text.
        ignore_code: When True (default), code blocks and inline code
            are excluded from the count.

    Returns:
        The number of whitespace-separated words.
    """
    text = md_to_plain(md) if ignore_code else md
    return len([w for w in re.split(r"\s+", text) if w])


def reading_time(md: str, *, wpm: int = 200) -> float:
    """Estimate reading time for a Markdown document.

    Args:
        md: Full Markdown content as text.
        wpm: Reading speed in words per minute. Defaults to ``200``,
            which approximates an average adult reader on prose.

    Returns:
        Estimated reading time in minutes.
    """
    return word_count(md) / max(1, wpm)
