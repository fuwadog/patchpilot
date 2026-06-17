"""CLI components: command dispatcher, autocomplete, display."""

from __future__ import annotations

from .completer import CLICompleter, setup_autocomplete
from .dispatcher import CommandDispatcher
from .display import Display

__all__ = [
    "CLICompleter",
    "setup_autocomplete",
    "CommandDispatcher",
    "Display",
]
