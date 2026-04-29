"""Structural extraction from Markdown content.

Public functions in this module never mutate their input. They return
plain dataclasses defined in :mod:`markdown_hero.models`. They do *not*
provide rendering or transformation — see :mod:`markdown_hero.transform`
for that.
"""

from __future__ import annotations

import re
from typing import Any, cast

import yaml

from .errors import FrontmatterError
from .models import CodeBlock, Heading, Image, Link, Table
from .transform import slugify

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
_HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$", re.MULTILINE)
_FENCED_RE = re.compile(
    r"^(?P<fence>```|~~~)(?P<lang>[^\n`]*)\n(?P<code>.*?)^(?P=fence)\s*$",
    re.MULTILINE | re.DOTALL,
)
_LINK_RE = re.compile(
    r"(?<!\!)\[(?P<text>(?:[^\[\]]|\[[^\[\]]*\])*)\]\((?P<url>[^)\s]*)(?:\s+\"(?P<title>[^\"]*)\")?\)"
)
_AUTOLINK_RE = re.compile(r"<(?P<url>https?://[^>\s]+)>")
_IMAGE_RE = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<url>[^)\s]+)(?:\s+\"(?P<title>[^\"]*)\")?\)")


def extract_frontmatter(md: str) -> dict[str, Any]:
    """Parse the YAML frontmatter at the top of a Markdown document.

    A frontmatter block must start at the very first line of ``md`` and
    is delimited by ``---`` lines. When no frontmatter is found, an empty
    dictionary is returned. When a frontmatter block is present but
    cannot be parsed as a YAML mapping, ``FrontmatterError`` is raised
    so that the caller can react explicitly instead of silently losing
    metadata.

    Args:
        md: Full Markdown content as text.

    Returns:
        A dictionary with the parsed frontmatter, or ``{}`` when no
        frontmatter block is present.

    Raises:
        FrontmatterError: When the YAML inside the delimiters is invalid
            or does not parse to a mapping.
    """
    m = _FRONTMATTER_RE.match(md)
    if not m:
        return {}
    try:
        data: Any = yaml.safe_load(m.group(1))
    except yaml.YAMLError as exc:
        raise FrontmatterError(f"invalid YAML in frontmatter: {exc}") from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise FrontmatterError(f"frontmatter must be a YAML mapping, got {type(data).__name__}")
    # yaml.safe_load returns Any; the runtime check above narrows to dict.
    return cast("dict[str, Any]", data)


def remove_frontmatter(md: str) -> tuple[str, dict[str, Any]]:
    """Split a Markdown document into body text and frontmatter metadata.

    Args:
        md: Full Markdown content as text.

    Returns:
        A tuple ``(body, metadata)`` where ``body`` is the Markdown with
        the frontmatter block stripped and ``metadata`` is the parsed
        YAML mapping (``{}`` when no frontmatter is present).

    Raises:
        FrontmatterError: When the YAML inside the delimiters is invalid
            or does not parse to a mapping.
    """
    m = _FRONTMATTER_RE.match(md)
    if not m:
        return md, {}
    fm = extract_frontmatter(md)
    return md[m.end() :], fm


def _strip_for_scan(md: str) -> str:
    """Replace fenced code blocks with blank placeholders, preserving line offsets."""
    out = []
    last = 0
    for m in _FENCED_RE.finditer(md):
        out.append(md[last : m.start()])
        # Keep line breaks so downstream line numbers stay correct.
        out.append("\n" * md[m.start() : m.end()].count("\n"))
        last = m.end()
    out.append(md[last:])
    return "".join(out)


def extract_headings(md: str) -> list[Heading]:
    """Return every ATX heading in the document, in source order.

    Headings inside fenced code blocks are ignored. The ``anchor``
    attribute is the GitHub-style slug derived from the heading text.

    Args:
        md: Full Markdown content as text.

    Returns:
        A list of ``Heading`` instances. Empty when the document has no
        headings.
    """
    body, _ = remove_frontmatter(md)
    scan = _strip_for_scan(body)
    headings: list[Heading] = []
    for m in _HEADING_RE.finditer(scan):
        text = m.group(2).strip()
        line = scan.count("\n", 0, m.start()) + 1
        headings.append(
            Heading(
                level=len(m.group(1)),
                text=text,
                line=line,
                anchor=slugify(text),
            )
        )
    return headings


def extract_links(md: str) -> list[Link]:
    """Return all inline and autolink links from the document.

    Reference-style links and links inside fenced code blocks are not
    returned. ``Link.type`` indicates the kind of link found.

    Args:
        md: Full Markdown content as text.

    Returns:
        A list of ``Link`` instances in source order with line numbers
        starting at 1.
    """
    body, _ = remove_frontmatter(md)
    scan = _strip_for_scan(body)
    out: list[Link] = []
    for m in _LINK_RE.finditer(scan):
        line = scan.count("\n", 0, m.start()) + 1
        out.append(
            Link(
                text=m.group("text"),
                url=m.group("url"),
                title=m.group("title"),
                line=line,
                type="inline",
            )
        )
    for m in _AUTOLINK_RE.finditer(scan):
        line = scan.count("\n", 0, m.start()) + 1
        url = m.group("url")
        out.append(Link(text=url, url=url, line=line, type="autolink"))
    return out


def extract_images(md: str) -> list[Image]:
    """Return every inline image reference from the document.

    Images inside fenced code blocks are ignored.

    Args:
        md: Full Markdown content as text.

    Returns:
        A list of ``Image`` instances in source order.
    """
    body, _ = remove_frontmatter(md)
    scan = _strip_for_scan(body)
    out: list[Image] = []
    for m in _IMAGE_RE.finditer(scan):
        line = scan.count("\n", 0, m.start()) + 1
        out.append(
            Image(
                alt=m.group("alt"),
                url=m.group("url"),
                title=m.group("title"),
                line=line,
            )
        )
    return out


def extract_code_blocks(md: str, *, language: str | None = None) -> list[CodeBlock]:
    """Return fenced code blocks, optionally filtered by language tag.

    Args:
        md: Full Markdown content as text.
        language: When provided, only blocks whose info string matches
            this value exactly are returned. Pass ``None`` to return
            every block.

    Returns:
        A list of ``CodeBlock`` instances in source order. Empty when no
        block matches.
    """
    body, _ = remove_frontmatter(md)
    out: list[CodeBlock] = []
    for m in _FENCED_RE.finditer(body):
        lang = m.group("lang").strip() or None
        if language and (lang or "") != language:
            continue
        line = body.count("\n", 0, m.start()) + 1
        out.append(CodeBlock(code=m.group("code"), language=lang, line=line, fenced=True))
    return out


def extract_tables(md: str) -> list[Table]:
    """Return GFM tables found in the document.

    The function recognizes pipe-delimited tables with a separator row.
    Tables inside fenced code blocks are ignored. Cell content is kept
    verbatim except for surrounding whitespace, which is trimmed.

    Args:
        md: Full Markdown content as text.

    Returns:
        A list of ``Table`` instances. Each ``Table`` carries headers,
        body rows, alignment per column, and the source line number of
        the header row.
    """
    body, _ = remove_frontmatter(md)
    scan = _strip_for_scan(body)
    lines = scan.split("\n")
    tables: list[Table] = []
    i = 0
    sep_re = re.compile(r"^\s*\|?\s*:?-{3,}:?(?:\s*\|\s*:?-{3,}:?)*\s*\|?\s*$")
    while i < len(lines) - 1:
        header = lines[i]
        sep = lines[i + 1]
        if "|" in header and sep_re.match(sep):
            headers = _split_row(header)
            aligns = _parse_align(sep)
            rows: list[list[str]] = []
            j = i + 2
            while j < len(lines) and "|" in lines[j] and lines[j].strip():
                rows.append(_split_row(lines[j]))
                j += 1
            tables.append(Table(headers=headers, rows=rows, line=i + 1, alignments=aligns))
            i = j
        else:
            i += 1
    return tables


def _split_row(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def _parse_align(sep: str) -> list[str]:
    out: list[str] = []
    for part in _split_row(sep):
        left = part.startswith(":")
        right = part.endswith(":")
        if left and right:
            out.append("center")
        elif right:
            out.append("right")
        elif left:
            out.append("left")
        else:
            out.append("default")
    return out


def build_toc(md: str, *, max_depth: int = 3) -> str:
    """Build a Markdown table of contents from the document headings.

    Each entry is a bullet with a relative link to the heading anchor.
    Indentation reflects heading level.

    Args:
        md: Full Markdown content as text.
        max_depth: Largest heading level to include. Defaults to ``3``,
            so H1, H2, and H3 are listed.

    Returns:
        A Markdown string with one bullet per heading. Returns ``""``
        when the document has no qualifying headings.
    """
    out: list[str] = []
    for h in extract_headings(md):
        if h.level > max_depth:
            continue
        indent = "  " * (h.level - 1)
        out.append(f"{indent}- [{h.text}](#{h.anchor})")
    return "\n".join(out)
