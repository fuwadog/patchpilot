"""Interactive REPL for PatchPilot.

Provides a readline-backed command prompt with:
  - Command history (arrow keys via ``readline``)
  - ``/``-prefixed commands (e.g. ``/file``, ``/fix``, ``/help``)
  - Plain-text messages sent to the AI with streaming Rich output
  - Ctrl+C cancellation, Ctrl+D / ``/exit`` to quit

Usage
-----
    from src.cli.repl import REPL
    repl = REPL(...)
    repl.run()
"""

from __future__ import annotations

import asyncio
import os
from typing import Optional

# readline is not available on Windows; provide a no-op fallback.
try:
    import readline  # noqa: F401
except ImportError:
    try:
        import pyreadline3 as readline  # type: ignore[no-redef]
    except ImportError:
        readline = None  # type: ignore[assignment]

from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text

from ..client.base import ModelProvider
from ..config import Config
from ..context.manager import ContextManager
from ..files.manager import FileManager
from ..files.patching import PatchManager
from ..files.snippets import SnippetManager
from ..session.manager import SessionManager
from ..session.store import SessionStore
from .commands.file import (
    cmd_file_add,
    cmd_file_folder,
    cmd_file_list,
    cmd_file_pin,
    cmd_file_remove,
    cmd_file_show,
    cmd_file_unpin,
)
from .commands.session import (
    cmd_history,
    cmd_resume,
    cmd_snippet,
)
from .dispatcher import CommandDispatcher
from .output import (
    console,
    print_assistant_message,
    print_error,
    print_help,
    print_info,
    print_success,
    print_system_message,
    print_user_message,
    print_warning,
    print_welcome,
    streaming_context,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_HISTFILE = os.path.expanduser("~/.patchpilot_history")
_HISTORY_MAX = 2000
_RICH_TAG_RE = None  # Unused in the REPL — we display via Rich directly


# ---------------------------------------------------------------------------
# Streaming display adapter
# ---------------------------------------------------------------------------


class _StreamingDisplay:
    """Adapter that routes ``SessionManager`` display calls to Rich output.

    ``SessionManager.send()`` calls back into this object as chunks arrive.
    This adapter shows a "Thinking…" spinner initially, then replaces it
    with the accumulated response text.  On completion, the final message
    is printed as a formatted assistant panel.

    Methods called by ``SessionManager``
    ------------------------------------
    - ``stream(text)`` — called with each content delta
    - ``reasoning(text)`` — called with reasoning content (ignored here)
    - ``newline()`` — called at the end of streaming
    - ``info(text)`` — informational message (interruption, status)
    - ``error(text)`` — error message
    """

    def __init__(self) -> None:
        self._accumulated: str = ""
        self._ctx: Optional[streaming_context] = None  # type: ignore[assignment]
        self._update = None
        self._started: bool = False

    def reasoning(self, text: str) -> None:
        """Called when the provider streams reasoning tokens (ignored in CLI)."""
        pass  # Reasoning is typically verbose — omit from CLI output

    def stream(self, text: str) -> None:
        """Called with each content chunk from the provider."""
        if not self._started:
            # Begin the Live display on first content token
            self._started = True
            spinner = Spinner("dots", Text("Thinking\u2026", style="italic"))
            self._live = Live(
                spinner, console=console, refresh_per_second=10, transient=True
            )
            self._live.start()

        self._accumulated += text
        if self._started and hasattr(self, "_live"):
            try:
                self._live.update(Text(self._accumulated))
            except Exception:
                pass

    def newline(self) -> None:
        """Finalise streaming and print the complete response."""
        self._cleanup_live()
        if self._accumulated:
            print_assistant_message(self._accumulated)
            self._accumulated = ""

    def info(self, text: str) -> None:
        """Display an informational / status message (e.g. stream cancelled)."""
        self._cleanup_live()
        # Reset accumulated so we don't re-print stale text
        self._accumulated = ""
        print_system_message(text.strip())

    def error(self, text: str) -> None:
        """Display an error message."""
        self._cleanup_live()
        self._accumulated = ""
        print_error(text.strip())

    def _cleanup_live(self) -> None:
        """Stop the Live display if it is active."""
        if hasattr(self, "_live") and self._live is not None:
            try:
                self._live.stop()
            except Exception:
                pass
            self._live = None
        self._started = False

    def __del__(self) -> None:
        self._cleanup_live()


# ---------------------------------------------------------------------------
# REPL
# ---------------------------------------------------------------------------


class REPL:
    """Interactive command-line REPL for PatchPilot.

    Parameters
    ----------
    config:
        Application configuration.
    provider:
        Active model provider.
    context:
        Token-aware context manager.
    files:
        File manager for loading / unloading files.
    patch:
        Patch manager for safe file writes.
    snippets:
        In-memory snippet manager.
    session:
        Session manager for AI interactions.
    store:
        Async session store for persistence.
    session_id:
        UUID of the current session.
    loop:
        Active ``asyncio`` event loop (shared for DB operations).
    """

    def __init__(
        self,
        config: Config,
        provider: ModelProvider,
        context: ContextManager,
        files: FileManager,
        patch: PatchManager,
        snippets: SnippetManager,
        session: SessionManager,
        store: SessionStore,
        session_id: str,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        self._config = config
        self._provider = provider
        self._context = context
        self._files = files
        self._patch = patch
        self._snippets = snippets
        self._session = session
        self._store = store
        self._session_id = session_id
        self._loop = loop

        # State
        self._running = False
        self._last_response: Optional[str] = None

        # Readline history
        self._setup_readline()

    # ------------------------------------------------------------------
    # Readline setup
    # ------------------------------------------------------------------

    def _setup_readline(self) -> None:
        """Configure ``readline`` for input history and tab completion.

        Falls back gracefully when ``readline`` is unavailable (Windows).
        """
        if readline is None:
            return  # No readline available — no history or tab-completion

        try:
            readline.read_history_file(_HISTFILE)  # type: ignore[union-attr]
        except FileNotFoundError:
            pass
        except PermissionError:
            pass  # Non-fatal — skip history persistence

        readline.set_history_length(_HISTORY_MAX)  # type: ignore[union-attr]

        # Tab completion
        readline.set_completer(self._tab_complete)  # type: ignore[union-attr]
        readline.parse_and_bind("tab: complete")  # type: ignore[union-attr]

        # Register history save on exit
        import atexit

        atexit.register(self._save_history)

    def _save_history(self) -> None:
        """Persist readline history to disk."""
        if readline is None:
            return
        try:
            readline.write_history_file(_HISTFILE)  # type: ignore[union-attr]
        except (PermissionError, OSError):
            pass

    def _tab_complete(self, text: str, state: int) -> Optional[str]:
        """Simple tab completion for commands and file paths."""
        if readline is None:
            return None

        # Build candidate list
        commands = [
            "/exit",
            "/quit",
            "/q",
            "/help",
            "/h",
            "/reset",
            "/tokens",
            "/list",
            "/l",
            "/file",
            "/f",
            "/folder",
            "/show",
            "/unload",
            "/unload-all",
            "/unload-folder",
            "/unload-pattern",
            "/pin",
            "/unpin",
            "/context-info",
            "/fix",
            "/refactor",
            "/patch",
            "/snippet",
            "/history",
            "/resume",
        ]

        if text.startswith("/"):
            candidates = [c for c in commands if c.startswith(text)]
        else:
            # File path completion (basic)
            candidates = []
            prefix = text or "."
            try:
                basedir = os.path.dirname(prefix) or "."
                partial = os.path.basename(prefix)
                for entry in os.listdir(basedir):
                    full = os.path.join(basedir, entry)
                    if entry.startswith(partial) or not partial:
                        candidates.append(
                            full + "/" if os.path.isdir(full) else full
                        )
            except PermissionError:
                pass
            candidates.sort()

        try:
            return candidates[state] if state < len(candidates) else None
        except IndexError:
            return None

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Run the REPL main loop until the user exits."""
        self._running = True
        print_welcome(model=self._config.MODEL)

        while self._running:
            try:
                user_input = input("patchpilot> ")
            except EOFError:
                # Ctrl+D
                print()
                self._confirm_and_exit()
                break
            except KeyboardInterrupt:
                # Ctrl+C during prompt — go to next line
                print()
                continue

            user_input = user_input.strip()
            if not user_input:
                continue

            if user_input.startswith("/"):
                self._handle_command(user_input)
            else:
                self._handle_chat(user_input)

    # ------------------------------------------------------------------
    # Command dispatch
    # ------------------------------------------------------------------

    # fmt: off
    _COMMAND_MAP = {
        "/exit":       "_cmd_exit",
        "/quit":       "_cmd_exit",
        "/q":          "_cmd_exit",
        "/help":       "_cmd_help",
        "/h":          "_cmd_help",
        "/reset":      "_cmd_reset",
        "/tokens":     "_cmd_tokens",
        "/list":       "_cmd_list",
        "/l":          "_cmd_list",
        "/file":       "_cmd_file",
        "/f":          "_cmd_file",
        "/folder":     "_cmd_folder",
        "/show":       "_cmd_show",
        "/unload":     "_cmd_unload",
        "/unload-all": "_cmd_unload_all",
        "/unload-folder": "_cmd_unload_folder",
        "/unload-pattern": "_cmd_unload_pattern",
        "/pin":        "_cmd_pin",
        "/unpin":      "_cmd_unpin",
        "/context-info": "_cmd_context_info",
        "/snippet":    "_cmd_snippet",
        "/history":    "_cmd_history",
        "/resume":     "_cmd_resume",
        "/fix":        "_cmd_fix",
        "/refactor":   "_cmd_refactor",
        "/patch":      "_cmd_patch",
    }
    # fmt: on

    def _handle_command(self, raw: str) -> None:
        """Dispatch a ``/``-prefixed command.

        Splits the input into (command, args) and delegates to the
        appropriate ``_cmd_*`` handler.
        """
        parts = raw.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1].strip() if len(parts) > 1 else ""

        handler_name = self._COMMAND_MAP.get(cmd)
        if handler_name is None:
            print_warning(
                f"Unknown command: {cmd}.  Type /help for available commands."
            )
            return

        handler = getattr(self, handler_name, None)
        if handler is None:
            print_error(f"Internal error: no handler for {cmd}")
            return

        handler(args)

    # ------------------------------------------------------------------
    # Chat handling
    # ------------------------------------------------------------------

    def _handle_chat(self, text: str) -> None:
        """Send a plain-text message to the AI with streaming output.

        Creates a temporary ``SessionManager`` with a Rich-aware display
        adapter so the response streams token-by-token.
        """
        print_user_message(text)

        display = _StreamingDisplay()
        chat_session = SessionManager(
            provider=self._provider,
            context=self._context,
            display=display,
            temperature=self._config.TEMPERATURE,
            max_tokens=self._config.MAX_RESPONSE_TOKENS,
        )

        try:
            response = chat_session.send(text, record_in_history=True)
        except KeyboardInterrupt:
            display.info("\n[Stream interrupted by user]")
            return

        if response:
            self._last_response = response
            # Persist to session database
            self._async_db_op(
                lambda: self._do_save_messages(text, response)
            )

    async def _do_save_messages(
        self, user_msg: str, assistant_msg: str
    ) -> None:
        """Save a user/assistant message pair to the session store."""
        if not self._store:
            return
        try:
            await self._store.add_message(
                self._session_id, "user", user_msg
            )
            await self._store.add_message(
                self._session_id, "assistant", assistant_msg
            )
        except Exception as exc:
            print_error(f"Failed to persist messages: {exc}")

    def _async_db_op(self, coro_factory: callable) -> None:
        """Run an async DB operation on the shared event loop.

        Parameters
        ----------
        coro_factory:
            A zero-arg callable that returns a coroutine.
        """
        try:
            self._loop.run_until_complete(coro_factory())
        except RuntimeError:
            # Loop is closed or not in a valid state — fallback to
            # creating a one-shot event loop.
            try:
                asyncio.run(coro_factory())
            except Exception:
                pass  # Best-effort persistence
        except Exception:
            pass  # Best-effort

    # ------------------------------------------------------------------
    # Command implementations
    # ------------------------------------------------------------------

    def _cmd_exit(self, args: str = "") -> None:
        """Handle ``/exit``, ``/quit``, ``/q``."""
        self._confirm_and_exit()

    def _confirm_and_exit(self) -> None:
        """Ask for confirmation before exiting (unless force)."""
        from .output import confirm

        if confirm("\nAre you sure you want to exit?"):
            self._running = False
            print_system_message("Goodbye!")

    def _cmd_help(self, args: str = "") -> None:
        """Handle ``/help`` or ``/h``."""
        print_help()

    def _cmd_reset(self, args: str = "") -> None:
        """Handle ``/reset`` — clear conversation history."""
        self._session.reset()
        print_success("Conversation history cleared (loaded files retained).")

    def _cmd_tokens(self, args: str = "") -> None:
        """Handle ``/tokens`` — show estimated token usage."""
        est = self._context.estimated_total_tokens()
        max_total = self._config.MAX_TOTAL_TOKENS
        pct = int((est / max_total) * 100) if max_total else 0
        print_info(f"Estimated tokens: ~{est:,} / {max_total:,} ({pct}%)")

    def _cmd_list(self, args: str = "") -> None:
        """Handle ``/list`` or ``/l`` — list loaded files."""
        paths = self._files.loaded_paths()
        tags = {
            p: "\U0001f4cc pinned" if self._context.is_pinned(p) else ""
            for p in paths
        }
        from .output import print_file_list

        print_file_list(paths, tags)

    def _cmd_file(self, args: str = "") -> None:
        """Handle ``/file`` or ``/f`` — file management subcommands.

        Supports::

            /file add <path>        Load a file
            /file folder <path>     Load a folder
            /file list              List loaded files
            /file remove <path>     Unload a file
            /file show <path>       Show file content
            /file pin <path>        Pin a file
            /file unpin <path>      Unpin a file
            /file <path>            Load a file (shorthand)
        """
        if not args.strip():
            print_warning(
                "Usage:\n"
                "  /file <path>        Load a file\n"
                "  /file add <path>    Load a file\n"
                "  /file folder <path> Load a folder\n"
                "  /file list          List loaded files\n"
                "  /file remove <path> Unload a file\n"
                "  /file show <path>   Show file content\n"
                "  /file pin <path>    Pin a file\n"
                "  /file unpin <path>  Unpin a file"
            )
            return

        parts = args.split(maxsplit=1)
        sub = parts[0].lower()
        rest = parts[1] if len(parts) > 1 else ""

        if sub == "add" and rest:
            cmd_file_add(self._files, rest)
        elif sub == "folder" and rest:
            cmd_file_folder(self._files, rest)
        elif sub == "list":
            cmd_file_list(self._files, self._context)
        elif sub == "remove" and rest:
            cmd_file_remove(self._files, self._context, rest)
        elif sub == "show" and rest:
            cmd_file_show(self._files, rest)
        elif sub == "pin" and rest:
            cmd_file_pin(self._context, self._files, rest)
        elif sub == "unpin" and rest:
            cmd_file_unpin(self._context, rest)
        elif rest:
            # /file <path> — shorthand for add
            cmd_file_add(self._files, args)
        else:
            # Single arg that is the path
            cmd_file_add(self._files, sub)

    def _cmd_folder(self, args: str = "") -> None:
        """Handle ``/folder <path>`` — load all files from a folder."""
        if not args.strip():
            print_warning("Usage: /folder <path>")
            return
        cmd_file_folder(self._files, args.strip())

    def _cmd_show(self, args: str = "") -> None:
        """Handle ``/show <path>`` — display file content."""
        from .commands.file import cmd_file_show

        if not args.strip():
            print_warning("Usage: /show <path>")
            return
        cmd_file_show(self._files, args.strip())

    def _cmd_unload(self, args: str = "") -> None:
        """Handle ``/unload <path>``."""
        if not args.strip():
            print_warning("Usage: /unload <path>")
            return
        # Check if pinned
        path = args.strip()
        if self._context.is_pinned(path):
            print_warning(
                f"{path} is pinned.  Use /unpin first or /unload-all --force."
            )
            return
        if self._files.unload(path):
            print_success(f"Unloaded: {path}")
        else:
            print_warning(f"File not loaded or could not be unloaded: {path}")

    def _cmd_unload_all(self, args: str = "") -> None:
        """Handle ``/unload-all [--force]``."""
        force = "--force" in args.split()
        count = self._files.unload_all(keep_pinned=not force)
        print_success(f"Unloaded {count} file(s).")

    def _cmd_unload_folder(self, args: str = "") -> None:
        """Handle ``/unload-folder <path>``."""
        if not args.strip():
            print_warning("Usage: /unload-folder <path>")
            return
        count = self._files.unload_folder(args.strip())
        print_success(f"Unloaded {count} file(s) from {args.strip()}.")

    def _cmd_unload_pattern(self, args: str = "") -> None:
        """Handle ``/unload-pattern <glob>``."""
        if not args.strip():
            print_warning("Usage: /unload-pattern <glob>")
            return
        count = self._files.unload_pattern(args.strip())
        print_success(
            f"Unloaded {count} file(s) matching {args.strip()}."
        )

    def _cmd_pin(self, args: str = "") -> None:
        """Handle ``/pin <path>``."""
        if not args.strip():
            print_warning("Usage: /pin <path>")
            return
        if self._context.pin_file(args.strip()):
            print_success(f"Pinned: {args.strip()}")
        else:
            print_error(
                f"Cannot pin {args.strip()}.  Load it with /file first."
            )

    def _cmd_unpin(self, args: str = "") -> None:
        """Handle ``/unpin <path>``."""
        if not args.strip():
            print_warning("Usage: /unpin <path>")
            return
        self._context.unpin_file(args.strip())
        print_success(f"Unpinned: {args.strip()}")

    def _cmd_context_info(self, args: str = "") -> None:
        """Handle ``/context-info`` — detailed token and file stats."""
        stats = self._context.get_stats()
        from .output import print_context_stats

        print_context_stats(stats)

    def _cmd_snippet(self, args: str = "") -> None:
        """Handle ``/snippet`` — snippet management subcommands."""
        cmd_snippet(self._snippets, self._patch, self._last_response, args)

    def _cmd_history(self, args: str = "") -> None:
        """Handle ``/history`` — list recent sessions."""
        self._async_db_op(lambda: cmd_history(self._store))

    def _cmd_resume(self, args: str = "") -> None:
        """Handle ``/resume [id]`` — load a past session."""
        self._async_db_op(
            lambda: cmd_resume(
                self._store, self._context, args.strip()
            )
        )
        # Update session_id to the resumed session
        # (cmd_resume handles this internally)

    def _cmd_fix(self, args: str = "") -> None:
        """Handle ``/fix``."""
        self._cmd_code_op("/fix", args)

    def _cmd_refactor(self, args: str = "") -> None:
        """Handle ``/refactor``."""
        self._cmd_code_op("/refactor", args)

    def _cmd_patch(self, args: str = "") -> None:
        """Handle ``/patch``."""
        self._cmd_code_op("/patch", args)

    def _cmd_code_op(self, cmd: str, args: str = "") -> None:
        """Shared implementation for ``/fix``, ``/refactor``, ``/patch``.

        Parameters
        ----------
        cmd:
            One of ``"/fix"``, ``"/refactor"``, ``"/patch"``.
        args:
            Remaining argument string: ``<path> [instructions...]``
        """
        parts = args.split(maxsplit=1)
        path = parts[0] if parts else ""
        instructions = parts[1].strip() if len(parts) > 1 else ""

        if not path:
            print_warning(f"Usage: {cmd} <path> [instructions]")
            return

        if not instructions:
            print_warning(
                f"No instructions provided for {cmd}.  "
                "The AI may produce a generic response."
            )

        # Load file if not already loaded
        if not self._files.is_loaded(path):
            ok, err = self._files.load(path)
            if not ok:
                print_error(f"Cannot load file: {err}")
                return

        # Build the structured prompt (reuse dispatcher's static method)
        content = self._files.get_content(path) or ""
        prompt = CommandDispatcher._build_code_prompt(
            cmd, path, content, instructions
        )

        # Record user intent and stream the response
        self._context.add_user(f"{cmd} {path}: {instructions}")
        response = self._stream_code_response(prompt)
        if not response:
            return

        self._last_response = response
        self._apply_code_block(path)

    def _stream_code_response(self, prompt: str) -> Optional[str]:
        """Stream an AI response for a code operation.

        Parameters
        ----------
        prompt:
            The structured prompt to send.

        Returns
        -------
        The full response text, or ``None`` on interruption / failure.
        """
        display = _StreamingDisplay()
        code_session = SessionManager(
            provider=self._provider,
            context=self._context,
            display=display,
            temperature=self._config.TEMPERATURE,
            max_tokens=self._config.MAX_RESPONSE_TOKENS,
        )

        try:
            return code_session.send(prompt, record_in_history=False)
        except KeyboardInterrupt:
            display.info("\n[Code operation interrupted by user]")
            return None

    def _apply_code_block(self, path: str) -> None:
        """Extract and apply a code block from the last response.

        Parameters
        ----------
        path:
            The target file path to write to.
        """
        if not self._last_response:
            return

        new_code = self._patch.extract_code_block(self._last_response)
        if new_code:
            ok, msg = self._patch.apply(
                path=path,
                new_content=new_code,
                confirm=True,
                dry_run=False,
            )
            if ok:
                print_success(msg)
                self._files.load(path)
            else:
                print_error(msg)
        else:
            print_warning(
                "No code block found in the response.  "
                "Use /snippet save <name> to save it as a snippet."
            )
