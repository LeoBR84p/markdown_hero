"""Transformações sobre Markdown."""
from __future__ import annotations

import re
import unicodedata

_RE_FENCED = re.compile(r"^(```|~~~)[^\n]*\n.*?^\1\s*$", re.MULTILINE | re.DOTALL)
_RE_INLINE_CODE = re.compile(r"`[^`\n]*`")
_RE_HEADING = re.compile(r"^(\s{0,3})(#{1,6})(\s+)", re.MULTILINE)
_RE_HTML = re.compile(r"<[^>\n]+>")
_RE_IMAGE = re.compile(r"!\[([^\]]*)\]\([^)]*\)")
_RE_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")


def slugify(text: str) -> str:
    """Slug compatível com GitHub/Pandoc."""
    s = unicodedata.normalize("NFKD", text)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"\s+", "-", s).strip("-")
    return s


def shift_headings(md: str, by: int) -> str:
    """Shift de todos os headings em ``by`` níveis (positivo rebaixa, negativo eleva).

    Headings que ultrapassem o limite [1, 6] são clampados.
    Não toca em conteúdo dentro de blocos de código.
    """
    if by == 0:
        return md

    def _process(chunk: str) -> str:
        def repl(m: re.Match[str]) -> str:
            new_level = max(1, min(6, len(m.group(2)) + by))
            return f"{m.group(1)}{'#' * new_level}{m.group(3)}"

        return _RE_HEADING.sub(repl, chunk)

    return _apply_outside_code(md, _process)


def _apply_outside_code(md: str, fn) -> str:
    """Aplica ``fn`` apenas fora de blocos de código fenced."""
    out = []
    last = 0
    for m in _RE_FENCED.finditer(md):
        out.append(fn(md[last:m.start()]))
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
    """Normaliza espaços e marcadores ATX/lista."""
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
    return _apply_outside_code(md, lambda x: _RE_HTML.sub("", x))


def strip_images(md: str, *, keep_alt: bool = True) -> str:
    repl = r"\1" if keep_alt else ""
    return _apply_outside_code(md, lambda x: _RE_IMAGE.sub(repl, x))


def strip_links(md: str, *, keep_text: bool = True) -> str:
    repl = r"\1" if keep_text else ""
    return _apply_outside_code(md, lambda x: _RE_LINK.sub(repl, x))


def strip_code_blocks(md: str, *, keep_inline: bool = False) -> str:
    s = _RE_FENCED.sub("", md)
    if not keep_inline:
        s = _RE_INLINE_CODE.sub("", s)
    return s


def md_to_plain(md: str) -> str:
    """Texto plano preservando quebras de parágrafo (mais leve que strip)."""
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
