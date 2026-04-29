"""CLI: markdown-hero <subcomando>."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .chunks import extract_chunks
from .docx import word_format
from .io import markdown_append, markdown_break, markdown_merge
from .lint import lint, reading_time, word_count
from .strip import strip


def _read(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def _write(path: str | None, content: str) -> None:
    if path in (None, "-"):
        sys.stdout.write(content)
    else:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(content, encoding="utf-8")


def cmd_strip(args: argparse.Namespace) -> int:
    text = _read(args.input)
    out = strip(
        text,
        keep_numbers=not args.no_numbers,
        keep_math=args.keep_math,
        keep_latex_text=args.keep_latex_text,
    )
    _write(args.output, out + ("\n" if not out.endswith("\n") else ""))
    return 0


def cmd_chunk(args: argparse.Namespace) -> int:
    text = _read(args.input)
    chunks = extract_chunks(
        text,
        purpose=args.purpose,
        max_tokens=args.max_tokens,
        overlap=args.overlap,
        source=None if args.input == "-" else args.input,
    )
    payload = [
        {
            "index": c.index,
            "text": c.text,
            "heading_path": c.heading_path,
            "token_count": c.token_count,
            "type": c.type,
            "char_start": c.char_start,
            "char_end": c.char_end,
            "oversized": c.oversized,
        }
        for c in chunks
    ]
    _write(args.output, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return 0


def cmd_append(args: argparse.Namespace) -> int:
    out = markdown_append(
        *args.inputs,
        output=args.output,
        separator=args.separator,
        frontmatter=args.frontmatter,
        headings=args.headings,
    )
    print(out)
    return 0


def cmd_break(args: argparse.Namespace) -> int:
    paths = markdown_break(
        args.input,
        args.delimiter,
        is_regex=args.regex,
        include_delimiter=args.include,
        output_dir=args.output_dir,
        frontmatter=args.frontmatter,
    )
    for p in paths:
        print(p)
    return 0


def cmd_merge(args: argparse.Namespace) -> int:
    out = markdown_merge(
        *args.inputs,
        output=args.output,
        dedupe_headings=not args.no_dedupe,
        rebuild_toc=args.toc,
    )
    print(out)
    return 0


def cmd_word(args: argparse.Namespace) -> int:
    out = word_format(args.input, args.output, template=args.template)
    print(out)
    return 0


def cmd_lint(args: argparse.Namespace) -> int:
    text = _read(args.input)
    issues = lint(text)
    if args.json:
        payload = [
            {"rule": i.rule, "message": i.message, "line": i.line, "severity": i.severity}
            for i in issues
        ]
        _write(args.output, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    else:
        for i in issues:
            sys.stdout.write(f"{i.severity.upper():7} L{i.line:<5} {i.rule}: {i.message}\n")
    return 1 if any(i.severity == "error" for i in issues) else 0


def cmd_stats(args: argparse.Namespace) -> int:
    text = _read(args.input)
    payload = {
        "words": word_count(text),
        "reading_time_min": round(reading_time(text), 2),
    }
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="markdown-hero", description="Markdown utilities.")
    p.add_argument("--version", action="version", version=f"markdown_hero {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("strip", help="reduce Markdown to normalized plain text")
    sp.add_argument("input", help=".md file or '-' for stdin")
    sp.add_argument("-o", "--output", help="output file (default: stdout)")
    sp.add_argument("--no-numbers", action="store_true", help="strip digits as well")
    sp.add_argument("--keep-math", action="store_true", help="keep math symbols verbatim")
    sp.add_argument("--keep-latex-text", action="store_true", help="keep formula text from $...$")
    sp.set_defaults(func=cmd_strip)

    sp = sub.add_parser("chunk", help="split a document into chunks (JSON output)")
    sp.add_argument("input")
    sp.add_argument("-o", "--output")
    sp.add_argument("--purpose", choices=["rag", "finetune", "summary", "generic"], default="generic")
    sp.add_argument("--max-tokens", type=int, default=0)
    sp.add_argument("--overlap", type=int, default=0)
    sp.set_defaults(func=cmd_chunk)

    sp = sub.add_parser("append", help="concatenate several Markdown files")
    sp.add_argument("inputs", nargs="+")
    sp.add_argument("-o", "--output", required=True)
    sp.add_argument("--separator", default="\n\n")
    sp.add_argument("--frontmatter", choices=["first", "merge", "drop", "all"], default="merge")
    sp.add_argument("--headings", choices=["preserve", "shift", "wrap"], default="shift")
    sp.set_defaults(func=cmd_append)

    sp = sub.add_parser("break", help="split a Markdown file at the given delimiter(s)")
    sp.add_argument("input")
    sp.add_argument("delimiter")
    sp.add_argument("--regex", action="store_true")
    sp.add_argument("--include", choices=["before", "after", "none"], default="none")
    sp.add_argument("--output-dir", required=True)
    sp.add_argument("--frontmatter", choices=["replicate", "first", "drop"], default="replicate")
    sp.set_defaults(func=cmd_break)

    sp = sub.add_parser("merge", help="smart append with section dedupe and optional TOC")
    sp.add_argument("inputs", nargs="+")
    sp.add_argument("-o", "--output", required=True)
    sp.add_argument("--no-dedupe", action="store_true")
    sp.add_argument("--toc", action="store_true")
    sp.set_defaults(func=cmd_merge)

    sp = sub.add_parser("word", help="render Markdown to a .docx file")
    sp.add_argument("input")
    sp.add_argument("-o", "--output", required=True)
    sp.add_argument("--template")
    sp.set_defaults(func=cmd_word)

    sp = sub.add_parser("lint", help="report structural issues in a Markdown file")
    sp.add_argument("input")
    sp.add_argument("--json", action="store_true")
    sp.add_argument("-o", "--output")
    sp.set_defaults(func=cmd_lint)

    sp = sub.add_parser("stats", help="word count and reading time")
    sp.add_argument("input")
    sp.set_defaults(func=cmd_stats)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
