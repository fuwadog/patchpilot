"""File manager – loads and tracks project files in context."""

from __future__ import annotations

import glob
import mimetypes
import os
from typing import ClassVar, Optional

from ..context.manager import ContextManager
from .readers import FileReaders


class FileManager:
    """
    Responsible for discovering, reading, and tracking project files.
    Supports multiple file formats: code, text, PDF, Word, Excel, etc.
    Delegates context injection to ContextManager and reading to FileReaders.
    """

    FILE_READERS: ClassVar[dict[str, str]] = {
        ".pdf": "read_pdf",
        ".docx": "read_word",
        ".doc": "read_word",
        ".xlsx": "read_excel",
        ".xls": "read_excel",
        ".xlsm": "read_excel",
        ".csv": "read_csv",
        ".json": "read_json",
        ".xml": "read_xml",
        ".html": "read_html",
        ".htm": "read_html",
        ".xhtml": "read_html",
        ".rtf": "read_rtf",
        ".odt": "read_odt",
        ".pptx": "read_powerpoint",
        ".ppt": "read_powerpoint",
    }

    TEXT_EXTENSIONS: ClassVar[set[str]] = {
        ".md",
        ".markdown",
        ".rst",
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
        ".cfg",
        ".conf",
    }

    def __init__(
        self, context: ContextManager, max_files: int, default_extensions: list[str]
    ):
        self._ctx = context
        self._max_files = max_files
        self._extensions = default_extensions
        # path -> full raw content (for patch generation etc.)
        self._store: dict[str, str] = {}

        # Initialize mimetypes
        mimetypes.init()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self, path: str) -> tuple[bool, Optional[str]]:
        """Load a single file. Returns (success, error_message)."""
        path = os.path.abspath(path)
        content, err = self._read(path)
        if err:
            return False, err
        if content is None:
            return False, "No content read from file"
        self._store[path] = content
        self._ctx.upsert_file(path, content)
        return True, None

    def unload(self, path: str, force: bool = False) -> bool:
        """
        Unload a single file.
        Returns True if successful, False if skipped (e.g. pinned).
        """
        path = os.path.abspath(path)
        if self._ctx.remove_file(path, force=force):
            self._store.pop(path, None)
            return True
        return False

    def unload_all(self, keep_pinned: bool = True) -> int:
        """Unload all non-pinned files."""
        paths = list(self._store.keys())
        count = 0
        for p in paths:
            if self.unload(p, force=not keep_pinned):
                count += 1
        return count

    def unload_folder(self, folder: str) -> int:
        """Unload all files within a folder."""
        folder = os.path.abspath(folder)
        paths = list(self._store.keys())
        count = 0
        for p in paths:
            if p.startswith(folder):
                if self.unload(p):
                    count += 1
        return count

    def unload_pattern(self, pattern: str) -> int:
        """Unload files matching a glob pattern."""
        import fnmatch

        paths = list(self._store.keys())
        count = 0
        for p in paths:
            if fnmatch.fnmatch(os.path.basename(p), pattern) or fnmatch.fnmatch(
                p, pattern
            ):
                if self.unload(p):
                    count += 1
        return count

    def get_pin_status(self, path: str) -> bool:
        return self._ctx.is_pinned(path)

    def load_folder(
        self, folder: str, extensions: Optional[list[str]] = None
    ) -> tuple[int, list[str]]:
        """
        Discover and load up to max_files matching files from folder.
        Returns (loaded_count, list_of_errors).
        """
        ext_list = extensions or self._extensions
        discovered = self._discover(folder, ext_list)
        errors: list[str] = []
        loaded = 0
        for path in discovered:
            ok, err = self.load(path)
            if ok:
                loaded += 1
            else:
                errors.append(f"{path}: {err}")
        return loaded, errors

    def get_content(self, path: str) -> Optional[str]:
        return self._store.get(os.path.abspath(path))

    def loaded_paths(self) -> list[str]:
        return list(self._store.keys())

    def is_loaded(self, path: str) -> bool:
        return os.path.abspath(path) in self._store

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _discover(self, folder: str, extensions: list[str]) -> list[str]:
        files: list[str] = []
        for ext in extensions:
            files.extend(glob.glob(os.path.join(folder, "**", ext), recursive=True))
        seen: set[str] = set()
        unique: list[str] = []
        for f in sorted(files):
            af = os.path.abspath(f)
            if af not in seen:
                seen.add(af)
                unique.append(af)
        return unique[: self._max_files]

    def _read(self, path: str) -> tuple[Optional[str], Optional[str]]:
        """
        Read file content based on file type.
        Supports: text files, PDFs, Word docs, Excel files, and more.
        Delegates to FileReaders static methods.
        """
        if not os.path.exists(path):
            return None, "File not found."

        try:
            _, ext = os.path.splitext(path)
            ext = ext.lower()

            reader_name = self.FILE_READERS.get(ext)
            if reader_name:
                reader_fn = getattr(FileReaders, reader_name, None)
                if reader_fn:
                    return reader_fn(path)  # type: ignore[no-any-return]

            return FileReaders.read_text(path)

        except Exception as exc:
            return None, f"Read error: {exc}"
