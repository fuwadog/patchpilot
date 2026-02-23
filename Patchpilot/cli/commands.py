"""CLI command dispatch – all command handler logic lives here."""
from __future__ import annotations
import textwrap
from typing import Optional

from session.manager import SessionManager
from files.manager import FileManager
from files.operations import PatchManager, SnippetManager
from context.manager import ContextManager
from cli.display import Display

HELP_TEXT = textwrap.dedent("""
Available commands:

  /exit                          Quit the assistant.
  /reset                         Clear conversation (keeps loaded project files).
  /help                          Show this help text.

  --- File management ---
  /file <path>                   Load a single file into project context.
  /folder <path>                 Discover and load up to MAX_FILES from a folder.
  /list                          List all loaded files.
  /show <path>                   Print truncated content of a loaded file.
  /unload <path>                 Remove a file from context.
  /unload-all [--force]          Unload all non-pinned files.
  /unload-folder <path>          Unload all files from a folder.
  /unload-pattern <glob>         Unload files matching a pattern.

  --- Code operations ---
  /fix <path> [instructions]     Ask the assistant to fix bugs in a file.
  /refactor <path> [instr]       Ask the assistant to refactor a file.
  /patch <path> [instr]          Ask assistant to produce and optionally apply a patch.

  --- Snippets & Pins ---
  /pin <path>                    Pin a file to prevent accidental unloading.
  /unpin <path>                  Remove pin from a file.
  /snippet save <name>           Save the last assistant code block as a named snippet.
  /snippet show <name>           Print a saved snippet.
  /snippet list                  List all saved snippet names.
  /snippet del <name>            Delete a snippet.

  --- Info ---
  /tokens                        Show estimated token usage.
  /context-info                  Detailed token and file stats.

Anything else is sent as a regular chat message.
""").strip()


class CommandDispatcher:
    def __init__(
        self,
        session: SessionManager,
        files: FileManager,
        context: ContextManager,
        patch: PatchManager,
        snippets: SnippetManager,
        display: Display,
        max_file_chars: int,
    ):
        self._session = session
        self._files = files
        self._ctx = context
        self._patch = patch
        self._snippets = snippets
        self._display = display
        self._max_file_chars = max_file_chars
        self._last_response: Optional[str] = None

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def dispatch(self, raw: str) -> bool:
        """
        Handle one line of user input.
        Returns False when the session should end.
        """
        raw = raw.rstrip()
        if not raw:
            return True

        parts = raw.split()
        cmd = parts[0].lower()

        if cmd == "/exit":
            return False

        if cmd == "/help":
            self._display.info(HELP_TEXT)
            return True

        if cmd == "/reset":
            self._session.reset()
            self._display.info("Conversation history cleared (project files retained).")
            return True

        if cmd == "/tokens":
            est = self._ctx.estimated_total_tokens()
            self._display.info(f"Estimated context tokens: ~{est}")
            return True

        if cmd == "/list":
            paths = self._files.loaded_paths()
            if not paths:
                self._display.info("No files loaded.")
            else:
                for p in paths:
                    self._display.info(p)
            return True

        if cmd == "/file":
            self._cmd_file(parts)
            return True

        if cmd == "/folder":
            self._cmd_folder(parts)
            return True

        if cmd == "/show":
            self._cmd_show(parts)
            return True

        if cmd == "/unload":
            self._cmd_unload(parts)
            return True

        if cmd == "/unload-all":
            self._cmd_unload_all(parts)
            return True

        if cmd == "/unload-folder":
            self._cmd_unload_folder(parts)
            return True

        if cmd == "/unload-pattern":
            self._cmd_unload_pattern(parts)
            return True

        if cmd == "/pin":
            self._cmd_pin(parts)
            return True

        if cmd == "/unpin":
            self._cmd_unpin(parts)
            return True

        if cmd == "/context-info":
            self._cmd_context_info()
            return True

        if cmd in ("/fix", "/refactor", "/patch"):
            self._cmd_code_op(cmd, raw)
            return True

        if cmd == "/snippet":
            self._cmd_snippet(parts)
            return True

        # Default: chat message
        self._display.assistant_header()
        response = self._session.send(raw, record_in_history=True)
        self._last_response = response
        return True

    # ------------------------------------------------------------------
    # State Getters for Autocomplete
    # ------------------------------------------------------------------

    def get_all_commands(self) -> list[str]:
        """Return all top-level commands starting with /."""
        return [
            "/exit", "/reset", "/help", "/file", "/folder", "/list", "/show",
            "/unload", "/unload-all", "/unload-folder", "/unload-pattern",
            "/pin", "/unpin", "/tokens", "/context-info", "/fix", "/refactor",
            "/patch", "/snippet"
        ]

    def get_loaded_paths(self) -> list[str]:
        """Return list of currently loaded file paths."""
        return self._files.loaded_paths()

    def get_snippet_names(self) -> list[str]:
        """Return list of saved snippet names."""
        return self._snippets.list_names()

    # ------------------------------------------------------------------
    # Command implementations
    # ------------------------------------------------------------------

    def _cmd_file(self, parts: list[str]) -> None:
        if len(parts) < 2 or not parts[1].strip():
            self._display.info("Usage: /file <path>")
            return
        path = " ".join(parts[1:])
        ok, err = self._files.load(path)
        if not ok:
            self._display.error(f"Failed to load: {err}")
        else:
            self._display.info(f"Loaded: {path}")

    def _cmd_folder(self, parts: list[str]) -> None:
        folder = parts[1] if len(parts) > 1 else "."
        import os
        if not os.path.isdir(folder):
            self._display.error(f"Folder not found: {folder}")
            return
        count, errors = self._files.load_folder(folder)
        for e in errors:
            self._display.info(f"  Skipped – {e}")
        self._display.info(f"Loaded {count} file(s) from {folder}.")

    def _cmd_show(self, parts: list[str]) -> None:
        if len(parts) < 2:
            self._display.info("Usage: /show <path>")
            return
        path = " ".join(parts[1:])
        content = self._files.get_content(path)
        if content is None:
            self._display.info("File not loaded. Use /file to load it first.")
            return
        # truncate for display
        max_chars = self._max_file_chars * 4
        display_content = content if len(content) <= max_chars else content[:max_chars] + "\n…[truncated]"
        self._display.info(f"\n--- {path} ---\n")
        self._display.info(display_content)
        self._display.info("\n--- end ---")

    def _cmd_unload(self, parts: list[str]) -> None:
        if len(parts) < 2:
            self._display.info("Usage: /unload <path>")
            return
        path = " ".join(parts[1:])
        if self._files.unload(path):
            self._display.success(f"Unloaded: {path}")
        else:
            self._display.warning(f"Skipped (likely pinned): {path}")

    def _cmd_unload_all(self, parts: list[str]) -> None:
        force = "--force" in parts
        count = self._files.unload_all(keep_pinned=not force)
        self._display.success(f"Unloaded {count} files.")

    def _cmd_unload_folder(self, parts: list[str]) -> None:
        if len(parts) < 2:
            self._display.info("Usage: /unload-folder <path>")
            return
        path = " ".join(parts[1:])
        count = self._files.unload_folder(path)
        self._display.success(f"Unloaded {count} files from {path}.")

    def _cmd_unload_pattern(self, parts: list[str]) -> None:
        if len(parts) < 2:
            self._display.info("Usage: /unload-pattern <glob>")
            return
        pattern = " ".join(parts[1:])
        count = self._files.unload_pattern(pattern)
        self._display.success(f"Unloaded {count} files matching {pattern}.")

    def _cmd_pin(self, parts: list[str]) -> None:
        if len(parts) < 2:
            self._display.info("Usage: /pin <path>")
            return
        path = " ".join(parts[1:])
        if self._ctx.pin_file(path):
            self._display.success(f"Pinned: {path}")
        else:
            self._display.error(f"Cannot pin {path}. Is it loaded?")

    def _cmd_unpin(self, parts: list[str]) -> None:
        if len(parts) < 2:
            self._display.info("Usage: /unpin <path>")
            return
        path = " ".join(parts[1:])
        self._ctx.unpin_file(path)
        self._display.success(f"Unpinned: {path}")

    def _cmd_context_info(self) -> None:
        stats = self._ctx.get_stats()
        self._display.info(f"Total tokens: {stats['total_tokens']} / {stats['max_total']}")
        self._display.info(f"Loaded files: {stats['file_count']} ({stats['pinned_count']} pinned)")
        self._display.newline()

        headers = ["File", "Tokens", "Pinned"]
        rows = [
            [f.get("path"), str(f.get("tokens")), "Yes" if f.get("pinned") else "No"]
            for f in stats["files"]
        ]
        self._display.table(headers, rows)

    def _cmd_code_op(self, cmd: str, raw: str) -> None:
        """Shared logic for /fix, /refactor, /patch."""
        tokens = raw.split(None, 2)  # [cmd, path, instructions?]
        if len(tokens) < 2:
            self._display.info(f"Usage: {cmd} <path> [instructions]")
            return
        path = tokens[1]
        instructions = tokens[2].strip() if len(tokens) > 2 else ""

        if not self._files.is_loaded(path):
            ok, err = self._files.load(path)
            if not ok:
                self._display.error(f"Cannot load file: {err}")
                return

        if not instructions:
            try:
                instructions = input("Instructions (one line): ").strip()
            except (EOFError, KeyboardInterrupt):
                instructions = ""

        content = self._files.get_content(path) or ""
        prompt = self._build_code_prompt(cmd, path, content, instructions)

        # Record user intent in history, then send the structured prompt
        self._ctx.add_user(f"{cmd} {path}: {instructions}")
        self._display.assistant_header()
        response = self._session.send(prompt, record_in_history=False)
        self._last_response = response

        # For /patch, offer to extract and apply
        if cmd == "/patch" and response:
            new_code = self._patch.extract_code_block(response)
            if new_code:
                ok, msg = self._patch.apply(path, new_code, confirm=True)
                self._display.info(msg)
                if ok:
                    # Refresh the in-memory store
                    self._files.load(path)
            else:
                self._display.info("No code block found in response to apply.")

    @staticmethod
    def _build_code_prompt(cmd: str, path: str, content: str, instructions: str) -> str:
        if cmd == "/fix":
            return (
                f"Fix bugs or errors in this file. Follow these instructions: {instructions}\n\n"
                f"File: {path}\n{content}\n\n"
                "Provide a clear explanation of the changes and a complete replacement file "
                "in a single fenced code block."
            )
        elif cmd == "/refactor":
            return (
                f"Refactor this file to improve readability, maintainability, or performance "
                f"according to: {instructions}\n\nFile: {path}\n{content}\n\n"
                "Provide a short summary and the full refactored file in a single fenced code block."
            )
        else:  # /patch
            return (
                f"Produce a patch (complete replacement) for this file according to: {instructions}\n\n"
                f"File: {path}\n{content}\n\n"
                "Provide only the replacement file in a single fenced code block."
            )

    def _cmd_snippet(self, parts: list[str]) -> None:
        sub = parts[1].lower() if len(parts) > 1 else ""
        if sub == "list":
            names = self._snippets.list_names()
            self._display.info("\n".join(names) if names else "No snippets saved.")
        elif sub == "show" and len(parts) > 2:
            block = self._snippets.as_context_block(parts[2])
            self._display.info(block if block else f"Snippet '{parts[2]}' not found.")
        elif sub == "del" and len(parts) > 2:
            deleted = self._snippets.delete(parts[2])
            self._display.info(f"Deleted '{parts[2]}'." if deleted else "Not found.")
        elif sub == "save" and len(parts) > 2:
            name = parts[2]
            if not self._last_response:
                self._display.info("No assistant response to save from.")
                return
            code = self._patch.extract_code_block(self._last_response)
            if not code:
                self._display.info("No code block found in last response.")
                return
            self._snippets.save(name, code)
            self._display.info(f"Snippet '{name}' saved.")
        else:
            self._display.info("Usage: /snippet save|show|list|del [name]")
