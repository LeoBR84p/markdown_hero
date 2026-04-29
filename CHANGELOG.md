# Changelog

All notable changes to this project are documented in this file. The format is
based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the
project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-05-01

### Added

- `strip(text, *, keep_numbers, keep_math, keep_latex_text)` — multilingual
  reduction of Markdown to a single-line plain-text representation.
- `extract_chunks(md, *, strategy, purpose, max_tokens, overlap, tokenizer,
  source, min_tokens)` — structural chunking with `structural`, `semantic`,
  `fixed`, and `hybrid` strategies plus per-purpose defaults
  (`rag`, `finetune`, `summary`, `generic`).
- `word_format(md, output_path, *, template, style_overrides)` — Word `.docx`
  rendering with a fixed style set. Tables repeat their header row across
  page breaks; captions render centered above the table.
- `markdown_append(*paths, output, separator, frontmatter, headings)` —
  concatenate Markdown files with frontmatter merging and heading shifting
  modes (`preserve`, `shift`, `wrap`).
- `markdown_break(path, delimiter, *, include_delimiter, output_dir,
  name_pattern, frontmatter, is_regex)` — split a Markdown file at one or
  more delimiters (string, compiled regex, or list mixing both).
- `markdown_merge(*paths, output, dedupe_headings, rebuild_toc, separator)`
  — smart append with optional consecutive-section dedupe and TOC rebuild.
- Extraction helpers: `extract_frontmatter`, `remove_frontmatter`,
  `extract_links`, `extract_images`, `extract_tables`, `extract_code_blocks`,
  `extract_headings`, `build_toc`.
- Transformation helpers: `slugify`, `shift_headings`, `normalize`,
  `strip_html`, `strip_images`, `strip_links`, `strip_code_blocks`,
  `md_to_plain`.
- Lint and metrics: `lint(md)` (rules `heading-skip`, `duplicate-anchor`,
  `empty-link-text`, `empty-link-url`, `unclosed-fence`), `word_count`,
  `reading_time`.
- Typed exception hierarchy: `MarkdownHeroError`, `FrontmatterError`,
  `MarkdownStructureError`.
- `markdown-hero` command-line interface with eight subcommands:
  `strip`, `chunk`, `append`, `break`, `merge`, `word`, `lint`, `stats`.
- PEP 561 `py.typed` marker so consumers benefit from the package's full
  type annotations.
- Documentation in `docs/reference.md` (full API reference) and
  `docs/helpers.md` (canonical index of internal utilities).

[Unreleased]: https://github.com/leobr84p/markdown_hero/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/leobr84p/markdown_hero/releases/tag/v0.1.0
