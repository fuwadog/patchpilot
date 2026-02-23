"""Token-aware context management."""
from __future__ import annotations
from dataclasses import dataclass, field
import os
from typing import Optional, SupportsIndex


@dataclass
class Message:
    role: str
    content: str

    def token_estimate(self) -> int:
        """Rough estimate: 1 token ≈ 4 chars."""
        return max(1, len(self.content) // 4)

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content}


class ContextManager:
    """
    Manages the three layers of context:
    1. System message (always included, fixed)
    2. File messages (project files, high priority)
    3. Conversation messages (rolling window, lower priority)

    Applies a token budget to keep total context within limits.
    """

    def __init__(self, system_prompt: str, max_total_tokens: int, max_file_tokens: int, max_convo_messages: int):
        self._system = Message("system", system_prompt)
        self._max_total = max_total_tokens
        self._max_file_tokens = max_file_tokens
        self._max_convo = max_convo_messages
        self._file_messages: list[Message] = []
        self._convo_messages: list[Message] = []
        self._pinned_files: set[str] = set()

    # ------------------------------------------------------------------
    # File layer
    # ------------------------------------------------------------------

    def upsert_file(self, path: str, content: str) -> None:
        tag = f"[PROJECT_FILE] {path}"
        # Remove existing entry for this path
        self._file_messages = [m for m in self._file_messages if not m.content.startswith(tag + "\n")]
        budgeted = self._apply_file_budget(content)
        self._file_messages.append(Message("user", f"{tag}\n{budgeted}"))

    def remove_file(self, path: str, force: bool = False) -> bool:
        """
        Remove a file from context.
        Returns True if removed, False if skipped (e.g. pinned).
        """
        path = os.path.abspath(path)
        if path in self._pinned_files and not force:
            return False

        tag = f"[PROJECT_FILE] {path}"
        self._file_messages = [m for m in self._file_messages if not m.content.startswith(tag + "\n")]
        self._pinned_files.discard(path)
        return True

    def _apply_file_budget(self, content: str) -> str:
        """Chunk content to fit within per-file token budget."""
        max_chars = self._max_file_tokens * 4
        if len(content) <= max_chars:
            return content
        half = max_chars // 2
        head = content[:half]
        tail = content[-(half - 100):]
        return head + "\n\n/* ...TRUNCATED... (tail follows) */\n\n" + tail

    # ------------------------------------------------------------------
    # Conversation layer
    # ------------------------------------------------------------------

    def add_user(self, content: str) -> None:
        self._convo_messages.append(Message("user", content))
        self._trim_convo()

    def add_assistant(self, content: str) -> None:
        self._convo_messages.append(Message("assistant", content))
        self._trim_convo()

    def _trim_convo(self) -> None:
        if len(self._convo_messages) > self._max_convo:
            self._convo_messages = self._convo_messages[-self._max_convo:]

    def reset_convo(self) -> None:
        self._convo_messages.clear()

    # ------------------------------------------------------------------
    # Build final message list with total-token enforcement
    # ------------------------------------------------------------------

    def build_messages(self, ephemeral_user_content: Optional[str] = None) -> list[dict]:
        """
        Assembles: system + files + convo + optional ephemeral user message.
        Drops oldest convo messages if total token budget is exceeded.
        Falls back to shrinking file content if still over budget.
        """
        ephemeral = [Message("user", ephemeral_user_content)] if ephemeral_user_content else []

        def total_tokens(convo: list[Message]) -> int:
            return (
                self._system.token_estimate()
                + sum(m.token_estimate() for m in self._file_messages)
                + sum(m.token_estimate() for m in convo)
                + sum(m.token_estimate() for m in ephemeral)
            )

        convo = list(self._convo_messages)
        # Drop oldest convo messages until within budget
        while total_tokens(convo) > self._max_total and convo:
            convo.pop(0)

        # If still over, compress file messages
        file_msgs = list(self._file_messages)
        if total_tokens(convo) > self._max_total:
            file_msgs = [
                Message(m.role, self._apply_file_budget(m.content[: self._max_file_tokens * 2]))
                for m in file_msgs
            ]

        all_messages = [self._system, *file_msgs, *convo, *ephemeral]
        return [m.to_dict() for m in all_messages]

    # ------------------------------------------------------------------
    # Inspection
    # ------------------------------------------------------------------

    def file_paths(self) -> list[str]:
        paths = []
        for m in self._file_messages:
            first_line = m.content.split("\n", 1)[0]
            if first_line.startswith("[PROJECT_FILE] "):
                paths.append(first_line[len("[PROJECT_FILE] "):])
        return paths

    def estimated_total_tokens(self) -> int:
        return (
            self._system.token_estimate()
            + sum(m.token_estimate() for m in self._file_messages)
            + sum(m.token_estimate() for m in self._convo_messages)
        )

    # ------------------------------------------------------------------
    # Pinning and Stats
    # ------------------------------------------------------------------

    def pin_file(self, path: str) -> bool:
        """Mark a file as pinned. File must be loaded first."""
        path = os.path.abspath(path)
        if any(m.content.startswith(f"[PROJECT_FILE] {path}\n") for m in self._file_messages):
            self._pinned_files.add(path)
            return True
        return False

    def unpin_file(self, path: str) -> None:
        path = os.path.abspath(path)
        self._pinned_files.discard(path)

    def is_pinned(self, path: str) -> bool:
        return os.path.abspath(path) in self._pinned_files

    def get_stats(self) -> dict:
        file_stats = []
        for m in self._file_messages:
            tag = "[PROJECT_FILE] "
            if m.content.startswith(tag):
                path = m.content.split("\n", 1)[0][len(tag):]
                file_stats.append({
                    "path": path,
                    "tokens": m.token_estimate(),
                    "pinned": path in self._pinned_files
                })

        return {
            "total_tokens": self.estimated_total_tokens(),
            "max_total": self._max_total,
            "file_count": len(self._file_messages),
            "pinned_count": len(self._pinned_files),
            "convo_messages": len(self._convo_messages),
            "files": file_stats
        }
