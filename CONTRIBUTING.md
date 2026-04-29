# Contributing to markdown_hero

Thank you for your interest in improving this project. The guidelines below
keep contributions consistent with the existing codebase.

## Quick start

```bash
git clone https://github.com/leobr84p/markdown_hero
cd markdown_hero
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

Run the full check suite locally before opening a PR:

```bash
pytest                                # unit tests
pyright markdown_hero/ tests/         # static type checking
ruff check . && ruff format --check . # linting and formatting
markdownlint --config .markdownlint.json README.md docs/*.md
pip-audit --strict                    # dependency vulnerabilities
```

`pre-commit run --all-files` runs every hook in one shot and is what CI
runs as well.

## Coding style

The project follows the in-repo guidelines summarized in `docs/helpers.md`
and these rules:

- **Tests with the change.** Code-only PRs are not merged. Tests must
  cover both the happy path and the documented error paths.
- **Public API gets Google-style docstrings in English.** Document every
  argument, the return value, and every exception that the function
  raises directly.
- **Pyright must stay clean.** The repo ships with `typeCheckingMode = "strict"`.
  Suppressing a diagnostic requires a specific rule code and a comment
  explaining why.
- **Markdownlint must stay clean.** Pre-commit will refuse the change
  otherwise.
- **No silent fallbacks.** Every `try: ... except SomeError: <fallback>`
  block needs a comment justifying the fallback.
- **Frozen dataclasses for value objects.** Mutable dataclasses are
  reserved for cases where mutation is essential (e.g. `Chunk` in the
  chunking pipeline).
- **Where to put a helper.** Consult `docs/helpers.md` first. Each module
  has a documented responsibility and "what does NOT belong" section.

## Commit messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```text
<type>: <short summary>

<body explaining why>

<footer with breaking-change notes if any>
```

Common types: `feat`, `fix`, `chore`, `refactor`, `test`, `docs`, `ci`.

## Submitting a change

1. Open an issue first for non-trivial work so we can align on direction.
2. Branch off `main` (or the active feature branch).
3. Ensure all checks pass locally.
4. Open a PR; describe the user-facing impact and the testing performed.
5. The PR template will guide you through the rest.

## Reporting bugs

Please open a GitHub issue using the bug template. For security issues
follow `SECURITY.md` instead of using the public tracker.
