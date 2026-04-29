"""markdown_hero — utilities for processing Markdown documents.

Public API only. Implementation details (block parsers, regexes) live in
private helpers and are not re-exported here.
"""

from .chunks import Chunk, extract_chunks
from .docx import word_format
from .errors import FrontmatterError, MarkdownHeroError, MarkdownStructureError
from .extract import (
    build_toc,
    extract_code_blocks,
    extract_frontmatter,
    extract_headings,
    extract_images,
    extract_links,
    extract_tables,
    remove_frontmatter,
)
from .io import markdown_append, markdown_break, markdown_merge
from .lint import Issue, lint, reading_time, word_count
from .models import CodeBlock, Heading, Image, Link, Table
from .strip import strip
from .transform import (
    md_to_plain,
    normalize,
    shift_headings,
    slugify,
    strip_code_blocks,
    strip_html,
    strip_images,
    strip_links,
)

__version__ = "0.1.0"

__all__ = [
    "Chunk",
    "CodeBlock",
    "FrontmatterError",
    "Heading",
    "Image",
    "Issue",
    "Link",
    "MarkdownHeroError",
    "MarkdownStructureError",
    "Table",
    "__version__",
    "build_toc",
    "extract_chunks",
    "extract_code_blocks",
    "extract_frontmatter",
    "extract_headings",
    "extract_images",
    "extract_links",
    "extract_tables",
    "lint",
    "markdown_append",
    "markdown_break",
    "markdown_merge",
    "md_to_plain",
    "normalize",
    "reading_time",
    "remove_frontmatter",
    "shift_headings",
    "slugify",
    "strip",
    "strip_code_blocks",
    "strip_html",
    "strip_images",
    "strip_links",
    "word_count",
    "word_format",
]
