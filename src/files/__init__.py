"""File management, patching, snippets, and multi-format readers."""

from __future__ import annotations

from .manager import FileManager
from .patching import PatchManager
from .readers import FileReaders
from .snippets import SnippetManager

__all__ = [
    "FileManager",
    "PatchManager",
    "FileReaders",
    "SnippetManager",
]
