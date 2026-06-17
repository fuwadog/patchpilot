"""In-memory named code snippet management."""

from __future__ import annotations

from typing import Optional


class SnippetManager:
    """
    Manages in-memory named code snippets that can be inserted into prompts
    without loading full files.
    """

    def __init__(self) -> None:
        self._snippets: dict[str, str] = {}

    def save(self, name: str, code: str) -> None:
        self._snippets[name] = code

    def get(self, name: str) -> Optional[str]:
        return self._snippets.get(name)

    def delete(self, name: str) -> bool:
        return self._snippets.pop(name, None) is not None

    def list_names(self) -> list[str]:
        return list(self._snippets.keys())

    def as_context_block(self, name: str) -> Optional[str]:
        code = self.get(name)
        if code is None:
            return None
        return f"[SNIPPET] {name}\n{code}"
