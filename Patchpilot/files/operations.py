"""Safe file operations: atomic writes, backups, unified diff preview."""
from __future__ import annotations
import difflib
import os
import re
import shutil
import tempfile
import time
from typing import Optional


class PatchManager:
    """
    Applies model-generated patches / replacements to files safely:
    1. Show unified diff preview (optional)
    2. Ask for confirmation (optional)
    3. Backup original (optional)
    4. Atomic write (temp file + rename)
    """

    def __init__(self, backup: bool = True, diff_preview: bool = True, backup_count: int = 5):
        self._backup = backup
        self._diff_preview = diff_preview
        self._backup_count = backup_count
        self._backup_dir = "backups"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract_code_block(self, model_response: str) -> Optional[str]:
        """
        Pull the first fenced code block out of a model response.
        Returns the inner text or None if not found.
        """
        pattern = r"```(?:\w+)?\n(.*?)```"
        match = re.search(pattern, model_response, re.DOTALL)
        return match.group(1).rstrip("\n") if match else None

    def apply(self, path: str, new_content: str, confirm: bool = True, dry_run: bool = False) -> tuple[bool, str]:
        """
        Write new_content to path safely.
        Returns (success, message).
        """
        path = os.path.abspath(path)
        old_content = self._read(path)

        if self._diff_preview:
            self._show_diff(path, old_content or "", new_content)

        if dry_run:
            return True, "[DRY-RUN] No changes applied."

        if confirm:
            try:
                answer = input(f"\nApply patch to {path}? [y/N] ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                return False, "Patch cancelled."
            if answer != "y":
                return False, "Patch not applied."

        if old_content is not None and self._backup:
            backup_path = self._backup_file(path)
            print(f"  Backup saved: {backup_path}")

        ok, msg = self._atomic_write(path, new_content)
        return ok, msg

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _read(path: str) -> Optional[str]:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return fh.read()
        except FileNotFoundError:
            return None
        except Exception as exc:
            return None

    @staticmethod
    def _show_diff(path: str, old: str, new: str) -> None:
        old_lines = old.splitlines(keepends=True)
        new_lines = new.splitlines(keepends=True)
        diff = list(difflib.unified_diff(old_lines, new_lines, fromfile=f"a/{path}", tofile=f"b/{path}"))
        if not diff:
            print("  (No changes detected in diff)")
            return
        print(f"\n--- Diff for {path} ---")
        # Colour output if tty
        use_color = os.isatty(1)
        for line in diff:
            if use_color:
                if line.startswith("+") and not line.startswith("+++"):
                    print(f"\033[32m{line}\033[0m", end="")
                elif line.startswith("-") and not line.startswith("---"):
                    print(f"\033[31m{line}\033[0m", end="")
                else:
                    print(line, end="")
            else:
                print(line, end="")
        print("\n--- End diff ---")

    def _backup_file(self, path: str) -> str:
        if not os.path.exists(self._backup_dir):
            os.makedirs(self._backup_dir)

        base = os.path.basename(path)
        ts = time.strftime("%Y%m%d_%H%M%S")
        backup = os.path.join(self._backup_dir, f"{base}.{ts}.bak")
        shutil.copy2(path, backup)

        # Rotation
        backups = sorted([
            os.path.join(self._backup_dir, f)
            for f in os.listdir(self._backup_dir)
            if f.startswith(base) and f.endswith(".bak")
        ], key=os.path.getmtime)

        while len(backups) > self._backup_count:
            oldest = backups.pop(0)
            try:
                os.remove(oldest)
            except Exception:
                pass

        return backup

    @staticmethod
    def _atomic_write(path: str, content: str) -> tuple[bool, str]:
        dir_name = os.path.dirname(path) or "."
        try:
            fd, tmp = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as fh:
                    fh.write(content)
                os.replace(tmp, path)
                return True, f"File written: {path}"
            except Exception:
                os.unlink(tmp)
                raise
        except Exception as exc:
            return False, f"Write failed: {exc}"


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
