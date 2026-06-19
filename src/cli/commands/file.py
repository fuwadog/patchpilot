"""File management commands for the PatchPilot REPL.

All functions follow the same signature pattern — accept the managers they
need, produce output via the Rich *output* module, and return ``None``.

Commands covered
----------------
- ``/file add <path>`` — load a file into context
- ``/file folder <path>`` — load all files from a directory
- ``/file list`` — list loaded files with pin status
- ``/file remove <path>`` — unload a file
- ``/file show <path>`` — display file content
- ``/file pin <path>`` — pin a file (prevent accidental unloading)
- ``/file unpin <path>`` — remove a pin
"""

from __future__ import annotations

from ...context.manager import ContextManager
from ...files.manager import FileManager
from ..output import (
    print_code_block,
    print_error,
    print_info,
    print_success,
    print_warning,
)

# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


def cmd_file_add(files: FileManager, path: str) -> None:
    """Load a single file into context.

    Parameters
    ----------
    files:
        The active :class:`FileManager` instance.
    path:
        Absolute or relative path to the file.
    """
    ok, err = files.load(path)
    if ok:
        print_success(f"Loaded: {path}")
    else:
        print_error(f"Failed to load: {err}")


def cmd_file_folder(
    files: FileManager, folder: str
) -> None:
    """Load all discoverable files from a folder.

    Parameters
    ----------
    files:
        The active :class:`FileManager` instance.
    folder:
        Path to the folder to scan.
    """
    import os

    if not os.path.isdir(folder):
        print_error(f"Folder not found: {folder}")
        return

    count, errors = files.load_folder(folder)
    for err in errors:
        print_warning(f"  Skipped \u2013 {err}")
    if count:
        print_success(f"Loaded {count} file(s) from {folder}.")
    else:
        print_info(f"No matching files found in {folder}.")


def cmd_file_list(
    files: FileManager, context: ContextManager
) -> None:
    """Display a table of loaded files with pin status.

    Parameters
    ----------
    files:
        The active :class:`FileManager` instance.
    context:
        The active :class:`ContextManager` (used to check pin status).
    """
    paths = files.loaded_paths()
    tags: dict[str, str] = {}
    for p in paths:
        if context.is_pinned(p):
            tags[p] = "\U0001f4cc pinned"
    from ..output import print_file_list

    print_file_list(paths, tags)


def cmd_file_remove(
    files: FileManager, context: ContextManager, path: str
) -> None:
    """Unload a file from context.

    Parameters
    ----------
    files:
        The active :class:`FileManager` instance.
    context:
        The active :class:`ContextManager` (used to check pin status).
    path:
        Path to the file to unload.
    """
    if context.is_pinned(path):
        print_warning(
            f"{path} is pinned.  Use /file unpin {path} first."
        )
        return
    if files.unload(path):
        print_success(f"Unloaded: {path}")
    else:
        print_warning(f"File not loaded or could not be unloaded: {path}")


def cmd_file_show(files: FileManager, path: str) -> None:
    """Display the content of a loaded file with syntax highlighting.

    Parameters
    ----------
    files:
        The active :class:`FileManager` instance.
    path:
        Path to the loaded file to display.
    """
    content = files.get_content(path)
    if content is None:
        print_error(
            f"File not loaded: {path}.  Use /file {path} to load it first."
        )
        return

    max_chars = 4000
    if len(content) > max_chars:
        display = content[:max_chars] + "\n\n\u2026 [truncated]"
    else:
        display = content

    # Determine language from extension
    ext = path.rsplit(".", 1)[-1] if "." in path else ""
    language_map = {
        "py": "python",
        "js": "javascript",
        "ts": "typescript",
        "tsx": "typescript",
        "jsx": "javascript",
        "rs": "rust",
        "go": "go",
        "java": "java",
        "rb": "ruby",
        "c": "c",
        "cpp": "cpp",
        "h": "c",
        "hpp": "cpp",
        "css": "css",
        "html": "html",
        "md": "markdown",
        "json": "json",
        "yaml": "yaml",
        "yml": "yaml",
        "toml": "toml",
        "sh": "bash",
        "bash": "bash",
        "ps1": "powershell",
    }
    language = language_map.get(ext, "")

    print_code_block(display, language=language)


def cmd_file_pin(
    context: ContextManager, files: FileManager, path: str
) -> None:
    """Pin a file to prevent accidental unloading.

    Parameters
    ----------
    context:
        The active :class:`ContextManager` (handles pinning).
    files:
        The active :class:`FileManager` (used to verify the file is loaded).
    path:
        Path to the file to pin.
    """
    if not files.is_loaded(path):
        print_error(
            f"Cannot pin {path}.  Load it with /file {path} first."
        )
        return
    if context.pin_file(path):
        print_success(f"Pinned: {path}")
    else:
        print_error(f"Failed to pin {path}.")


def cmd_file_unpin(context: ContextManager, path: str) -> None:
    """Remove a pin from a file.

    Parameters
    ----------
    context:
        The active :class:`ContextManager` (handles unpinning).
    path:
        Path to the file to unpin.
    """
    context.unpin_file(path)
    print_success(f"Unpinned: {path}")
