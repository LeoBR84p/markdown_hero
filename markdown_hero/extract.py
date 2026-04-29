"""Funções de extração estrutural a partir de Markdown."""
from __future__ import annotations

import re
from typing import Any

import yaml

from .models import CodeBlock, Heading, Image, Link, Table

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
_HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$", re.MULTILINE)
_FENCED_RE = re.compile(
    r"^(?P<fence>```|~~~)(?P<lang>[^\n`]*)\n(?P<code>.*?)^(?P=fence)\s*$",
    re.MULTILINE | re.DOTALL,
)
_LINK_RE = re.compile(
    r"(?<!\!)\[(?P<text>(?:[^\[\]]|\[[^\[\]]*\])+)\]\((?P<url>[^)\s]+)(?:\s+\"(?P<title>[^\"]*)\")?\)"
)
_AUTOLINK_RE = re.compile(r"<(?P<url>https?://[^>\s]+)>")
_IMAGE_RE = re.compile(
    r"!\[(?P<alt>[^\]]*)\]\((?P<url>[^)\s]+)(?:\s+\"(?P<title>[^\"]*)\")?\)"
)


def _slugify_anchor(text: str) -> str:
    """Slug compatível com GitHub: minúsculas, espaços→'-', remove pontuação."""
    import unicodedata

    s = unicodedata.normalize("NFKD", text)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"\s+", "-", s).strip("-")
    return s


def extract_frontmatter(md: str) -> dict[str, Any]:
    """Devolve o dicionário do YAML frontmatter (ou {} se ausente)."""
    m = _FRONTMATTER_RE.match(md)
    if not m:
        return {}
    try:
        data = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return {}
    if not isinstance(data, dict):
        return {}
    return data


def remove_frontmatter(md: str) -> tuple[str, dict[str, Any]]:
    """Remove o frontmatter e devolve (corpo, metadados)."""
    m = _FRONTMATTER_RE.match(md)
    if not m:
        return md, {}
    fm = extract_frontmatter(md)
    return md[m.end():], fm


def _strip_for_scan(md: str) -> str:
    """Substitui blocos de código por placeholders preservando offsets das linhas."""
    out = []
    last = 0
    for m in _FENCED_RE.finditer(md):
        out.append(md[last:m.start()])
        # Mantém quebras de linha para preservar números de linha.
        out.append("\n" * md[m.start():m.end()].count("\n"))
        last = m.end()
    out.append(md[last:])
    return "".join(out)


def extract_headings(md: str) -> list[Heading]:
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
                anchor=_slugify_anchor(text),
            )
        )
    return headings


def extract_links(md: str) -> list[Link]:
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
    out = []
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
    """Gera um sumário em Markdown a partir dos headings."""
    out: list[str] = []
    for h in extract_headings(md):
        if h.level > max_depth:
            continue
        indent = "  " * (h.level - 1)
        out.append(f"{indent}- [{h.text}](#{h.anchor})")
    return "\n".join(out)
