"""Session management commands for the PatchPilot REPL.

All functions are simple, stateless, and produce output via the Rich
*output* module.  They accept the managers they need as arguments.

Commands covered
----------------
- ``/history`` — list recent sessions from the database
- ``/resume [id]`` — load a previous session's conversation
- ``/reset`` — clear the current conversation (handled in REPL, not here)
- ``/tokens`` — show token usage estimates
- ``/context-info`` — detailed token and file statistics
- ``/snippet save|show|list|del`` — manage named code snippets
"""

from __future__ import annotations

from typing import Optional

from ...context.manager import ContextManager
from ...files.patching import PatchManager
from ...files.snippets import SnippetManager
from ...session.store import SessionStore
from ..output import (
    print_context_stats,
    print_error,
    print_info,
    print_session_list,
    print_success,
)

# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


async def cmd_history(store: SessionStore) -> None:
    """List recent sessions from the database.

    Parameters
    ----------
    store:
        The active :class:`SessionStore` instance.
    """
    if not store:
        print_error("Session store not available.")
        return

    try:
        sessions = await store.list_sessions(limit=20)
    except Exception as exc:
        print_error(f"Failed to load sessions: {exc}")
        return

    if not sessions:
        print_info("No saved sessions.")
        return

    # Convert SessionSummary dataclass instances to dicts for the output function
    session_dicts = [
        {
            "id": s.id,
            "title": s.title,
            "message_count": s.message_count,
            "created_at": s.created_at,
        }
        for s in sessions
    ]
    print_session_list(session_dicts)


async def cmd_resume(
    store: SessionStore,
    context: ContextManager,
    session_id_prefix: str,
) -> Optional[str]:
    """Resume a previous session by ID prefix.

    Matches the first session whose ID starts with *session_id_prefix*.
    If no prefix is provided, lists recent sessions instead.

    Parameters
    ----------
    store:
        The active :class:`SessionStore` instance.
    context:
        The active :class:`ContextManager` — its conversation will be
        replaced with the resumed session's messages.
    session_id_prefix:
        The prefix of the session ID to resume.  Empty string lists
        recent sessions.

    Returns
    -------
    The full session ID if resumed, or ``None``.
    """
    if not store:
        print_error("Session store not available.")
        return None

    try:
        sessions = await store.list_sessions(limit=100)
    except Exception as exc:
        print_error(f"Failed to load sessions: {exc}")
        return None

    if not session_id_prefix:
        # Show recent sessions as a hint
        if not sessions:
            print_info("No saved sessions.")
            return None
        session_dicts = [
            {
                "id": s.id,
                "title": s.title,
                "message_count": s.message_count,
                "created_at": s.created_at,
            }
            for s in sessions[:10]
        ]
        print_session_list(session_dicts)
        print_info("Use /resume <session_id_prefix> to load a session.")
        return None

    # Find matching session
    match = next(
        (s for s in sessions if s.id.startswith(session_id_prefix)),
        None,
    )
    if not match:
        print_error(
            f"No session found matching '{session_id_prefix}'."
        )
        return None

    # Load messages and replace context conversation
    try:
        messages = await store.get_session_messages(match.id)
    except Exception as exc:
        print_error(f"Failed to load messages: {exc}")
        return None

    context.reset_convo()
    for msg in messages:
        if msg["role"] == "user":
            context.add_user(msg["content"])
        elif msg["role"] == "assistant":
            context.add_assistant(msg["content"])

    msg_count = len(messages)
    print_success(
        f"Resumed session: {match.title} ({msg_count} messages)"
    )
    return match.id


def cmd_tokens(context: ContextManager) -> None:
    """Show estimated token usage for the current context.

    Parameters
    ----------
    context:
        The active :class:`ContextManager` instance.
    """
    stats = context.get_stats()
    print_context_stats(stats)


# ---------------------------------------------------------------------------
# Snippet commands
# ---------------------------------------------------------------------------


def cmd_snippet(
    snippets: SnippetManager,
    patch: PatchManager,
    last_response: Optional[str],
    args: str,
) -> None:
    """Handle ``/snippet`` subcommands.

    Parameters
    ----------
    snippets:
        The active :class:`SnippetManager` instance.
    patch:
        The active :class:`PatchManager` (used to extract code blocks).
    last_response:
        The most recent assistant response (may be ``None``).
    args:
        The full argument string after ``/snippet``.
    """
    parts = args.split(maxsplit=1) if args else []
    sub = parts[0].lower() if parts else ""
    rest = parts[1] if len(parts) > 1 else ""

    if not sub or sub == "help":
        _print_snippet_usage()
        return

    dispatch = {
        "list": _snippet_list,
        "show": _snippet_show,
        "del": _snippet_delete,
        "save": _snippet_save,
    }

    handler = dispatch.get(sub)
    if handler:
        handler(snippets, patch, last_response, rest)
    else:
        print_error(
            f"Unknown snippet subcommand: {sub}.  "
            "Use /snippet help for usage."
        )


# ---------------------------------------------------------------------------
# Snippet subcommand implementations
# ---------------------------------------------------------------------------


def _print_snippet_usage() -> None:
    """Print the ``/snippet`` usage help."""
    print_info(
        "Usage:\n"
        "  /snippet save <name>       Save last code block as snippet\n"
        "  /snippet show <name>       Display a saved snippet\n"
        "  /snippet list              List all snippets\n"
        "  /snippet del <name>        Delete a snippet"
    )


def _snippet_list(
    snippets: SnippetManager,
    patch: PatchManager,  # noqa: ARG001
    last_response: str | None,  # noqa: ARG001
    rest: str,  # noqa: ARG001
) -> None:
    """List all saved snippets."""
    names = snippets.list_names()
    if names:
        print_info("Saved snippets:")
        for name in names:
            print(f"  \u2022 {name}")
    else:
        print_info("No snippets saved.")


def _snippet_show(
    snippets: SnippetManager,
    patch: PatchManager,  # noqa: ARG001
    last_response: str | None,  # noqa: ARG001
    name: str,
) -> None:
    """Display a saved snippet."""
    if not name:
        print_error("Usage: /snippet show <name>")
        return
    block = snippets.as_context_block(name)
    if block:
        from ..output import print_code_block

        print_code_block(block, language="")
    else:
        print_error(f"Snippet '{name}' not found.")


def _snippet_delete(
    snippets: SnippetManager,
    patch: PatchManager,  # noqa: ARG001
    last_response: str | None,  # noqa: ARG001
    name: str,
) -> None:
    """Delete a saved snippet."""
    if not name:
        print_error("Usage: /snippet del <name>")
        return
    deleted = snippets.delete(name)
    if deleted:
        print_success(f"Deleted snippet '{name}'.")
    else:
        print_error(f"Snippet '{name}' not found.")


def _snippet_save(
    snippets: SnippetManager,
    patch: PatchManager,
    last_response: str | None,
    name: str,
) -> None:
    """Save the last assistant code block as a snippet."""
    if not name:
        print_error("Usage: /snippet save <name>")
        return
    if not last_response:
        print_error(
            "No assistant response to save from.  "
            "Send a chat message or use /fix first."
        )
        return

    code = patch.extract_code_block(last_response)
    if not code:
        print_error(
            "No code block found in the last response.  "
            "The assistant must include a fenced code block."
        )
        return

    snippets.save(name, code)
    print_success(f"Snippet '{name}' saved ({len(code)} chars).")
