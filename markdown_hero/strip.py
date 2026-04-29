"""Função strip: reduz Markdown a texto puro normalizado."""
from __future__ import annotations

import re
import unicodedata

_RE_FENCED = re.compile(r"```[\s\S]*?```|~~~[\s\S]*?~~~", re.MULTILINE)
_RE_INLINE_CODE = re.compile(r"`[^`\n]*`")
_RE_MATH_BLOCK = re.compile(r"\$\$[\s\S]*?\$\$")
_RE_MATH_INLINE = re.compile(r"\$[^$\n]+\$")
_RE_HTML = re.compile(r"<[^>\n]+>")
_RE_IMAGE = re.compile(r"!\[([^\]]*)\]\([^)]*\)")
_RE_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_RE_REF_LINK = re.compile(r"\[([^\]]+)\]\[[^\]]*\]")
_RE_REF_DEF = re.compile(r"^\s{0,3}\[[^\]]+\]:\s+\S+.*$", re.MULTILINE)
_RE_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+", re.MULTILINE)
_RE_BLOCKQUOTE = re.compile(r"^\s{0,3}>\s?", re.MULTILINE)
_RE_LIST = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+", re.MULTILINE)
_RE_HR = re.compile(r"^\s{0,3}(?:-{3,}|\*{3,}|_{3,})\s*$", re.MULTILINE)
_RE_EMPHASIS = re.compile(r"\*\*|__|\*|_|~~")
_RE_TABLE_PIPES = re.compile(r"\|")
_RE_TABLE_SEP = re.compile(r"^\s*:?-{3,}:?(?:\s*\|\s*:?-{3,}:?)*\s*$", re.MULTILINE)

_MATH_SYMBOLS = "=<>±×÷≤≥≠%°∞+/"
_MATH_SYMBOLS_SET = set(_MATH_SYMBOLS)


def strip(
    text: str,
    *,
    keep_numbers: bool = True,
    keep_math: bool = False,
    keep_latex_text: bool = False,
) -> str:
    """Reduz Markdown a um texto plano em minúsculas, sem acentos nem pontuação.

    Parâmetros:
        text: conteúdo Markdown.
        keep_numbers: preserva dígitos (default True).
        keep_math: preserva sinais matemáticos (`=`, `<`, `>`, `≤`, `≥`, `≠`,
            `±`, `×`, `÷`, `%`, `°`, `+`, `/`). Default False.
        keep_latex_text: quando True, desembrulha o conteúdo de fórmulas LaTeX
            inline `$...$` em vez de descartá-lo.
    """
    if not text:
        return ""

    s = text

    # 1. Blocos de código.
    s = _RE_FENCED.sub(" ", s)

    # 2. Inline code.
    s = _RE_INLINE_CODE.sub(" ", s)

    # 3. Math.
    if keep_latex_text:
        s = _RE_MATH_BLOCK.sub(lambda m: " " + m.group(0).strip("$") + " ", s)
        s = _RE_MATH_INLINE.sub(lambda m: " " + m.group(0).strip("$") + " ", s)
    else:
        s = _RE_MATH_BLOCK.sub(" ", s)
        s = _RE_MATH_INLINE.sub(" ", s)

    # 4. HTML.
    s = _RE_HTML.sub(" ", s)

    # 5. Imagens (mantém alt) e links (mantém texto).
    s = _RE_IMAGE.sub(r"\1", s)
    s = _RE_LINK.sub(r"\1", s)
    s = _RE_REF_LINK.sub(r"\1", s)
    s = _RE_REF_DEF.sub(" ", s)

    # 6. Marcadores de bloco.
    s = _RE_HR.sub(" ", s)
    s = _RE_HEADING.sub("", s)
    s = _RE_BLOCKQUOTE.sub("", s)
    s = _RE_LIST.sub("", s)

    # 7. Tabelas: remove a linha separadora e reduz pipes a espaço.
    s = _RE_TABLE_SEP.sub(" ", s)
    s = _RE_TABLE_PIPES.sub(" ", s)

    # 8. Marcadores de ênfase.
    s = _RE_EMPHASIS.sub("", s)

    # 9. Normalização Unicode (remove diacríticos: ç→c, ã→a, é→e, etc).
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))

    # 10. Tratamento de pontuação e símbolos.
    out_chars: list[str] = []
    for ch in s:
        cat = unicodedata.category(ch)  # ex: 'Lu', 'Nd', 'Po', 'Zs', 'Cc'
        if cat.startswith("L") or cat.startswith("N") or ch in (" ", "\t", "\n"):
            out_chars.append(ch)
        elif keep_math and ch in _MATH_SYMBOLS_SET:
            out_chars.append(ch)
        elif ch in _MATH_SYMBOLS_SET and not keep_math:
            # Symbols matemáticos sem keep_math: deletados (juntam tokens vizinhos).
            continue
        else:
            # Demais sinais (.,;:!?()[]{}…): viram espaço.
            out_chars.append(" ")
    s = "".join(out_chars)

    # 11. Remove qualquer caractere não-ASCII residual (símbolos exóticos).
    s = re.sub(r"[^\x00-\x7f]", " ", s)

    # 12. Lowercase.
    s = s.lower()

    # 13. Números.
    if not keep_numbers:
        s = re.sub(r"\d+", " ", s)

    # 14. Colapsa espaços e quebras.
    s = re.sub(r"\s+", " ", s).strip()
    return s
