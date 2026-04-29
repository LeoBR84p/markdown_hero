"""File-level operations on Markdown documents: append, break, merge.

Functions in this module read from disk, transform the content in
memory, and write the result back. They never mutate the input files.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable, Literal

import yaml

from .extract import remove_frontmatter
from .transform import shift_headings

FrontmatterAppendMode = Literal["first", "merge", "drop", "all"]
FrontmatterBreakMode = Literal["replicate", "first", "drop"]
HeadingsMode = Literal["preserve", "shift", "wrap"]
IncludeDelimiter = Literal["before", "after", "none"]


def _read(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def _write(path: str | Path, content: str) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def _dump_frontmatter(data: dict[str, Any]) -> str:
    if not data:
        return ""
    yml = yaml.safe_dump(data, sort_keys=False, allow_unicode=True).strip()
    return f"---\n{yml}\n---\n\n"


def _has_h1(body: str) -> bool:
    return bool(re.search(r"^\s{0,3}#\s+\S", body, re.MULTILINE))


def markdown_append(
    *paths: str | Path,
    output: str | Path,
    separator: str = "\n\n",
    frontmatter: FrontmatterAppendMode = "merge",
    headings: HeadingsMode = "shift",
) -> Path:
    """Concatenate several Markdown files into a single output file.

    Headings can be shifted to avoid duplicate H1s, wrapped under a new
    H1 per file, or preserved verbatim. Frontmatter from each input is
    merged, kept from the first file, dropped, or preserved as-is.

    Args:
        *paths: Two or more input file paths in concatenation order.
        output: Destination file path. Parent directories are created
            on demand.
        separator: Text inserted between consecutive bodies.
        frontmatter: How to combine YAML frontmatter blocks. One of
            ``"first"``, ``"merge"`` (default), ``"drop"``, ``"all"``.
        headings: How to handle heading levels across files. One of
            ``"preserve"``, ``"shift"`` (default), ``"wrap"``.

    Returns:
        The ``Path`` to the written output file.

    Raises:
        ValueError: When called without any input paths.
        FrontmatterError: When any input file's frontmatter is invalid.
    """
    if not paths:
        raise ValueError("markdown_append: at least one input path is required")

    bodies: list[str] = []
    fms: list[dict[str, Any]] = []
    for p in paths:
        raw = _read(p)
        body, fm = remove_frontmatter(raw)
        bodies.append(body)
        fms.append(fm)

    if headings == "shift":
        if bodies and _has_h1(bodies[0]):
            for i in range(1, len(bodies)):
                if _has_h1(bodies[i]):
                    bodies[i] = shift_headings(bodies[i], by=1)
    elif headings == "wrap":
        for i, p in enumerate(paths):
            title = fms[i].get("title") or Path(p).stem
            bodies[i] = f"# {title}\n\n" + shift_headings(bodies[i], by=1)

    if frontmatter == "merge":
        merged: dict[str, Any] = {}
        conflicts: list[str] = []
        for fm in fms:
            for k, v in fm.items():
                if k in merged and merged[k] != v:
                    conflicts.append(k)
                else:
                    merged.setdefault(k, v)
        if conflicts:
            merged["_conflicts"] = sorted(set(conflicts))
        head = _dump_frontmatter(merged)
    elif frontmatter == "first":
        head = _dump_frontmatter(fms[0])
    elif frontmatter == "all":
        head = "".join(_dump_frontmatter(fm) for fm in fms if fm)
    else:
        head = ""

    body_joined = separator.join(b.strip() for b in bodies if b.strip())
    return _write(output, head + body_joined + "\n")


def markdown_break(
    path: str | Path,
    delimiter: str | re.Pattern[str] | Iterable[str | re.Pattern[str]],
    *,
    include_delimiter: IncludeDelimiter = "none",
    output_dir: str | Path,
    name_pattern: str = "{stem}_{i:03d}.md",
    frontmatter: FrontmatterBreakMode = "replicate",
    is_regex: bool = False,
) -> list[Path]:
    """Split a Markdown file into N+1 parts wherever the delimiter occurs.

    Each generated part is written with surrounding whitespace trimmed
    so the previous part ends at the last visible character before the
    delimiter and the next part starts at the first visible character
    after it.

    Args:
        path: Source Markdown file.
        delimiter: The boundary marker. Accepts a literal string, a
            compiled regex, or an iterable mixing both.
        include_delimiter: Where the delimiter text lands. ``"before"``
            attaches it to the previous part, ``"after"`` to the next,
            ``"none"`` discards it.
        output_dir: Directory that will receive the parts. Created on
            demand.
        name_pattern: Format string with ``{stem}`` (source basename)
            and ``{i}`` (zero-based index).
        frontmatter: Frontmatter handling per part. ``"replicate"``
            (default) writes the original block on every part with
            ``part`` and ``part_of`` injected; ``"first"`` keeps it on
            the first part only; ``"drop"`` discards it.
        is_regex: When True, a string ``delimiter`` is treated as a
            regex pattern (with ``re.MULTILINE`` enabled). Compiled
            patterns are always honored as-is.

    Returns:
        A list of ``Path`` objects pointing to the written parts.

    Raises:
        FrontmatterError: When the source file's frontmatter is invalid.
    """
    raw = _read(path)
    body, fm = remove_frontmatter(raw)
    pattern = _build_delim_pattern(delimiter, is_regex)
    matches = list(pattern.finditer(body))
    if not matches:
        return [_write(Path(output_dir) / name_pattern.format(stem=Path(path).stem, i=0), raw)]

    parts: list[tuple[int, int]] = []
    cursor = 0
    for m in matches:
        if include_delimiter == "after":
            parts.append((cursor, m.start()))
            cursor = m.start()
        elif include_delimiter == "before":
            parts.append((cursor, m.end()))
            cursor = m.end()
        else:  # none
            parts.append((cursor, m.start()))
            cursor = m.end()
    parts.append((cursor, len(body)))

    out: list[Path] = []
    stem = Path(path).stem
    n = len(parts)
    for i, (a, b) in enumerate(parts):
        chunk = body[a:b]
        chunk = chunk.lstrip("\n\r\t ").rstrip("\n\r\t ")
        if not chunk:
            continue
        head = ""
        if frontmatter == "replicate" and fm:
            piece_fm = dict(fm)
            piece_fm["part"] = i
            piece_fm["part_of"] = n
            head = _dump_frontmatter(piece_fm)
        elif frontmatter == "first" and fm and i == 0:
            head = _dump_frontmatter(fm)
        target = Path(output_dir) / name_pattern.format(stem=stem, i=i)
        out.append(_write(target, head + chunk + "\n"))
    return out


def _build_delim_pattern(
    delimiter: str | re.Pattern[str] | Iterable[str | re.Pattern[str]],
    is_regex: bool,
) -> re.Pattern[str]:
    if isinstance(delimiter, re.Pattern):
        return delimiter
    if isinstance(delimiter, str):
        return re.compile(
            delimiter if is_regex else re.escape(delimiter),
            re.MULTILINE,
        )
    parts: list[str] = []
    for d in delimiter:
        if isinstance(d, re.Pattern):
            parts.append(d.pattern)
        else:
            parts.append(d if is_regex else re.escape(d))
    return re.compile("|".join(parts), re.MULTILINE)


def markdown_merge(
    *paths: str | Path,
    output: str | Path,
    dedupe_headings: bool = True,
    rebuild_toc: bool = False,
    separator: str = "\n\n",
) -> Path:
    """Concatenate Markdown files with optional dedupe and TOC rebuilding.

    Wraps :func:`markdown_append` (with frontmatter merging and heading
    shift) and adds two optional post-processing steps: removing
    consecutive sections that share the same heading and prepending a
    rebuilt table of contents wrapped in ``<!-- TOC -->`` markers.

    Args:
        *paths: Two or more input file paths in concatenation order.
        output: Destination file path.
        dedupe_headings: When True (default), consecutive sections with
            an identical heading are deduplicated.
        rebuild_toc: When True, a fresh TOC is inserted at the top.
        separator: Text inserted between consecutive bodies.

    Returns:
        The ``Path`` to the written output file.

    Raises:
        FrontmatterError: When any input file's frontmatter is invalid.
    """
    from .extract import build_toc

    out_path = markdown_append(
        *paths,
        output=output,
        separator=separator,
        frontmatter="merge",
        headings="shift",
    )
    text = _read(out_path)
    body, fm = remove_frontmatter(text)
    if dedupe_headings:
        body = _dedupe_consecutive_sections(body)
    if rebuild_toc:
        toc = build_toc(body)
        body = re.sub(r"<!--\s*TOC\s*-->[\s\S]*?<!--\s*/TOC\s*-->", "", body)
        body = f"<!-- TOC -->\n{toc}\n<!-- /TOC -->\n\n" + body
    head = _dump_frontmatter(fm) if fm else ""
    return _write(out_path, head + body)


def _dedupe_consecutive_sections(body: str) -> str:
    """Drop sections whose heading repeats the previous heading verbatim (same level and text)."""
    pattern = re.compile(r"(^\s{0,3}#{1,6}\s+.+?$)", re.MULTILINE)
    matches = list(pattern.finditer(body))
    if not matches:
        return body
    seen_prev: str | None = None
    keep_ranges: list[tuple[int, int]] = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        title = m.group(0).strip()
        if title == seen_prev:
            continue
        keep_ranges.append((m.start(), end))
        seen_prev = title
    head = body[: matches[0].start()]
    return head + "".join(body[a:b] for a, b in keep_ranges)
