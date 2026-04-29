# markdown_hero — Helpers index

Canonical location of every internal utility, organized by domain.
Before creating a new helper, **check this list first** to avoid
duplication (P9, P62).

## Slug / anchor generation

| Helper | Location | Purpose |
|---|---|---|
| `slugify(text)` | `markdown_hero.transform.slugify` | GitHub/Pandoc-compatible slug. Used by `extract_headings` and `build_toc`. |

## Frontmatter (YAML at the top of a Markdown file)

| Helper | Location | Purpose |
|---|---|---|
| `extract_frontmatter(md)` | `markdown_hero.extract` | Returns parsed YAML mapping. Raises `FrontmatterError` on invalid input. |
| `remove_frontmatter(md)` | `markdown_hero.extract` | Returns `(body, metadata)`. |
| `_dump_frontmatter(data)` | `markdown_hero.io` | Internal: serialize a mapping back into a `---` block. |

## Heading manipulation

| Helper | Location | Purpose |
|---|---|---|
| `extract_headings(md)` | `markdown_hero.extract` | List of `Heading` with anchor and line. |
| `build_toc(md, max_depth)` | `markdown_hero.extract` | Markdown table of contents. |
| `shift_headings(md, by)` | `markdown_hero.transform` | Demote/promote ATX headings, clamping to [1, 6]. Skips code blocks. |

## Markup stripping

| Helper | Location | Purpose |
|---|---|---|
| `strip(text, **opts)` | `markdown_hero.strip` | Aggressive normalization to single-line plain text. |
| `md_to_plain(md)` | `markdown_hero.transform` | Lighter version, preserves paragraphs. |
| `strip_html`, `strip_images`, `strip_links`, `strip_code_blocks` | `markdown_hero.transform` | Surgical removals. |

## Tokenization

| Helper | Location | Purpose |
|---|---|---|
| `_default_tokenizer()` | `markdown_hero.chunks` | Returns a `Callable[[str], int]`. Uses `tiktoken` cl100k_base when available, otherwise an approximation. Custom tokenizers can be passed to `extract_chunks(tokenizer=...)`. |

## Block parsing (Markdown → typed blocks)

| Helper | Location | Purpose |
|---|---|---|
| `_parse_blocks(body)` | `markdown_hero.docx` | Internal block tokenizer used by `word_format`. Splits fenced code apart, then dispatches per kind. |
| `_split_sections(body)` | `markdown_hero.chunks` | Heading-aligned section splitter used by structural chunking. |

## Errors

| Type | Location | Use case |
|---|---|---|
| `MarkdownHeroError` | `markdown_hero.errors` | Base class. Catch this when consuming the package generically. |
| `FrontmatterError` | `markdown_hero.errors` | Raised for malformed YAML frontmatter. |
| `MarkdownStructureError` | `markdown_hero.errors` | Raised by internal renderers/parsers when they encounter an unexpected structure (typically indicates a bug). |

## Where things live (and what does **not** belong)

| Module | Owns | Does **not** own |
|---|---|---|
| `strip` | The `strip()` function and its regex constants. | Anything that preserves Markdown structure. |
| `extract` | Read-only inspection of Markdown content. | Mutation, rendering, IO. |
| `transform` | Pure text-in / text-out transformations. | IO, chunking, rendering. |
| `chunks` | Chunking strategies and their tokenizer plumbing. | Frontmatter parsing, link extraction. |
| `io` | File-level operations (append, break, merge). | In-memory transformations. |
| `docx` | Word rendering only. | Markdown-to-Markdown transformations. |
| `lint` | Structural diagnostics over Markdown. | Auto-fixes (we never mutate input). |
| `cli` | Command-line wiring. | New library logic — every CLI subcommand must call into the package. |
| `errors` | Exception hierarchy. | Anything else. |
| `models` | Public dataclasses. | Logic, parsing, IO. |

When adding a new helper, place it in the module whose responsibility
matches the table above. If no module fits, surface the discussion in a
PR before creating a new top-level module.
