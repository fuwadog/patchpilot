"""Terminal display helpers."""
from __future__ import annotations
import os
import sys


class Display:
    """Centralises all terminal output so the rest of the app stays I/O-free."""

    def __init__(self):
        self._tty = sys.stdout.isatty() and os.getenv("NO_COLOR") is None
        self._DIM = "\033[90m" if self._tty else ""
        self._RED = "\033[31m" if self._tty else ""
        self._GREEN = "\033[32m" if self._tty else ""
        self._YELLOW = "\033[33m" if self._tty else ""
        self._BLUE = "\033[34m" if self._tty else ""
        self._MAGENTA = "\033[35m" if self._tty else ""
        self._CYAN = "\033[36m" if self._tty else ""
        self._BOLD = "\033[1m" if self._tty else ""
        self._RESET = "\033[0m" if self._tty else ""

    def stream(self, text: str) -> None:
        """Print streamed model content inline."""
        print(text, end="", flush=True)

    def reasoning(self, text: str) -> None:
        """Print reasoning/thinking tokens in dim colour."""
        print(f"{self._DIM}{text}{self._RESET}", end="", flush=True)

    def info(self, text: str) -> None:
        print(f"{self._BLUE if self._tty else ''}{text}{self._RESET}")

    def success(self, text: str) -> None:
        print(f"{self._GREEN}✓ {text}{self._RESET}")

    def warning(self, text: str) -> None:
        print(f"{self._YELLOW}⚠ {text}{self._RESET}")

    def error(self, text: str) -> None:
        print(f"{self._RED}Error: {text}{self._RESET}")

    def newline(self) -> None:
        print()

    def separator(self, char: str = "-", width: int = 60) -> None:
        print(f"{self._DIM}{char * width}{self._RESET}")

    def assistant_header(self) -> None:
        print(f"\n{self._MAGENTA}Assistant:{self._RESET} ", end="", flush=True)

    def table(self, headers: list[str], rows: list[list[str]]) -> None:
        """Print a simple ASCII table."""
        if not rows:
            return

        # Calculate col widths
        widths = [len(h) for h in headers]
        for row in rows:
            for i, val in enumerate(row):
                widths[i] = max(widths[i], len(str(val)))

        # Header
        head_str = "  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
        print(f"{self._BOLD}{head_str}{self._RESET}")
        print(f"{self._DIM}{'-' * (sum(widths) + 2 * (len(headers) - 1))}{self._RESET}")

        # Rows
        for row in rows:
            row_str = "  ".join(str(val).ljust(widths[i]) for i, val in enumerate(row))
            print(row_str)
