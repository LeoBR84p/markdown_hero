"""markdown_hero — utilitários para processamento de Markdown."""

from .strip import strip
from .chunks import extract_chunks, Chunk
from .io import markdown_append, markdown_break, markdown_merge
from .docx import word_format
from .extract import (
    extract_frontmatter,
    remove_frontmatter,
    extract_links,
    extract_images,
    extract_tables,
    extract_code_blocks,
    extract_headings,
    build_toc,
)
from .transform import (
    normalize,
    slugify,
    shift_headings,
    strip_html,
    strip_images,
    strip_links,
    strip_code_blocks,
    md_to_plain,
)
from .lint import lint, word_count, reading_time, Issue
from .models import Link, Image, Table, CodeBlock, Heading

__version__ = "0.1.0"

__all__ = [
    "strip",
    "extract_chunks",
    "Chunk",
    "markdown_append",
    "markdown_break",
    "markdown_merge",
    "word_format",
    "extract_frontmatter",
    "remove_frontmatter",
    "extract_links",
    "extract_images",
    "extract_tables",
    "extract_code_blocks",
    "extract_headings",
    "build_toc",
    "normalize",
    "slugify",
    "shift_headings",
    "strip_html",
    "strip_images",
    "strip_links",
    "strip_code_blocks",
    "md_to_plain",
    "lint",
    "word_count",
    "reading_time",
    "Issue",
    "Link",
    "Image",
    "Table",
    "CodeBlock",
    "Heading",
    "__version__",
]
