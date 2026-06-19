"""CLI command dispatch – all command handler logic lives here."""

from __future__ import annotations

import re
import textwrap
from typing import Any, ClassVar, Optional

from ..context.manager import ContextManager
from ..files.manager import FileManager
from ..files.patching import PatchManager
from ..files.snippets import SnippetManager
from ..session.manager import SessionManager
from ..session.store import SessionStore

_RICH_TAG_RE = re.compile(r"\[/?[a-zA-Z][a-zA-Z0-9 _-]*\]")


def _strip_rich_markup(text: str) -> str:
    """Remove Rich console markup tags that Textual Markdown cannot render.

    Rich tags like [bold], [/italic], [bright_red] leak as literal text
    when passed through Markdown widgets. This strips them cleanly.
    """
    return _RICH_TAG_RE.sub("", text)


HELP_TEXT = textwrap.dedent("""\
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

  --- Sessions ---
  /history                       Show recent sessions.
  /resume [id]                   Resume a previous session by ID prefix.

  --- Info ---
  /tokens                        Show estimated token usage.
  /context-info                  Detailed token and file stats.

Anything else is sent as a regular chat message.
""").strip()


class CommandDispatcher:
    COMMAND_HANDLERS: ClassVar[dict[str, str]] = {
        "/exit": "_cmd_exit",
        "/help": "_cmd_help",
        "/reset": "_cmd_reset",
        "/tokens": "_cmd_tokens",
        "/list": "_cmd_list",
        "/file": "_cmd_file",
        "/folder": "_cmd_folder",
        "/show": "_cmd_show",
        "/unload": "_cmd_unload",
        "/unload-all": "_cmd_unload_all",
        "/unload-folder": "_cmd_unload_folder",
        "/unload-pattern": "_cmd_unload_pattern",
        "/pin": "_cmd_pin",
        "/unpin": "_cmd_unpin",
        "/context-info": "_cmd_context_info",
        "/snippet": "_cmd_snippet",
        "/history": "_cmd_history",
        "/resume": "_cmd_resume",
    }

    def __init__(
        self,
        session: SessionManager,
        files: FileManager,
        context: ContextManager,
        patch: PatchManager,
        snippets: SnippetManager,
        display: Any = None,  # kept for backward compatibility
        max_file_chars: int = 10000,
        store: Optional[SessionStore] = None,
        session_id: str = "",
    ):
        self._session = session
        self._files = files
        self._ctx = context
        self._patch = patch
        self._snippets = snippets
        self._display = display  # no longer used for output
        self._max_file_chars = max_file_chars
        self._last_response: Optional[str] = None
        self._store = store
        self._session_id = session_id
        self.exit_requested: bool = False

    # ------------------------------------------------------------------
    # Main entry points
    # ------------------------------------------------------------------

    def dispatch(self, raw: str) -> bool:  # noqa: C901
        """Sync dispatch for backward compatibility. Returns False to exit."""
        raw = raw.rstrip()
        if not raw:
            return True

        parts = raw.split()
        cmd = parts[0].lower()

        if cmd == "/exit":
            self.exit_requested = True
            result = self._cmd_exit()
            result = _strip_rich_markup(result)
            print(result)
            return False

        args_str = " ".join(parts[1:]) if len(parts) > 1 else ""

        if cmd in ("/fix", "/refactor", "/patch"):
            result = self._cmd_code_op(cmd, raw)
            result = _strip_rich_markup(result)
            if result:
                print(result)
        elif cmd in ("/history", "/resume"):
            print(f"Use '{cmd}' in the Textual app (requires async DB).")
        elif cmd in self.COMMAND_HANDLERS:
            handler = getattr(self, self.COMMAND_HANDLERS[cmd])
            result = handler(args_str) if args_str else handler()
            result = _strip_rich_markup(result)
            if result:
                print(result)
        else:
            # Chat message — send to AI
            response = self._session.send(raw, record_in_history=True)
            if response:
                print(_strip_rich_markup(response))
            self._last_response = response

        return True

    async def dispatch_async(self, user_input: str) -> str:  # noqa: C901
        """Async dispatch for Textual TUI. Returns response string."""
        if not user_input.strip():
            return ""

        parts = user_input.strip().split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        # Special cases requiring async or side effects
        if cmd in ("/fix", "/refactor", "/patch"):
            result = await self._cmd_code_op_async(cmd, args)
        elif cmd == "/history":
            result = await self._cmd_history_async()
        elif cmd == "/resume":
            result = await self._cmd_resume_async(args)
        elif cmd == "/exit":
            self.exit_requested = True
            result = self._cmd_exit()
        elif cmd in self.COMMAND_HANDLERS:
            handler = getattr(self, self.COMMAND_HANDLERS[cmd])
            result = handler(args) if args else handler()
        else:
            # Chat message — send to AI via async stream
            if self._store and self._session_id:
                await self._store.add_message(self._session_id, "user", user_input)
            result = await self._collect_async_response(user_input)
            result = _strip_rich_markup(result)
            if self._store and self._session_id:
                await self._store.add_message(self._session_id, "assistant", result)
            return result

        # Sanitize Rich markup tags from response
        if result:
            result = _strip_rich_markup(result)

        # Persist command to DB
        if self._store and self._session_id:
            await self._store.add_message(self._session_id, "user", user_input)
            await self._store.add_message(self._session_id, "assistant", result)
        return result

    async def _collect_async_response(self, user_input: str) -> str:
        """Send a chat message via async streaming and collect the full response."""
        full_response = ""
        async for chunk in self._session.stream_async(user_input):
            if chunk.content:
                full_response += chunk.content
        if full_response:
            self._last_response = full_response
        return full_response

    # ------------------------------------------------------------------
    # Command implementations (all return str, accept optional args)
    # ------------------------------------------------------------------

    def _cmd_exit(self, args: str = "") -> str:
        return "Goodbye!"

    def _cmd_help(self, args: str = "") -> str:
        return HELP_TEXT

    def _cmd_reset(self, args: str = "") -> str:
        self._session.reset()
        return "Conversation history cleared (project files retained)."

    def _cmd_tokens(self, args: str = "") -> str:
        est = self._ctx.estimated_total_tokens()
        return f"Estimated context tokens: ~{est}"

    def _cmd_list(self, args: str = "") -> str:
        paths = self._files.loaded_paths()
        if not paths:
            return "No files loaded."
        return "\n".join(paths)

    def _cmd_file(self, args: str = "") -> str:
        if not args.strip():
            return "Usage: /file <path>"
        path = args.strip()
        ok, err = self._files.load(path)
        if not ok:
            return f"Failed to load: {err}"
        return f"Loaded: {path}"

    def _cmd_folder(self, args: str = "") -> str:
        folder = args.strip() or "."
        import os

        if not os.path.isdir(folder):
            return f"Folder not found: {folder}"
        count, errors = self._files.load_folder(folder)
        lines = [f"  Skipped – {e}" for e in errors]
        lines.append(f"Loaded {count} file(s) from {folder}.")
        return "\n".join(lines)

    def _cmd_show(self, args: str = "") -> str:
        if not args.strip():
            return "Usage: /show <path>"
        path = args.strip()
        content = self._files.get_content(path)
        if content is None:
            return "File not loaded. Use /file to load it first."
        max_chars = self._max_file_chars * 4
        display_content = (
            content
            if len(content) <= max_chars
            else content[:max_chars] + "\n…[truncated]"
        )
        return f"**{path}**\n\n```\n{display_content}\n```"

    def _cmd_unload(self, args: str = "") -> str:
        if not args.strip():
            return "Usage: /unload <path>"
        path = args.strip()
        if self._files.unload(path):
            return f"Unloaded: {path}"
        return f"Skipped (likely pinned): {path}"

    def _cmd_unload_all(self, args: str = "") -> str:
        force = "--force" in args.split()
        count = self._files.unload_all(keep_pinned=not force)
        return f"Unloaded {count} files."

    def _cmd_unload_folder(self, args: str = "") -> str:
        if not args.strip():
            return "Usage: /unload-folder <path>"
        path = args.strip()
        count = self._files.unload_folder(path)
        return f"Unloaded {count} files from {path}."

    def _cmd_unload_pattern(self, args: str = "") -> str:
        if not args.strip():
            return "Usage: /unload-pattern <glob>"
        pattern = args.strip()
        count = self._files.unload_pattern(pattern)
        return f"Unloaded {count} files matching {pattern}."

    def _cmd_pin(self, args: str = "") -> str:
        if not args.strip():
            return "Usage: /pin <path>"
        path = args.strip()
        if self._ctx.pin_file(path):
            return f"Pinned: {path}"
        return f"Cannot pin {path}. Is it loaded?"

    def _cmd_unpin(self, args: str = "") -> str:
        if not args.strip():
            return "Usage: /unpin <path>"
        path = args.strip()
        self._ctx.unpin_file(path)
        return f"Unpinned: {path}"

    def _cmd_context_info(self, args: str = "") -> str:
        stats = self._ctx.get_stats()
        lines = [
            f"**Total tokens:** ~{stats['total_tokens']} / {stats['max_total']}",
            f"**Loaded files:** {stats['file_count']} ({stats['pinned_count']} pinned)",
        ]
        if stats["files"]:
            lines.append("")
            lines.append("| File | Tokens | Pinned |")
            lines.append("|------|-------:|--------|")
            for f in stats["files"]:
                pinned = "Yes" if f.get("pinned") else "No"
                path = f.get("path", "")
                # Truncate long paths for table display
                if len(path) > 45:
                    path = "…" + path[-44:]
                lines.append(f"| {path} | {f.get('tokens', '')} | {pinned} |")
        return "\n".join(lines)

    def _cmd_snippet(self, args: str = "") -> str:
        parts = args.split(None, 1)
        sub = parts[0].lower() if parts else ""
        rest = parts[1] if len(parts) > 1 else ""

        if sub == "list":
            names = self._snippets.list_names()
            return "\n".join(names) if names else "No snippets saved."
        if sub == "show" and rest:
            block = self._snippets.as_context_block(rest)
            return block if block else f"Snippet '{rest}' not found."
        if sub == "del" and rest:
            deleted = self._snippets.delete(rest)
            return f"Deleted '{rest}'." if deleted else "Not found."
        if sub == "save" and rest:
            name = rest
            if not self._last_response:
                return "No assistant response to save from."
            code = self._patch.extract_code_block(self._last_response)
            if not code:
                return "No code block found in last response."
            self._snippets.save(name, code)
            return f"Snippet '{name}' saved."
        return "Usage: /snippet save|show|list|del [name]"

    def _cmd_history(self, args: str = "") -> str:
        """Sync stub — real implementation is async via dispatch_async."""
        return "Use /history in the Textual app (requires async DB)."

    def _cmd_resume(self, args: str = "") -> str:
        """Sync stub — real implementation is async via dispatch_async."""
        if not args.strip():
            return "Use /resume [id] in the Textual app (requires async DB)."
        return "Use /resume in the Textual app (requires async DB)."

    # ------------------------------------------------------------------
    # Async command implementations (DB-backed)
    # ------------------------------------------------------------------

    async def _cmd_history_async(self) -> str:
        """Show recent sessions from the DB."""
        if not self._store:
            return "Session store not available."
        sessions = await self._store.list_sessions()
        if not sessions:
            return "No saved sessions."
        lines = ["Recent sessions:"]
        for s in sessions:
            lines.append(f"  [{s.id[:8]}] {s.title} ({s.message_count} messages)")
        return "\n".join(lines)

    async def _cmd_resume_async(self, args: str = "") -> str:
        """Resume a previous session from the DB."""
        if not self._store:
            return "Session store not available."

        if not args.strip():
            sessions = await self._store.list_sessions(limit=5)
            if not sessions:
                return "No sessions to resume."
            lines = ["Recent sessions (use /resume <id> to resume):"]
            for s in sessions:
                lines.append(f"  [{s.id[:8]}] {s.title}")
            return "\n".join(lines)

        session_id_prefix = args.strip()
        sessions = await self._store.list_sessions(limit=100)
        match = next((s for s in sessions if s.id.startswith(session_id_prefix)), None)
        if not match:
            return f"No session found matching '{session_id_prefix}'."

        messages = await self._store.get_session_messages(match.id)
        self._ctx.reset_convo()
        for msg in messages:
            if msg["role"] == "user":
                self._ctx.add_user(msg["content"])
            elif msg["role"] == "assistant":
                self._ctx.add_assistant(msg["content"])
        self._session_id = match.id
        return f"Resumed session: {match.title} ({len(messages)} messages)"

    # ------------------------------------------------------------------
    # Code operations (sync variant)
    # ------------------------------------------------------------------

    def _cmd_code_op(self, cmd: str, raw: str) -> str:
        """Shared sync logic for /fix, /refactor, /patch. Returns response."""
        tokens = raw.split(None, 2)  # [cmd, path, instructions?]
        if len(tokens) < 2:
            return f"Usage: {cmd} <path> [instructions]"
        path = tokens[1]
        instructions = tokens[2].strip() if len(tokens) > 2 else ""

        if not self._files.is_loaded(path):
            ok, err = self._files.load(path)
            if not ok:
                return f"Cannot load file: {err}"

        if not instructions:
            return f"Usage: {cmd} <path> [instructions]"

        content = self._files.get_content(path) or ""
        prompt = self._build_code_prompt(cmd, path, content, instructions)

        # Record user intent, then send the structured prompt (not double-recorded)
        self._ctx.add_user(f"{cmd} {path}: {instructions}")
        response = self._session.send(prompt, record_in_history=False)
        if not response:
            return "No response from assistant."
        self._last_response = response

        if cmd == "/patch":
            new_code = self._patch.extract_code_block(response)
            if new_code:
                ok, msg = self._patch.apply(path, new_code, confirm=False)
                if ok:
                    self._files.load(path)
                return f"{response}\n\n---\n{msg}"
            return response + "\n\n---\nNo code block found in response to apply."

        return response

    async def _cmd_code_op_async(self, cmd: str, args: str) -> str:  # noqa: C901
        """Shared async logic for /fix, /refactor, /patch. Returns response."""
        parts = args.split(None, 1)
        if not parts:
            return f"Usage: {cmd} <path> [instructions]"
        path = parts[0]
        instructions = parts[1].strip() if len(parts) > 1 else ""

        if not self._files.is_loaded(path):
            ok, err = self._files.load(path)
            if not ok:
                return f"Cannot load file: {err}"

        if not instructions:
            return f"Usage: {cmd} <path> [instructions]"

        content = self._files.get_content(path) or ""
        prompt = self._build_code_prompt(cmd, path, content, instructions)

        # Record user intent, then stream the structured prompt
        self._ctx.add_user(f"{cmd} {path}: {instructions}")

        full_response = ""
        async for chunk in self._session.stream_async(prompt):
            if chunk.content:
                full_response += chunk.content

        if not full_response:
            return "No response from assistant."
        self._last_response = full_response

        if cmd == "/patch":
            new_code = self._patch.extract_code_block(full_response)
            if new_code:
                ok, msg = self._patch.apply(path, new_code, confirm=False)
                if ok:
                    self._files.load(path)
                return f"{full_response}\n\n---\n{msg}"
            return full_response + "\n\n---\nNo code block found in response to apply."

        return full_response

    @staticmethod
    def _build_code_prompt(cmd: str, path: str, content: str, instructions: str) -> str:
        if cmd == "/fix":
            return (
                f"Fix bugs or errors in this file. Follow these instructions: "
                f"{instructions}\n\nFile: {path}\n{content}\n\n"
                "Provide a clear explanation of the changes and a complete "
                "replacement file in a single fenced code block."
            )
        if cmd == "/refactor":
            return (
                f"Refactor this file to improve readability, maintainability, "
                f"or performance according to: {instructions}\n\n"
                f"File: {path}\n{content}\n\n"
                "Provide a short summary and the full refactored file in a "
                "single fenced code block."
            )
        # /patch
        return (
            f"Produce a patch (complete replacement) for this file according "
            f"to: {instructions}\n\nFile: {path}\n{content}\n\n"
            "Provide only the replacement file in a single fenced code block."
        )

    # ------------------------------------------------------------------
    # State Getters for Autocomplete
    # ------------------------------------------------------------------

    def get_all_commands(self) -> list[str]:
        """Return all top-level commands starting with /."""
        return [
            "/exit",
            "/reset",
            "/help",
            "/file",
            "/folder",
            "/list",
            "/show",
            "/unload",
            "/unload-all",
            "/unload-folder",
            "/unload-pattern",
            "/pin",
            "/unpin",
            "/tokens",
            "/context-info",
            "/fix",
            "/refactor",
            "/patch",
            "/snippet",
            "/history",
            "/resume",
        ]

    def get_loaded_paths(self) -> list[str]:
        """Return list of currently loaded file paths."""
        return self._files.loaded_paths()

    def get_snippet_names(self) -> list[str]:
        """Return list of saved snippet names."""
        return self._snippets.list_names()
