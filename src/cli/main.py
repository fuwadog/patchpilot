"""Typer CLI entry point for PatchPilot.

Supports two modes:
  - **One-shot commands**: ``patchpilot fix <file> -i "instructions"``
  - **Interactive REPL**:  ``patchpilot`` or ``patchpilot chat``

Production-quality code with type hints and docstrings.
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from typing import Optional

import typer

from ..client.nvidia import NvidiaProvider
from ..client.ollama import OllamaProvider
from ..config import Config
from ..context.manager import ContextManager
from ..files.manager import FileManager
from ..files.patching import PatchManager
from ..files.snippets import SnippetManager
from ..session.manager import SessionManager
from ..session.store import SessionStore
from .dispatcher import CommandDispatcher
from .output import (
    print_assistant_message,
    print_error,
    print_success,
    print_warning,
)
from .repl import REPL

# ---------------------------------------------------------------------------
# Typer app
# ---------------------------------------------------------------------------

app = typer.Typer(
    name="patchpilot",
    help="PatchPilot - AI-powered code assistant",
    no_args_is_help=False,  # We handle no-args ourselves (launch REPL)
    add_completion=False,
)

# ---------------------------------------------------------------------------
# Provider factory
# ---------------------------------------------------------------------------


def _create_provider(config: Config) -> NvidiaProvider | OllamaProvider:
    """Create the appropriate model provider from *config*.

    Uses :class:`NvidiaProvider` when an ``API_KEY`` is set (default path),
    otherwise falls back to :class:`OllamaProvider` for local inference.
    """
    if config.API_KEY:
        return NvidiaProvider(
            api_key=config.API_KEY,
            base_url=config.BASE_URL,
            model=config.MODEL,
            max_retries=getattr(config, "MAX_RETRIES", 3),
            retry_delay=getattr(config, "RETRY_DELAY", 1.5),
        )
    # Local fallback
    return OllamaProvider(
        model=config.MODEL,
        base_url=config.BASE_URL,
    )


# ---------------------------------------------------------------------------
# Service factory
# ---------------------------------------------------------------------------


def _create_services(
    config: Config,
) -> tuple[
    NvidiaProvider | OllamaProvider,
    ContextManager,
    FileManager,
    PatchManager,
    SnippetManager,
    SessionManager,
]:
    """Create all service objects for a CLI session.

    1. Model provider
    2. Context manager (token-aware)
    3. File manager (discovery / loading)
    4. Patch manager (safe file writes)
    5. Snippet manager (in-memory)
    6. Session manager (sync streaming)
    """
    provider = _create_provider(config)

    context = ContextManager(
        system_prompt=config.SYSTEM_PROMPT,
        max_total_tokens=config.MAX_TOTAL_TOKENS,
        max_file_tokens=config.MAX_FILE_TOKENS,
        max_convo_messages=config.MAX_CONVO_MESSAGES,
    )

    files = FileManager(
        context=context,
        max_files=config.MAX_FILES,
        default_extensions=config.DEFAULT_EXTENSIONS,
    )

    patch = PatchManager(
        backup=config.BACKUP_ON_WRITE,
        diff_preview=config.DIFF_PREVIEW,
    )

    snippets = SnippetManager()

    session = SessionManager(
        provider=provider,
        context=context,
        display=None,  # No-op display for batch operations
        temperature=config.TEMPERATURE,
        max_tokens=config.MAX_RESPONSE_TOKENS,
    )

    return provider, context, files, patch, snippets, session


# ---------------------------------------------------------------------------
# Shared code-op logic (used by fix, refactor, patch)
# ---------------------------------------------------------------------------


def _run_code_op(
    cmd: str,
    file: str,
    instructions: str,
    dry_run: bool = False,
    no_backup: bool = False,
) -> None:
    """Shared logic for ``/fix``, ``/refactor``, ``/patch`` one-shot commands.

    Parameters
    ----------
    cmd:
        One of ``"fix"``, ``"refactor"``, ``"patch"``.
    file:
        Path to the target file.
    instructions:
        Instructions for the AI (may be empty, but the user will be warned).
    dry_run:
        If True, show the diff but do not write.
    no_backup:
        If True, skip backup creation.
    """
    config = Config()
    _provider, _context, files, patch, _snippets, session = _create_services(config)

    # Load the target file
    if not files.is_loaded(file):
        ok, err = files.load(file)
        if not ok:
            print_error(f"Cannot load file: {err}")
            raise typer.Exit(1)

    if not instructions:
        print_warning("No instructions provided. Sending a generic prompt anyway.")

    content = files.get_content(file) or ""

    # Reuse the dispatcher's prompt builder (static method)
    prompt = CommandDispatcher._build_code_prompt(
        f"/{cmd}", file, content, instructions
    )

    # Record user intent and send
    _context.add_user(f"/{cmd} {file}: {instructions}")
    response = session.send(prompt, record_in_history=False)

    if not response:
        print_error("No response from assistant.")
        raise typer.Exit(1)

    # Print the assistant's explanation
    print_assistant_message(response)

    # For /patch (and fix/refactor by default), extract and apply the code block
    new_code = patch.extract_code_block(response)
    if new_code:
        ok, msg = patch.apply(
            path=file,
            new_content=new_code,
            confirm=False,  # CLI commands are explicit — no extra prompts
            dry_run=dry_run,
        )
        if ok:
            print_success(msg)
            # Reload so context sees the updated content
            files.load(file)
        else:
            print_error(msg)
    else:
        print_warning("No code block found in the response. Nothing to apply.")


# ---------------------------------------------------------------------------
# One-shot commands
# ---------------------------------------------------------------------------


@app.command()
def fix(
    file: str = typer.Argument(..., help="File to fix"),
    instructions: str = typer.Option(
        "", "--instructions", "-i", help="Instructions for the AI fix"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show changes without applying them"
    ),
    no_backup: bool = typer.Option(
        False, "--no-backup", help="Skip creating a backup of the original"
    ),
) -> None:
    """Fix bugs or errors in a file using AI.

    Loads the file, sends it to the AI with fix instructions, and applies
    the suggested changes atomically.
    """
    _run_code_op("fix", file, instructions, dry_run, no_backup)


@app.command()
def refactor(
    file: str = typer.Argument(..., help="File to refactor"),
    instructions: str = typer.Option(
        "", "--instructions", "-i", help="Refactoring instructions"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show changes without applying them"
    ),
    no_backup: bool = typer.Option(
        False, "--no-backup", help="Skip creating a backup of the original"
    ),
) -> None:
    """Refactor a file to improve structure, readability, or performance.

    Loads the file, sends it to the AI with refactoring instructions, and
    applies the suggested changes atomically.
    """
    _run_code_op("refactor", file, instructions, dry_run, no_backup)


@app.command()
def patch(
    file: str = typer.Argument(..., help="File to patch"),
    instructions: str = typer.Option(
        ..., "--instructions", "-i", help="Patch instructions (required)"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show changes without applying them"
    ),
    no_backup: bool = typer.Option(
        False, "--no-backup", help="Skip creating a backup of the original"
    ),
) -> None:
    """Generate and apply an AI patch to a file.

    Unlike ``fix`` or ``refactor``, the ``patch`` command is designed for
    targeted, instruction-driven edits.  The AI response is expected to
    contain a single fenced code block with the replacement content.
    """
    _run_code_op("patch", file, instructions, dry_run, no_backup)


@app.command()
def chat(
    model: Optional[str] = typer.Option(
        None, "--model", "-m", help="Override the AI model for this session"
    ),
) -> None:
    """Start an interactive REPL session.

    Launches the PatchPilot command-line REPL where you can:
      - Chat with the AI (plain text)
      - Run commands prefixed with ``/`` (e.g., ``/file``, ``/fix``)
      - Stream AI responses token by token
      - Persist conversations to the session database
    """
    config = Config()
    if model:
        config.MODEL = model  # Allow model override

    _run_repl(config)


# ---------------------------------------------------------------------------
# Entry-point helpers
# ---------------------------------------------------------------------------


def _run_repl(config: Config | None = None) -> None:
    """Initialise services and launch the interactive REPL.

    Parameters
    ----------
    config:
        Optional pre-built config.  Created from defaults if omitted.
    """
    if config is None:
        config = Config()

    provider, context, files, patch, snippets, session = _create_services(config)

    store = SessionStore(config.DB_PATH)

    # Single event loop for all async DB operations
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    session_id: str = ""

    try:
        loop.run_until_complete(store.connect())
        session_id = str(uuid.uuid4())
        loop.run_until_complete(
            store.create_session(session_id, title="CLI session")
        )

        repl = REPL(
            config=config,
            provider=provider,
            context=context,
            files=files,
            patch=patch,
            snippets=snippets,
            session=session,
            store=store,
            session_id=session_id,
            loop=loop,
        )
        repl.run()
    finally:
        if session_id:
            try:
                loop.run_until_complete(store.close(session_id))
            except Exception:
                pass
        loop.close()


def main() -> None:
    """Entry point — launches REPL if no arguments, otherwise dispatches to Typer.

    Detected as the ``[project.scripts]`` entry in ``pyproject.toml``.
    """
    if len(sys.argv) == 1:
        # No arguments → launch the REPL
        _run_repl()
    else:
        app()


# ---------------------------------------------------------------------------
# Allow ``python -m src.cli.main``
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()
