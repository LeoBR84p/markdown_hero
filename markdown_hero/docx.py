"""Renderização de Markdown para Word (.docx) com estilos pré-definidos."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

from .extract import remove_frontmatter

# Conjunto fixo de estilos.
DEFAULT_STYLES: dict[str, dict[str, Any]] = {
    "body_font": "Calibri",
    "code_font": "Consolas",
    "body_size": 11,
    "code_size": 10,
    "heading_sizes": {1: 18, 2: 14, 3: 12, 4: 11, 5: 11, 6: 11},
    "code_bg": "F5F5F5",
    "table_header_bg": "E7E6E6",
    "link_color": "0563C1",
    "table_caption_centered": True,
    "table_repeat_header": True,
}


def word_format(
    md: str | Path,
    output_path: str | Path,
    *,
    template: str | Path | None = None,
    style_overrides: dict[str, Any] | None = None,
) -> Path:
    """Converte Markdown para .docx aplicando o conjunto de estilos definido.

    Args:
        md: string Markdown ou caminho para arquivo.
        output_path: destino do .docx.
        template: caminho opcional para template .docx (usa seus estilos).
        style_overrides: sobrescreve chaves do dicionário de estilos default.
    """
    text = _read_md(md)
    body, _ = remove_frontmatter(text)

    styles = dict(DEFAULT_STYLES)
    if style_overrides:
        styles.update(style_overrides)

    doc = Document(str(template)) if template else Document()
    _ensure_custom_styles(doc, styles)

    blocks = _parse_blocks(body)
    for block in blocks:
        _render_block(doc, block, styles)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out))
    return out


def _read_md(md: str | Path) -> str:
    if isinstance(md, Path) or (isinstance(md, str) and "\n" not in md and Path(md).exists()):
        return Path(md).read_text(encoding="utf-8")
    return str(md)


# --- Parsing em blocos -------------------------------------------------------

_FENCED_RE = re.compile(r"^(```|~~~)([^\n]*)\n(.*?)^\1\s*$", re.MULTILINE | re.DOTALL)
_HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$")
_QUOTE_RE = re.compile(r"^\s{0,3}>\s?(.*)$")
_UL_RE = re.compile(r"^(\s*)([-*+])\s+(.*)$")
_OL_RE = re.compile(r"^(\s*)(\d+)[.)]\s+(.*)$")
_HR_RE = re.compile(r"^\s{0,3}(?:-{3,}|\*{3,}|_{3,})\s*$")
_TABLE_SEP_RE = re.compile(r"^\s*\|?\s*:?-{3,}:?(?:\s*\|\s*:?-{3,}:?)*\s*\|?\s*$")
_CAPTION_RE = re.compile(r"^Table:\s*(.+)$", re.IGNORECASE)


def _parse_blocks(body: str) -> list[dict]:
    """Tokeniza o Markdown em blocos de alto nível."""
    blocks: list[dict] = []
    # Primeiro extrai blocos fenced para preservá-los.
    last = 0
    fenced_segments: list[tuple[int, int, dict]] = []
    for m in _FENCED_RE.finditer(body):
        fenced_segments.append((m.start(), m.end(), {
            "kind": "code",
            "lang": m.group(2).strip() or None,
            "code": m.group(3).rstrip("\n"),
        }))

    cursor = 0
    for start, end, code_block in fenced_segments:
        if start > cursor:
            blocks.extend(_parse_non_code(body[cursor:start]))
        blocks.append(code_block)
        cursor = end
    if cursor < len(body):
        blocks.extend(_parse_non_code(body[cursor:]))
    return blocks


def _parse_non_code(text: str) -> list[dict]:
    lines = text.split("\n")
    blocks: list[dict] = []
    i = 0
    n = len(lines)
    pending_caption: str | None = None
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if _HR_RE.match(line):
            blocks.append({"kind": "hr"})
            i += 1
            continue
        m = _HEADING_RE.match(line)
        if m:
            blocks.append({"kind": "heading", "level": len(m.group(1)), "text": m.group(2).strip()})
            i += 1
            continue
        # Tabela.
        if "|" in line and i + 1 < n and _TABLE_SEP_RE.match(lines[i + 1]):
            headers = _split_row(line)
            aligns = _parse_align(lines[i + 1])
            rows: list[list[str]] = []
            j = i + 2
            while j < n and lines[j].strip() and "|" in lines[j]:
                rows.append(_split_row(lines[j]))
                j += 1
            blocks.append({
                "kind": "table",
                "headers": headers,
                "rows": rows,
                "alignments": aligns,
                "caption": pending_caption,
            })
            pending_caption = None
            i = j
            continue
        # Caption (Pandoc-style "Table: ...") aparece após uma tabela; aqui pré-armazenamos.
        cap = _CAPTION_RE.match(line.strip())
        if cap:
            # Atribuir à última tabela emitida.
            if blocks and blocks[-1]["kind"] == "table":
                blocks[-1]["caption"] = cap.group(1).strip()
            else:
                pending_caption = cap.group(1).strip()
            i += 1
            continue
        # Quote.
        if _QUOTE_RE.match(line):
            buf: list[str] = []
            while i < n and (_QUOTE_RE.match(lines[i]) or (lines[i].strip() and not _is_block_start(lines[i]))):
                qm = _QUOTE_RE.match(lines[i])
                buf.append(qm.group(1) if qm else lines[i].strip())
                i += 1
            blocks.append({"kind": "quote", "text": " ".join(buf).strip()})
            continue
        # Lista (UL ou OL).
        if _UL_RE.match(line) or _OL_RE.match(line):
            items: list[dict] = []
            while i < n and lines[i].strip() and (_UL_RE.match(lines[i]) or _OL_RE.match(lines[i])):
                ul = _UL_RE.match(lines[i])
                ol = _OL_RE.match(lines[i])
                if ul:
                    indent, _, text_part = ul.groups()
                    items.append({
                        "ordered": False,
                        "level": len(indent) // 2,
                        "text": text_part,
                    })
                elif ol:
                    indent, _, text_part = ol.groups()
                    items.append({
                        "ordered": True,
                        "level": len(indent) // 2,
                        "text": text_part,
                    })
                i += 1
            blocks.append({"kind": "list", "items": items})
            continue
        # Parágrafo (acumula até linha vazia).
        buf = [line]
        i += 1
        while i < n and lines[i].strip() and not _is_block_start(lines[i]):
            buf.append(lines[i])
            i += 1
        blocks.append({"kind": "paragraph", "text": " ".join(b.strip() for b in buf)})
    return blocks


def _is_block_start(line: str) -> bool:
    return bool(
        _HEADING_RE.match(line)
        or _UL_RE.match(line)
        or _OL_RE.match(line)
        or _QUOTE_RE.match(line)
        or _HR_RE.match(line)
    )


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


# --- Renderização ------------------------------------------------------------

_INLINE_RE = re.compile(
    r"(?P<code>`[^`\n]+`)"
    r"|(?P<bold>\*\*[^*\n]+\*\*|__[^_\n]+__)"
    r"|(?P<italic>\*[^*\n]+\*|_[^_\n]+_)"
    r"|(?P<strike>~~[^~\n]+~~)"
    r"|(?P<image>!\[[^\]]*\]\([^)]+\))"
    r"|(?P<link>\[[^\]]+\]\([^)]+\))"
)


def _render_block(doc, block: dict, styles: dict) -> None:
    kind = block["kind"]
    if kind == "heading":
        p = doc.add_heading(level=min(block["level"], 9))
        p.text = ""
        _render_inline(p, block["text"], styles)
        return
    if kind == "paragraph":
        p = doc.add_paragraph(style="Normal")
        _render_inline(p, block["text"], styles)
        return
    if kind == "quote":
        try:
            p = doc.add_paragraph(style="Quote")
        except KeyError:
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Pt(18)
        _render_inline(p, block["text"], styles)
        for run in p.runs:
            run.italic = True
        return
    if kind == "list":
        for item in block["items"]:
            style_name = "List Number" if item["ordered"] else "List Bullet"
            try:
                p = doc.add_paragraph(style=style_name)
            except KeyError:
                p = doc.add_paragraph()
            _render_inline(p, item["text"], styles)
        return
    if kind == "code":
        _render_code(doc, block["code"], styles)
        return
    if kind == "hr":
        p = doc.add_paragraph()
        pPr = p._p.get_or_add_pPr()
        pBdr = OxmlElement("w:pBdr")
        bottom = OxmlElement("w:bottom")
        bottom.set(qn("w:val"), "single")
        bottom.set(qn("w:sz"), "6")
        bottom.set(qn("w:space"), "1")
        bottom.set(qn("w:color"), "auto")
        pBdr.append(bottom)
        pPr.append(pBdr)
        return
    if kind == "table":
        _render_table(doc, block, styles)
        return


def _render_inline(paragraph, text: str, styles: dict) -> None:
    """Aplica formatação inline (bold, italic, code, link) ao parágrafo."""
    pos = 0
    for m in _INLINE_RE.finditer(text):
        if m.start() > pos:
            paragraph.add_run(text[pos:m.start()])
        if m.group("bold"):
            run = paragraph.add_run(m.group("bold").strip("*_"))
            run.bold = True
        elif m.group("italic"):
            run = paragraph.add_run(m.group("italic").strip("*_"))
            run.italic = True
        elif m.group("strike"):
            run = paragraph.add_run(m.group("strike").strip("~"))
            run.font.strike = True
        elif m.group("code"):
            run = paragraph.add_run(m.group("code").strip("`"))
            run.font.name = styles["code_font"]
            run.font.size = Pt(styles["code_size"])
            _shade_run(run, styles["code_bg"])
        elif m.group("image"):
            inner = m.group("image")
            mm = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", inner)
            if mm:
                run = paragraph.add_run(f"[image: {mm.group(1) or mm.group(2)}]")
                run.italic = True
        elif m.group("link"):
            inner = m.group("link")
            mm = re.match(r"\[([^\]]+)\]\(([^)]+)\)", inner)
            if mm:
                _add_hyperlink(paragraph, mm.group(2), mm.group(1), styles["link_color"])
        pos = m.end()
    if pos < len(text):
        paragraph.add_run(text[pos:])


def _render_code(doc, code: str, styles: dict) -> None:
    try:
        p = doc.add_paragraph(style="Code Block")
    except KeyError:
        p = doc.add_paragraph()
    for i, line in enumerate(code.splitlines() or [""]):
        if i > 0:
            p.add_run().add_break()
        run = p.add_run(line)
        run.font.name = styles["code_font"]
        run.font.size = Pt(styles["code_size"])
    _shade_paragraph(p, styles["code_bg"])


def _render_table(doc, block: dict, styles: dict) -> None:
    if block.get("caption") and styles["table_caption_centered"]:
        cap = doc.add_paragraph(block["caption"])
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in cap.runs:
            run.italic = True
            run.font.size = Pt(10)

    headers = block["headers"]
    rows = block["rows"]
    aligns = block.get("alignments") or ["default"] * len(headers)
    if not headers:
        return

    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    try:
        table.style = "Table Grid"
    except KeyError:
        pass

    # Header.
    hdr_cells = table.rows[0].cells
    for j, h in enumerate(headers):
        cell = hdr_cells[j]
        cell.text = ""
        p = cell.paragraphs[0]
        _render_inline(p, h, styles)
        for run in p.runs:
            run.bold = True
        _set_cell_align(p, "center")
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        _shade_cell(cell, styles["table_header_bg"])

    if styles["table_repeat_header"]:
        _repeat_table_header(table.rows[0])

    # Body.
    for ri, row in enumerate(rows, start=1):
        cells = table.rows[ri].cells
        for j in range(len(headers)):
            text_cell = row[j] if j < len(row) else ""
            cell = cells[j]
            cell.text = ""
            p = cell.paragraphs[0]
            _render_inline(p, text_cell, styles)
            align = aligns[j] if j < len(aligns) else "default"
            _set_cell_align(p, align)


def _set_cell_align(paragraph, align: str) -> None:
    if align == "center":
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif align == "right":
        paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    elif align == "left":
        paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT


def _shade_cell(cell, hex_color: str) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def _shade_paragraph(paragraph, hex_color: str) -> None:
    pPr = paragraph._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), hex_color)
    pPr.append(shd)


def _shade_run(run, hex_color: str) -> None:
    rPr = run._r.get_or_add_rPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), hex_color)
    rPr.append(shd)


def _repeat_table_header(row) -> None:
    trPr = row._tr.get_or_add_trPr()
    tblHeader = OxmlElement("w:tblHeader")
    tblHeader.set(qn("w:val"), "true")
    trPr.append(tblHeader)


def _add_hyperlink(paragraph, url: str, text: str, color: str) -> None:
    part = paragraph.part
    r_id = part.relate_to(
        url,
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
        is_external=True,
    )
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), r_id)
    new_run = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")
    color_el = OxmlElement("w:color")
    color_el.set(qn("w:val"), color)
    rPr.append(color_el)
    underline = OxmlElement("w:u")
    underline.set(qn("w:val"), "single")
    rPr.append(underline)
    new_run.append(rPr)
    t = OxmlElement("w:t")
    t.text = text
    t.set(qn("xml:space"), "preserve")
    new_run.append(t)
    hyperlink.append(new_run)
    paragraph._p.append(hyperlink)


# --- Estilos customizados ----------------------------------------------------

def _ensure_custom_styles(doc, styles: dict) -> None:
    from docx.enum.style import WD_STYLE_TYPE

    style_collection = doc.styles
    names = {s.name for s in style_collection}

    if "Code Block" not in names:
        s = style_collection.add_style("Code Block", WD_STYLE_TYPE.PARAGRAPH)
        s.font.name = styles["code_font"]
        s.font.size = Pt(styles["code_size"])

    if "Code Char" not in names:
        s = style_collection.add_style("Code Char", WD_STYLE_TYPE.CHARACTER)
        s.font.name = styles["code_font"]
        s.font.size = Pt(styles["code_size"])

    # Ajustes de fonte default (apenas se 'Normal' não foi imposta por template).
    normal = style_collection["Normal"]
    if normal.font.name in (None, "Calibri"):
        normal.font.name = styles["body_font"]
        normal.font.size = Pt(styles["body_size"])

    # Tamanhos de heading.
    for lvl, size in styles["heading_sizes"].items():
        try:
            h = style_collection[f"Heading {lvl}"]
            h.font.size = Pt(size)
            h.font.bold = True
            if h.font.color and h.font.color.rgb is None:
                h.font.color.rgb = RGBColor(0, 0, 0)
        except KeyError:
            pass
