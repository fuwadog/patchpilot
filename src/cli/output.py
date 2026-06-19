"""Rich output layer for the PatchPilot CLI.

All interactive output flows through this module so that callers never touch
``print()`` or ``console.print()`` directly.  Every function accepts plain
strings and wraps them in the appropriate Rich renderable with the
Catppuccin Mocha theme.

Two global consoles are provided:

* ``console`` — writes to **stderr** (interactive TUI / status).
* ``output_console`` — writes to **stdout** (piped / machine-readable data).

Importing
---------
    >>> from src.cli.output import console, print_success, streaming_context
    >>> console.print("[bold]Hello[/]")
    >>> print_success("Done.")
"""

from __future__ import annotations

import difflib
import sys
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Callable, Generator

from rich import box
from rich.console import Console, Group
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.spinner import Spinner
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from .theme import PATCHPILOT_THEME

# ---------------------------------------------------------------------------
# Console singletons
# ---------------------------------------------------------------------------

console = Console(theme=PATCHPILOT_THEME, file=sys.stderr, highlight=False)
"""Interactive console — writes to *stderr*.  Use for all user-facing output."""

output_console = Console(theme=PATCHPILOT_THEME, highlight=False)
"""Piped console — writes to *stdout*.  Use for machine-readable / JSON output."""

# ---------------------------------------------------------------------------
# Streaming state (used by print_streaming_* functions)
# ---------------------------------------------------------------------------

_streaming_live: Live | None = None
"""Active :class:`Live` instance while a streaming session is in progress."""


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def print_welcome(model: str = "PatchPilot", version: str = "1.0.0") -> None:
    """Print a welcome banner with model name and version.

    Parameters
    ----------
    model:
        The model or assistant name to display.
    version:
        Semver string shown in the banner.
    """
    try:
        welcome_text = Text()
        welcome_text.append(f"{model} ", style="title")
        welcome_text.append(f"v{version}", style="muted")
        welcome_text.append("\nTerminal-native AI code assistant", style="subtitle")

        hint = Text("\n\nType ", style="dim")
        hint.append("/help", style="command")
        hint.append(" for available commands or start typing a message.", style="dim")

        panel = Panel(
            Group(welcome_text, hint),
            title="[accent]Ready[/]",
            border_style="border",
            padding=(1, 2),
        )
        console.print(panel)
    except Exception:
        # Graceful fallback — never crash on formatting
        console.print(f"{model} v{version} — Terminal AI code assistant")


def print_help() -> None:
    """Print a Rich-formatted help table with all commands."""
    try:
        table = Table(
            title="[title]Commands[/]",
            title_style="title",
            box=box.ROUNDED,
            border_style="border",
            header_style="bold",
        )
        table.add_column("Command", style="command", no_wrap=True)
        table.add_column("Description", style="value")
        table.add_column("Shortcut", style="hint", no_wrap=True)

        rows: list[tuple[str, str, str]] = [
            ("/exit", "Quit the assistant", "/q"),
            ("/reset", "Clear conversation (keeps files)", ""),
            ("/help", "Show this help", "/h"),
            ("", "", ""),
            ("[bold]File management[/]", "", ""),
            ("/file <path>", "Load a file", "/f"),
            ("/folder <path>", "Load all files from a folder", ""),
            ("/list", "List loaded files", "/l"),
            ("/show <path>", "Show file content", ""),
            ("/unload <path>", "Unload a file", ""),
            ("/unload-all", "Unload non-pinned files", ""),
            ("/unload-folder <path>", "Unload files from a folder", ""),
            ("/unload-pattern <glob>", "Unload files matching a glob", ""),
            ("", "", ""),
            ("[bold]Code operations[/]", "", ""),
            ("/fix <path> [instr]", "Fix bugs in a file", ""),
            ("/refactor <path> [instr]", "Refactor a file", ""),
            ("/patch <path> [instr]", "Produce & apply a patch", ""),
            ("", "", ""),
            ("[bold]Snippets & Pins[/]", "", ""),
            ("/pin <path>", "Pin a file", ""),
            ("/unpin <path>", "Remove pin", ""),
            ("/snippet save <name>", "Save last code block", ""),
            ("/snippet show <name>", "Show saved snippet", ""),
            ("/snippet list", "List snippets", ""),
            ("/snippet del <name>", "Delete snippet", ""),
            ("", "", ""),
            ("[bold]Sessions[/]", "", ""),
            ("/history", "Show recent sessions", ""),
            ("/resume [id]", "Resume a session", ""),
            ("", "", ""),
            ("[bold]Info[/]", "", ""),
            ("/tokens", "Estimate token usage", ""),
            ("/context-info", "Detailed context stats", ""),
        ]

        for cmd, desc, shortcut in rows:
            if not cmd and not desc:
                table.add_section()
                continue
            if cmd.startswith("[bold]"):
                table.add_section()
                table.add_row(cmd, "", "", style="label")
                continue
            table.add_row(cmd, desc, shortcut)

        console.print(table)
    except Exception:
        console.print(
            "[command]/exit[/]  — Quit\n"
            "[command]/help[/]  — Show help\n"
            "[command]/file[/] <path> — Load a file\n"
            "[command]/list[/]  — List loaded files\n"
            "Use [command]/help[/] in the app for the full list."
        )


def print_panel(
    content: str | Text | Markdown,
    title: str = "",
    style: str = "border",
) -> None:
    """Print a bordered panel with an optional title.

    Parameters
    ----------
    content:
        The body of the panel — plain text, :class:`Text`, or :class:`Markdown`.
    title:
        Optional title shown in the top-left border.
    style:
        Named style for the border (default ``\"border\"``).
    """
    try:
        panel = Panel(content, title=title, border_style=style, padding=(1, 2))
        console.print(panel)
    except Exception:
        if title:
            console.print(f"[{style}]{title}[/]")
        console.print(str(content))


def print_user_message(text: str) -> None:
    """Print a user message with the ``[user]`` label style.

    Parameters
    ----------
    text:
        The raw message text.
    """
    try:
        label = Text("You", style="user")
        body = Text(f"\n{text}", style="default")
        console.print(Group(label, body))
    except Exception:
        console.print(f"You: {text}")


def print_assistant_message(text: str) -> None:
    """Print an assistant response, rendering Markdown when possible.

    Falls back to plain text if Markdown rendering fails.

    Parameters
    ----------
    text:
        The response string (may contain Markdown).
    """
    try:
        label = Text("Assistant", style="assistant")
        body = Markdown(text)
        console.print(Group(label, Panel(body, border_style="border", padding=(1, 2))))
    except Exception:
        console.print(f"Assistant: {text}")


def print_system_message(text: str) -> None:
    """Print a dim, italic system notification.

    Parameters
    ----------
    text:
        The system message text.
    """
    try:
        console.print(Text(text, style="system"))
    except Exception:
        console.print(text)


def print_error(text: str) -> None:
    """Print a red-bordered error panel.

    Parameters
    ----------
    text:
        Error description.
    """
    try:
        panel = Panel(
            Text(text, style="error"),
            title="[error]ERROR[/]",
            border_style="error",
            padding=(1, 2),
        )
        console.print(panel)
    except Exception:
        console.print(f"Error: {text}")


def print_success(text: str) -> None:
    """Print a green-bordered success notification.

    Parameters
    ----------
    text:
        Success message.
    """
    try:
        panel = Panel(
            Text(text, style="success"),
            title="[success]SUCCESS[/]",
            border_style="success",
            padding=(1, 2),
        )
        console.print(panel)
    except Exception:
        console.print(f"Success: {text}")


def print_warning(text: str) -> None:
    """Print a yellow-bordered warning notification.

    Parameters
    ----------
    text:
        Warning message.
    """
    try:
        panel = Panel(
            Text(text, style="warning"),
            title="[warning]WARNING[/]",
            border_style="warning",
            padding=(1, 2),
        )
        console.print(panel)
    except Exception:
        console.print(f"Warning: {text}")


def print_info(text: str) -> None:
    """Print a blue-bordered info notification.

    Parameters
    ----------
    text:
        Info message.
    """
    try:
        panel = Panel(
            Text(text, style="info"),
            title="[info]ℹ Info[/]",
            border_style="info",
            padding=(1, 2),
        )
        console.print(panel)
    except Exception:
        console.print(f"Info: {text}")


# ---------------------------------------------------------------------------
# Streaming helpers
# ---------------------------------------------------------------------------


def print_streaming_start() -> None:
    """Show a ``\"Thinking…\"`` spinner on stderr.

    Must be paired with :func:`print_streaming_end`.  Between calls use
    :func:`print_streaming_delta` to update the displayed text.
    """
    global _streaming_live
    try:
        spinner = Spinner("dots", Text("Thinking…", style="italic"))
        _streaming_live = Live(spinner, console=console, refresh_per_second=10)
        _streaming_live.start()
    except Exception:
        console.print("Thinking…", style="dim", end="")


def print_streaming_delta(text: str) -> None:
    """Update the streaming display with the latest token(s).

    Parameters
    ----------
    text:
        The accumulated response text so far (or the latest delta).
    """
    global _streaming_live
    if _streaming_live is not None:
        try:
            # Render the accumulated text as a styled panel
            content = Text(text)
            _streaming_live.update(content)
        except Exception:
            pass


def print_streaming_end() -> None:
    """Finalise the streaming spinner and print the complete response."""
    global _streaming_live
    if _streaming_live is not None:
        try:
            _streaming_live.stop()
        except Exception:
            pass
        _streaming_live = None


@contextmanager
def streaming_context() -> Generator[Callable[[str], None], None, None]:
    """Context manager for streaming :class:`Live` display.

    Yields a callback that accepts the *latest* text string and refreshes
    the display in-place.  The spinner is shown until the context exits.

    Example
    -------
        >>> with streaming_context() as update:
        ...     for token in stream:
        ...         update(token)
    """
    spinner = Spinner("dots", Text("Thinking…", style="italic"))
    live = Live(spinner, console=console, refresh_per_second=10)

    def _update(text: str) -> None:
        try:
            content = Text(text)
            live.update(content)
        except Exception:
            pass

    try:
        live.start()
        yield _update
    finally:
        live.stop()


# ---------------------------------------------------------------------------
# File & context display
# ---------------------------------------------------------------------------


def print_file_list(
    paths: list[str],
    tags: dict[str, str] | None = None,
) -> None:
    """Print a table of loaded files with optional status tags.

    Parameters
    ----------
    paths:
        List of file paths to display.
    tags:
        Optional mapping of ``path -> tag`` (e.g. ``\"pinned\"``, ``\"modified\"``,
        ``\"new\"``).  Paths without an entry get no tag.
    """
    try:
        if not paths:
            console.print("[dim]No files loaded.[/]")
            return

        table = Table(
            title="[title]Loaded Files[/]",
            box=box.SIMPLE,
            border_style="border",
            header_style="bold",
        )
        table.add_column("#", style="dim", width=3)
        table.add_column("Path", style="file.path")
        table.add_column("Tag", style="file.tag", width=14, no_wrap=True)

        for idx, path in enumerate(paths, start=1):
            tag = (tags or {}).get(path, "")
            table.add_row(str(idx), path, tag)

        console.print(table)
    except Exception:
        for p in paths:
            console.print(p)


def print_context_stats(stats: dict[str, Any]) -> None:
    """Print estimated token usage and file statistics as a panel.

    Expected ``stats`` keys
    -----------------------
    total_tokens, max_total, file_count, pinned_count, files (list of dicts
    with keys ``path``, ``tokens``, ``pinned``).
    """
    try:
        total = stats.get("total_tokens", 0)
        max_total = stats.get("max_total", 0)
        file_count = stats.get("file_count", 0)
        pinned_count = stats.get("pinned_count", 0)

        info = Text()
        info.append("Tokens:  ", style="label")
        info.append(f"{total:,} / {max_total:,}", style="value")
        info.append("\nFiles:   ", style="label")
        info.append(f"{file_count} ({pinned_count} pinned)", style="value")

        # Per-file breakdown
        file_details = stats.get("files", [])
        if file_details:
            info.append("\n\n", style="default")
            for f in file_details:
                path = f.get("path", "?")
                tokens = f.get("tokens", 0)
                pinned = " 📌" if f.get("pinned") else ""
                info.append(f"\n  {path}", style="file.path")
                info.append(f"  ~{tokens} tok{pinned}", style="file.meta")

        panel = Panel(
            info,
            title="[title]Context Stats[/]",
            border_style="border",
            padding=(1, 2),
        )
        console.print(panel)
    except Exception:
        console.print(f"Tokens: {stats.get('total_tokens', 0)}")


def print_session_list(sessions: list[dict[str, Any]]) -> None:
    """Print a table of past sessions.

    Each ``sessions`` entry should have keys:
    ``id``, ``title``, ``message_count`` (or ``message_count``), ``created_at``.

    Parameters
    ----------
    sessions:
        List of session dicts from the session store.
    """
    try:
        if not sessions:
            console.print("[dim]No saved sessions.[/]")
            return

        table = Table(
            title="[title]Sessions[/]",
            box=box.ROUNDED,
            border_style="border",
            header_style="bold",
            leading=1,
        )
        table.add_column("ID", style="command", no_wrap=True, width=12)
        table.add_column("Title", style="file.name")
        table.add_column("Messages", style="value", justify="right", width=9)
        table.add_column("Created", style="dim", width=16)

        for s in sessions:
            session_id = s.get("id", "?")[:12]
            title = s.get("title", "Untitled") or "Untitled"
            msg_count = s.get("message_count", s.get("message_count", 0))
            created = s.get("created_at", "")
            if isinstance(created, datetime):
                created = created.strftime("%Y-%m-%d %H:%M")
            else:
                created = str(created)[:16]
            table.add_row(session_id, title, str(msg_count), created)

        console.print(table)
    except Exception:
        for s in sessions:
            console.print(f"{s.get('id', '?')}  {s.get('title', 'Untitled')}")


# ---------------------------------------------------------------------------
# Code & diff display
# ---------------------------------------------------------------------------


def print_code_block(code: str, language: str = "") -> None:
    """Print a syntax-highlighted code block.

    Uses :class:`rich.syntax.Syntax` for highlighting with auto-detection of
    the language when *language* is empty.

    Parameters
    ----------
    code:
        The source code to display.
    language:
        Language hint for the highlighter (e.g. ``\"python\"``, ``\"typescript\"``).
        If empty, Rich will attempt auto-detection.
    """
    try:
        lexer = language if language else "guess"
        syntax = Syntax(
            code,
            lexer,
            theme="monokai",
            line_numbers=True,
            word_wrap=True,
            padding=(1, 2),
        )
        console.print(syntax)
    except Exception:
        console.print(f"```{language}")
        console.print(code)
        console.print("```")


def print_diff(
    old: str,
    new: str,
    filename: str = "",
) -> None:
    """Print a unified diff between two strings with inline colour.

    Parameters
    ----------
    old:
        Original content.
    new:
        Modified content.
    filename:
        Optional file name shown in the diff header.
    """
    try:
        diff_lines = list(
            difflib.unified_diff(
                old.splitlines(keepends=True),
                new.splitlines(keepends=True),
                fromfile=filename or "original",
                tofile=filename or "modified",
                lineterm="",
            )
        )

        if not diff_lines:
            console.print("[dim]No differences.[/]")
            return

        highlighted: list[Text] = []
        for line in diff_lines:
            if (
                line.startswith("+++")
                or line.startswith("---")
                or line.startswith("@@")
            ):
                highlighted.append(Text(line.rstrip(), style="accent"))
            elif line.startswith("+"):
                highlighted.append(Text(line.rstrip(), style="success"))
            elif line.startswith("-"):
                highlighted.append(Text(line.rstrip(), style="error"))
            else:
                highlighted.append(Text(line.rstrip(), style="dim"))

        diff_panel = Panel(
            Group(*highlighted),
            title=f"[title]Diff — {filename or '(unnamed)'}[/]",
            border_style="border",
            padding=(1, 2),
        )
        console.print(diff_panel)
    except Exception:
        console.print(f"Diff for {filename or '(unnamed)'}:")


# ---------------------------------------------------------------------------
# Status bar
# ---------------------------------------------------------------------------


def print_status(
    model: str,
    provider: str,
    tokens_used: int,
    files_loaded: int,
) -> None:
    """Print a status panel summarising the current session.

    Parameters
    ----------
    model:
        The active model name.
    provider:
        The provider (e.g. ``\"openai\"``, ``\"ollama\"``).
    tokens_used:
        Total tokens consumed in the session.
    files_loaded:
        Number of files currently loaded.
    """
    try:
        info = Text()
        info.append("Model:   ", style="label")
        info.append(f"{model}", style="value")
        info.append("\nProvider: ", style="label")
        info.append(f"{provider}", style="value")
        info.append("\nTokens:  ", style="label")
        info.append(f"{tokens_used:,}", style="value")
        info.append("\nFiles:   ", style="label")
        info.append(f"{files_loaded}", style="value")

        panel = Panel(
            info,
            title="[title]Session Status[/]",
            border_style="border",
            padding=(1, 2),
            width=40,
        )
        console.print(panel)
    except Exception:
        console.print(
            f"Status: {model} ({provider}) — {tokens_used} tokens,"
            f" {files_loaded} files"
        )


# ---------------------------------------------------------------------------
# Interactive prompts
# ---------------------------------------------------------------------------


def confirm(prompt: str = "Are you sure?") -> bool:
    """Ask the user a yes/no question and return the answer.

    Parameters
    ----------
    prompt:
        The question to display.

    Returns
    -------
    True if the user answered ``y`` / ``yes``, False otherwise.
    """
    from rich.prompt import Confirm as RichConfirm

    try:
        return RichConfirm.ask(prompt, console=console, default=False)
    except Exception:
        # Fallback for non-interactive environments
        console.print(f"{prompt} [dim](y/n)[/]", end=" ")
        try:
            answer = input().strip().lower()
            return answer in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            return False
