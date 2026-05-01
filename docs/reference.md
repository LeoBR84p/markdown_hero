# markdown_hero — Technical reference

This document describes every public function, its parameters, behavior,
and usage examples. The current version is **0.1.0**, Python ≥ 3.10,
target dialect **GFM** (GitHub Flavored Markdown).

## Table of contents

1. [`strip`](#strip) — normalized plain text
2. [`extract_chunks`](#extract_chunks) — structural chunking
3. [`word_format`](#word_format) — Word (.docx) export
4. [`markdown_append`](#markdown_append) — concatenation
5. [`markdown_break`](#markdown_break) — split by delimiters
6. [`markdown_merge`](#markdown_merge) — smart append
7. [Extraction functions](#extraction) — frontmatter, links, images, tables, code, headings, TOC
8. [Transformation functions](#transformation) — normalize, slugify, shift_headings, strip_*
9. [Lint and metrics](#lint) — `lint`, `word_count`, `reading_time`
10. [CLI](#cli)
11. [Data models](#models)
12. [Design decisions](#design)
13. [Limits and security](#limits)

---

<a id="strip"></a>

## 1. `strip(text, *, keep_numbers=True, keep_math=False, keep_latex_text=False) -> str`

Reduces Markdown to a single line of text: lowercase, no diacritics
(NFKD), no punctuation, no markup. Runs of whitespace and line breaks
collapse to a single space.

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `text` | `str` | — | Markdown content to normalize. |
| `keep_numbers` | `bool` | `True` | Preserve digits. |
| `keep_math` | `bool` | `False` | Preserve math symbols: `=`, `<`, `>`, `≤`, `≥`, `≠`, `±`, `×`, `÷`, `%`, `°`, `+`, `/`. |
| `keep_latex_text` | `bool` | `False` | Instead of removing `$...$` / `$$...$$` formulas, unwrap their content as text. |

### Behavior

- Code blocks, inline code, inline HTML, LaTeX formulas, links, and
  images are processed before normalization.
- For links and images the visible text/alt is preserved and the URL
  is dropped.
- Math symbols (`=`) are **deleted with no replacement**, so `p=2`
  becomes `p2`.
- Generic punctuation (`.,;:!?()[]{}`) becomes a space.
- After NFKD, residual non-ASCII characters are removed.

### Example

```python
from markdown_hero import strip

md = """**Trade-off between mean and max.**
p=1 (weighted arithmetic mean) ignores risk concentration.
p=2 captures both."""

strip(md)
# 'trade off between mean and max p1 weighted arithmetic mean
#  ignores risk concentration p2 captures both'

strip(md, keep_math=True)
# '... p=1 ... p=2 ...'

strip("A formula $x = y + 1$.", keep_latex_text=True)
# 'a formula x y 1'
```

---

<a id="extract_chunks"></a>

## 2. `extract_chunks(md, *, strategy=None, purpose="generic", max_tokens=0, overlap=0, tokenizer=None, source=None, min_tokens=0) -> list[Chunk]`

Splits a document into pieces with structural metadata that is useful
for RAG, fine-tuning, summarization, etc.

### Strategies

| Strategy | Behavior |
|---|---|
| `structural` | Splits by heading hierarchy; each section becomes one chunk. |
| `semantic` | Groups paragraphs up to `max_tokens`. |
| `fixed` | Hard token-based slicing. |
| `hybrid` | Structural split plus per-token sub-splitting inside large sections. |

### Defaults per `purpose`

| `purpose` | `strategy` | `max_tokens` | `overlap` |
|---|---|---|---|
| `rag` | `hybrid` | 512 | 64 |
| `finetune` | `structural` | 1024 | 0 |
| `summary` | `structural` | 2048 | 0 |
| `generic` | `structural` | 512 | 0 |

### Parameters

| Parameter | Type | Description |
|---|---|---|
| `md` | `str` | Full Markdown content. |
| `strategy` | `str \| None` | Overrides the strategy derived from `purpose`. |
| `purpose` | `"rag"\|"finetune"\|"summary"\|"generic"` | Sets sensible defaults. |
| `max_tokens` | `int` | Override the token budget; `0` keeps the purpose default. |
| `overlap` | `int` | Token overlap between consecutive chunks of the same section. |
| `tokenizer` | `Callable[[str], int]` | Token counter; default uses `tiktoken` (cl100k_base) when installed, otherwise the approximation `len/3.5`. |
| `source` | `str \| None` | Document identifier recorded on every chunk. |
| `min_tokens` | `int` | When > 0, sections smaller than this are merged into the previous chunk. |

### Structural guarantees

- **Never splits inside fenced blocks** or tables — they remain intact.
- **Overlap is restricted to the same section** (it does not cross
  headings) to avoid semantic contamination.
- **Full breadcrumb**: every chunk carries `heading_path = ["Cap",
  "Section", ...]`.
- **Oversized**: when a single block exceeds `max_tokens` and cannot be
  subdivided, the chunk has `oversized=True`.

### Example

```python
from markdown_hero import extract_chunks

chunks = extract_chunks(open("doc.md").read(), purpose="rag", source="doc.md")
for c in chunks:
    print(f"[{' › '.join(c.heading_path)}] tokens={c.token_count} type={c.type}")
    print(c.text[:80])
```

### Best practices for RAG

- Use `purpose="rag"` (structural + sub-split + small overlap).
- Index `heading_path` as metadata: filtering by section yields large
  retrieval gains.
- For heterogeneous documents (code + prose), the `type` field allows
  routing different content kinds through different embedding models or
  retrieval pipelines.

---

<a id="word_format"></a>

## 3. `word_format(md, output_path, *, template=None, style_overrides=None) -> Path`

Renders Markdown into a `.docx` file with a professional default style
set.

### Parameters

| Parameter | Type | Description |
|---|---|---|
| `md` | `str \| Path` | Markdown content or path to a Markdown file. |
| `output_path` | `str \| Path` | Destination of the `.docx`. |
| `template` | `str \| Path \| None` | `.docx` template whose styles are used as the base. |
| `style_overrides` | `dict \| None` | Overrides keys of the `DEFAULT_STYLES` dictionary. |

### Default style set (`DEFAULT_STYLES`)

```python
{
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
```

### Markdown → Word style mapping

| Element | Word style | Details |
|---|---|---|
| `# H1`–`###### H6` | `Heading 1`–`Heading 6` | Per-level sizes, **bold**. |
| Paragraph | `Normal` | Calibri 11pt. |
| **bold**, *italic*, ~~strike~~ | inline runs | Applied per character run. |
| `inline code` | run with `Code Char` | Consolas 10pt, background `#F5F5F5`. |
| ```` ```block``` ```` | `Code Block` (custom) | Consolas 10pt, background `#F5F5F5`. |
| `> quote` | `Quote` | Italic, indented. |
| `- list` / `1. list` | `List Bullet` / `List Number` | Native Word styles. |
| Table | `Table Grid` + header `#E7E6E6` | Bold header, repeats across page breaks. |
| `Table: caption` | `Caption` | Centered, italic, 10pt, above the table. |
| Link | run with hyperlink | Blue `#0563C1`, underlined. |
| `---` | Horizontal rule | Bottom border on a paragraph. |

### Example

```python
from markdown_hero import word_format
word_format("report.md", "report.docx")

# With a user template (preserves header / footer / branding):
word_format("report.md", "report.docx", template="company-base.docx")

# Overriding styles:
word_format(
    "report.md",
    "report.docx",
    style_overrides={"body_size": 12, "code_bg": "EFEFEF"},
)
```

---

<a id="markdown_append"></a>

## 4. `markdown_append(*paths, output, separator="\n\n", frontmatter="merge", headings="shift") -> Path`

Concatenates several Markdown files into a single output file.

### `frontmatter` modes

| Value | Behavior |
|---|---|
| `merge` (default) | Combines every block into a single mapping. Conflicts keep the first value and list the colliding keys under `_conflicts`. |
| `first` | Keeps only the frontmatter from the first file. |
| `drop` | Removes frontmatter from all files. |
| `all` | Preserves each block sequentially (rarely useful). |

### `headings` modes

| Value | Behavior |
|---|---|
| `shift` (default) | If the first file has an H1, the others are shifted by +1 to avoid duplicate H1s. |
| `preserve` | Does not change headings. |
| `wrap` | Each file is inserted as a section under `# {filename or frontmatter title}`. |

### Example

```python
from markdown_hero import markdown_append

markdown_append(
    "intro.md", "ch1.md", "ch2.md",
    output="book.md",
    frontmatter="merge",
    headings="shift",
)
```

---

<a id="markdown_break"></a>

## 5. `markdown_break(path, delimiter, *, include_delimiter="none", output_dir, name_pattern="{stem}_{i:03d}.md", frontmatter="replicate", is_regex=False) -> list[Path]`

Splits a Markdown file into **N+1** parts wherever the delimiter occurs
**N** times.

### Parameters

| Parameter | Type | Description |
|---|---|---|
| `delimiter` | `str \| re.Pattern \| Iterable` | Accepts a literal string, a compiled regex, or a list mixing both. |
| `is_regex` | `bool` | When `True`, a string is interpreted as a regex (with the `re.MULTILINE` flag). |
| `include_delimiter` | `"before"\|"after"\|"none"` | Where the delimiter text goes (end of previous part, start of next, or discarded). |
| `output_dir` | `str \| Path` | Output directory (created on demand). |
| `name_pattern` | `str` | Filename template. Receives `stem` (from the source file) and `i` (index). |
| `frontmatter` | `"replicate"\|"first"\|"drop"` | YAML frontmatter handling. With `replicate` each part receives `part: i` and `part_of: N`. |

### Whitespace handling

Each part is written with `lstrip` / `rstrip` so the previous part ends
at the last visible character before the delimiter and the next part
starts at the first visible character after it.

### Example

```python
from markdown_hero import markdown_break

# 1) Split on a literal separator
markdown_break("book.md", "---SEP---", output_dir="parts/")

# 2) Split on a regex matching level-1 headings
markdown_break(
    "book.md", r"^# .+$", is_regex=True,
    include_delimiter="after", output_dir="chapters/",
    name_pattern="ch_{i:02d}.md",
)

# 3) Multiple delimiters
markdown_break("doc.md", ["===", "---END---"], output_dir="parts/")
```

---

<a id="markdown_merge"></a>

## 6. `markdown_merge(*paths, output, dedupe_headings=True, rebuild_toc=False, separator="\n\n") -> Path`

Smart append: uses `markdown_append` with frontmatter merging and
heading shifting, plus:

- **Heading dedupe**: removes consecutive sections that share the same
  heading.
- **Optional TOC**: rebuilds a table of contents wrapped in
  `<!-- TOC -->` / `<!-- /TOC -->` markers.

```python
from markdown_hero import markdown_merge

markdown_merge("a.md", "b.md", output="merged.md", rebuild_toc=True)
```

---

<a id="extraction"></a>

## 7. Extraction functions

| Function | Returns |
|---|---|
| `extract_frontmatter(md)` | `dict` (empty when absent) |
| `remove_frontmatter(md)` | `(body, metadata)` |
| `extract_links(md)` | `list[Link]` (inline + autolink) |
| `extract_images(md)` | `list[Image]` |
| `extract_tables(md)` | `list[Table]` (with `headers`, `rows`, `alignments`) |
| `extract_code_blocks(md, language=None)` | `list[CodeBlock]` (filterable by language) |
| `extract_headings(md)` | `list[Heading]` (with level and GitHub-style anchor) |
| `build_toc(md, max_depth=3)` | `str` (Markdown) |

All ignore content inside fenced code blocks (matches in
`print("[link](x)")` are not returned as links).

```python
from markdown_hero import extract_links, build_toc

for link in extract_links(open("doc.md").read()):
    print(link.line, link.url)

print(build_toc(open("doc.md").read(), max_depth=2))
```

---

<a id="transformation"></a>

## 8. Transformation functions

| Function | Description |
|---|---|
| `normalize(md, unify_lists=True, trim_trailing=True, collapse_blank_lines=True)` | Standardizes whitespace and list markers. |
| `slugify(text)` | GitHub/Pandoc-compatible slug. |
| `shift_headings(md, by)` | Demote/promote headings, ignoring code blocks; clamped to [1, 6]. |
| `strip_html(md)` | Removes inline HTML tags. |
| `strip_images(md, keep_alt=True)` | Removes images (optionally keeping alt text). |
| `strip_links(md, keep_text=True)` | Removes links (optionally keeping link text). |
| `strip_code_blocks(md, keep_inline=False)` | Removes fenced blocks; optionally inline code as well. |
| `md_to_plain(md)` | Plain text preserving paragraph breaks (lighter than `strip`). |

---

<a id="lint"></a>

## 9. Lint and metrics

### `lint(md) -> list[Issue]`

Detects:

| Rule | Severity | Description |
|---|---|---|
| `heading-skip` | warning | H1 → H3 with no intermediate H2, etc. |
| `duplicate-anchor` | warning | Two headings produce the same anchor. |
| `empty-link-text` | warning | `[](url)` |
| `empty-link-url` | warning | `[text]()` or `[text](#)` |
| `unclosed-fence` | error | Code fence opened but not closed. |

```python
from markdown_hero import lint

for issue in lint(open("doc.md").read()):
    print(f"L{issue.line} {issue.severity}: {issue.rule} — {issue.message}")
```

### `word_count(md, ignore_code=True) -> int`

Counts text words, ignoring code blocks by default.

### `reading_time(md, wpm=200) -> float`

Reading time estimate in minutes (200 WPM ≈ average prose reader).

---

<a id="cli"></a>

## 10. CLI — `markdown-hero`

```text
markdown-hero strip   <input> [-o OUT] [--no-numbers] [--keep-math] [--keep-latex-text]
markdown-hero chunk   <input> [-o OUT] [--purpose rag|finetune|summary|generic]
                              [--max-tokens N] [--overlap N]
markdown-hero append  <input...> -o OUT [--separator SEP] [--frontmatter ...] [--headings ...]
markdown-hero break   <input> <delim> --output-dir DIR [--regex] [--include before|after|none]
                              [--frontmatter replicate|first|drop]
markdown-hero merge   <input...> -o OUT [--no-dedupe] [--toc]
markdown-hero word    <input> -o OUT [--template TEMPLATE.docx]
markdown-hero lint    <input> [--json] [-o OUT]
markdown-hero stats   <input>
```

Use `-` as `<input>` to read from stdin.

```bash
echo "**hi**" | markdown-hero strip -
# hi

markdown-hero chunk doc.md --purpose rag --max-tokens 512 -o chunks.json
markdown-hero word doc.md -o doc.docx --template company.docx
markdown-hero break book.md "## " --regex --include after --output-dir sections/
```

`lint` returns **exit code 1** when there are `error` issues (useful in
CI).

---

<a id="models"></a>

## 11. Data models

```python
@dataclass(frozen=True)
class Link:        text: str; url: str; title: str|None; line: int; type: Literal["inline","reference","autolink"]

@dataclass(frozen=True)
class Image:       alt: str; url: str; title: str|None; line: int

@dataclass(frozen=True)
class Table:       headers: list[str]; rows: list[list[str]]; alignments: list[str]; line: int

@dataclass(frozen=True)
class CodeBlock:   code: str; language: str|None; line: int; fenced: bool

@dataclass(frozen=True)
class Heading:     level: int; text: str; line: int; anchor: str

@dataclass
class Chunk:
    text: str
    heading_path: list[str]
    char_start: int; char_end: int
    token_count: int
    type: Literal["prose","code","table","list","mixed"]
    source: str|None
    index: int
    oversized: bool
    metadata: dict
```

---

<a id="design"></a>

## 12. Design decisions

- **Target dialect**: GFM. It covers 95% of real-world cases (GitHub,
  Obsidian, Notion export). MyST and CommonMark are not fully supported
  in 0.1.
- **Minimal dependencies**: `markdown-it-py`, `mdit-py-plugins`,
  `python-docx`, `PyYAML`. `tiktoken` is optional (`tokenizers` extra).
- **Language**: `strip` is multilingual via `unicodedata.NFKD` — there
  is no per-language table.
- **Math symbols**: deleted with no replacement by default, joining
  adjacent tokens (`p=2` → `p2`). With `keep_math=True` they are
  preserved.
- **Generic punctuation**: becomes a space, then runs of whitespace
  collapse.
- **Code blocks** are untouched by transformation functions
  (`shift_headings`, `strip_html`, etc.). This avoids corrupting
  technical content.
- **Frontmatter**: detected **only at the very top** of the file,
  delimited by `---` on their own lines.
- **Result ordering**: `extract_*` returns items in document order with
  `line` 1-based.

---

<a id="limits"></a>

## 13. Limits and security considerations

### File size

`markdown_hero` reads the whole document into memory (`Path.read_text`).
There is no streaming. For typical documents (up to a few MB) this is
adequate and keeps the API simple; for very large files (hundreds of MB)
break the content with external tools before calling the library.

### `markdown_break` with `is_regex=True` and untrusted input

When `is_regex=True`, the `delimiter` argument is compiled directly via
`re.compile`. **Do not pass untrusted input** (coming from end users
without validation) as a regex: malicious patterns can cause *ReDoS*
(exponential backtracking). If the input comes from a user, keep the
default `is_regex=False` or validate the pattern first.

### Frontmatter and YAML

`extract_frontmatter` uses `yaml.safe_load` (not `yaml.load`), which
prevents deserialization of arbitrary Python objects. Even so, validate
the contents before using values in sensitive operations (for example,
building paths from `metadata["filename"]`).

### Parser limitation

The library uses regular expressions for structural recognition rather
than a full CommonMark/GFM parser. It covers the subset documented in
this file but may diverge from reference implementations on edge cases
(deeply nested lists, complex inline HTML, multi-line reference links).
