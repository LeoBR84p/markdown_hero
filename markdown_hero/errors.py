"""Exception hierarchy for markdown_hero.

Domain errors raised by the package. Generic Python exceptions
(``ValueError``, ``TypeError``) are still used for plain argument
validation; this module is reserved for failures with a Markdown-specific
meaning.
"""
from __future__ import annotations


class MarkdownHeroError(Exception):
    """Base class for all markdown_hero errors."""


class FrontmatterError(MarkdownHeroError):
    """Raised when YAML frontmatter is present but cannot be parsed.

    The error wraps the original ``yaml.YAMLError`` (when available) in
    the ``__cause__`` attribute.
    """


class MarkdownStructureError(MarkdownHeroError):
    """Raised when a structural assumption about Markdown content fails."""
