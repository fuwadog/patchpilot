"""Catppuccin Mocha colour theme for Rich.

Provides a :class:`rich.theme.Theme` named ``PATCHPILOT_THEME`` with every
named style used by the PatchPilot CLI.  Use it by passing ``theme=`` to any
:class:`rich.console.Console`, e.g.::

    >>> from rich.console import Console
    >>> from src.cli.theme import PATCHPILOT_THEME
    >>> console = Console(theme=PATCHPILOT_THEME)
    >>> console.print("[success]All good![/]")
"""

from __future__ import annotations

from rich.theme import Theme as RichTheme

# ---------------------------------------------------------------------------
# Catppuccin Mocha palette
# ---------------------------------------------------------------------------
# Reference: https://github.com/catppuccin/catppuccin
_PENCIL = "#89b4fa"       # Blue        — primary / processing
_PURPLE = "#cba6f7"       # Purple      — secondary
_LAVENDER = "#b4befe"     # Lavender    — accent
_YELLOW = "#f9e2af"       # Yellow      — warning
_RED = "#f38ba8"          # Red         — error
_GREEN = "#a6e3a1"        # Green       — success
_TEXT = "#cdd6f4"         # Text        — foreground
_BG = "#1e1e2e"           # App bg      — background / badge-text
_SURFACE = "#181825"      # Card/bar bg — surface
_PANEL = "#313244"        # Hover/panel — panel
_BORDER = "#45475a"       # Borders     — border-dim
_SUBTEXT0 = "#a6adc8"     # Dim text
_SUBTEXT1 = "#bac2de"     # Less-dim text
_OVERLAY2 = "#9399b2"     # Meta text
_INFO = "#74c7ec"         # Info blue

PATCHPILOT_THEME = RichTheme(
    {
        # ------------------------------------------------------------------
        # Base styles
        # ------------------------------------------------------------------
        "default": _TEXT,
        "bold": f"bold {_TEXT}",
        "dim": _SUBTEXT0,
        "italic": f"italic {_SUBTEXT1}",
        "error": _RED,
        "warning": _YELLOW,
        "success": _GREEN,
        "info": _INFO,
        # ------------------------------------------------------------------
        # UI component styles
        # ------------------------------------------------------------------
        "title": f"bold {_TEXT}",
        "subtitle": f"italic {_SUBTEXT1}",
        "label": f"bold {_TEXT}",
        "value": _SUBTEXT1,
        "hint": f"italic {_OVERLAY2}",
        "border": _BORDER,
        "accent": _LAVENDER,
        "muted": _SUBTEXT0,
        # ------------------------------------------------------------------
        # Status badge styles
        # ------------------------------------------------------------------
        "badge.processing": f"bold {_BG} on {_PENCIL}",
        "badge.info": f"bold {_BG} on {_INFO}",
        "badge.succeeded": f"bold {_BG} on {_GREEN}",
        "badge.warning": f"bold {_BG} on {_YELLOW}",
        "badge.failed": f"bold {_BG} on {_RED}",
        # ------------------------------------------------------------------
        # Message styles (conversation roles)
        # ------------------------------------------------------------------
        "user": f"bold {_PENCIL}",
        "assistant": f"bold {_GREEN}",
        "system": f"italic {_OVERLAY2}",
        "command": f"bold {_PURPLE}",
        "code": f"{_LAVENDER} on {_SURFACE}",
        # ------------------------------------------------------------------
        # File-related styles
        # ------------------------------------------------------------------
        "file.name": f"bold {_TEXT}",
        "file.path": _SUBTEXT1,
        "file.tag": f"bold {_BG} on {_PENCIL}",
        "file.meta": f"italic {_OVERLAY2}",
        # ------------------------------------------------------------------
        # Callout styles
        # ------------------------------------------------------------------
        "callout.info": f"bold {_INFO}",
        "callout.warning": f"bold {_YELLOW}",
        "callout.error": f"bold {_RED}",
        "callout.success": f"bold {_GREEN}",
    },
    # Infer styles on unknown tags so that [unknown]text[/] still uses the
    # colour as a literal ANSI colour name when possible.
    inherit=True,
)
