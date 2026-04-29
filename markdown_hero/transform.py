"""Transformations that take Markdown in and return Markdown (or plain text).

Functions here are pure: no IO, no mutation of input. Code blocks are
preserved verbatim so technical content is never rewritten.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Callable

_RE_FENCED = re.compile(r"^(```|~~~)[^\n]*\n.*?^\1\s*$", re.MULTILINE | re.DOTALL)
_RE_INLINE_CODE = re.compile(r"`[^`\n]*`")
_RE_HEADING = re.compile(r"^(\s{0,3})(#{1,6})(\s+)", re.MULTILINE)
_RE_HTML = re.compile(r"<[^>\n]+>")
_RE_IMAGE = re.compile(r"!\[([^\]]*)\]\([^)]*\)")
_RE_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")


def slugify(text: str) -> str:
    """Convert arbitrary text into a GitHub/Pandoc-compatible slug.

    Diacritics are removed via NFKD, the result is lowercased, every
    non-word character is dropped, and runs of whitespace collapse to a
    single hyphen. Surrounding hyphens are trimmed.

    Args:
        text: Arbitrary string, typically heading text.

    Returns:
        A lowercase ASCII slug suitable for a URL fragment. May be empty
        when ``text`` contains no word characters.

    Example:
        >>> slugify("Olá Mundo!")
        'ola-mundo'
    """
    s = unicodedata.normalize("NFKD", text)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"\s+", "-", s).strip("-")
    return s


def shift_headings(md: str, by: int) -> str:
    """Shift every ATX heading by a given number of levels.

    Positive values demote headings (H1 -> H2 with ``by=1``), negative
    values promote them. Result levels are clamped to the ``[1, 6]``
    range. Content inside fenced code blocks is preserved verbatim, so a
    ``# fake`` line within a code block is not modified.

    Args:
        md: Full Markdown content as text.
        by: Number of levels to add to each heading. ``0`` returns the
            input unchanged.

    Returns:
        The Markdown content with adjusted heading levels.

    Example:
        >>> shift_headings("# A\\n## B", 1)
        '## A\\n### B'
    """
    if by == 0:
        return md

    def _process(chunk: str) -> str:
        def repl(m: re.Match[str]) -> str:
            new_level = max(1, min(6, len(m.group(2)) + by))
            return f"{m.group(1)}{'#' * new_level}{m.group(3)}"

        return _RE_HEADING.sub(repl, chunk)

    return _apply_outside_code(md, _process)


def _apply_outside_code(md: str, fn: Callable[[str], str]) -> str:
    """Apply ``fn`` to every region of ``md`` that is not inside a fenced code block."""
    out: list[str] = []
    last = 0
    for m in _RE_FENCED.finditer(md):
        out.append(fn(md[last : m.start()]))
        out.append(m.group(0))
        last = m.end()
    out.append(fn(md[last:]))
    return "".join(out)


def normalize(
    md: str,
    *,
    unify_lists: bool = True,
    trim_trailing: bool = True,
    collapse_blank_lines: bool = True,
) -> str:
    """Normalize whitespace and list markers in a Markdown document.

    Code blocks are preserved untouched. The function does not change
    heading levels, link targets, or any semantic content.

    Args:
        md: Full Markdown content as text.
        unify_lists: When True (default), ``*`` and ``+`` list markers
            are rewritten to ``-`` outside code blocks.
        trim_trailing: When True (default), trailing whitespace is
            removed from every line.
        collapse_blank_lines: When True (default), three or more
            consecutive blank lines collapse to two.

    Returns:
        The normalized Markdown text.
    """
    s = md
    if trim_trailing:
        s = "\n".join(line.rstrip() for line in s.split("\n"))
    if unify_lists:
        s = _apply_outside_code(
            s,
            lambda x: re.sub(r"^(\s*)[*+](\s+)", r"\1-\2", x, flags=re.MULTILINE),
        )
    if collapse_blank_lines:
        s = re.sub(r"\n{3,}", "\n\n", s)
    return s


def strip_html(md: str) -> str:
    """Remove inline HTML tags from the document while preserving code blocks.

    Args:
        md: Full Markdown content as text.

    Returns:
        Markdown content without HTML tags.
    """
    return _apply_outside_code(md, lambda x: _RE_HTML.sub("", x))


def strip_images(md: str, *, keep_alt: bool = True) -> str:
    """Remove image references from the document.

    Args:
        md: Full Markdown content as text.
        keep_alt: When True (default), the alt text of each image is
            kept inline. When False, the entire image reference is
            removed.

    Returns:
        Markdown content with image syntax removed.
    """
    repl = r"\1" if keep_alt else ""
    return _apply_outside_code(md, lambda x: _RE_IMAGE.sub(repl, x))


def strip_links(md: str, *, keep_text: bool = True) -> str:
    """Remove inline links from the document.

    Args:
        md: Full Markdown content as text.
        keep_text: When True (default), the visible link text is kept
            inline. When False, the link is removed entirely.

    Returns:
        Markdown content with link syntax removed.
    """
    repl = r"\1" if keep_text else ""
    return _apply_outside_code(md, lambda x: _RE_LINK.sub(repl, x))


def strip_code_blocks(md: str, *, keep_inline: bool = False) -> str:
    """Remove fenced code blocks (and optionally inline code) from the document.

    Args:
        md: Full Markdown content as text.
        keep_inline: When True, inline code spans (``` `like this` ```)
            are kept. When False (default), they are also removed.

    Returns:
        Markdown content without code regions.
    """
    s = _RE_FENCED.sub("", md)
    if not keep_inline:
        s = _RE_INLINE_CODE.sub("", s)
    return s


def md_to_plain(md: str) -> str:
    """Convert Markdown to plain text preserving paragraph structure.

    Lighter than :func:`markdown_hero.strip`: it removes Markdown markup
    (headings, lists, emphasis, links, images, HTML, code) but keeps
    paragraph breaks and the original casing.

    Args:
        md: Full Markdown content as text.

    Returns:
        Plain text with double newlines between paragraphs.
    """
    s = strip_code_blocks(md, keep_inline=True)
    s = _RE_INLINE_CODE.sub(lambda m: m.group(0).strip("`"), s)
    s = strip_html(s)
    s = strip_images(s, keep_alt=True)
    s = strip_links(s, keep_text=True)
    s = re.sub(r"^(\s{0,3})#{1,6}\s+", "", s, flags=re.MULTILINE)
    s = re.sub(r"^\s{0,3}>\s?", "", s, flags=re.MULTILINE)
    s = re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+", "", s, flags=re.MULTILINE)
    s = re.sub(r"\*\*|__|\*|_|~~", "", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()
