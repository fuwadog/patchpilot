from __future__ import annotations

import os
from typing import Any, Callable, ClassVar, Iterable

from prompt_toolkit.completion import (
    CompleteEvent,
    Completer,
    Completion,
    FuzzyCompleter,
    PathCompleter,
)
from prompt_toolkit.document import Document


class CLICompleter(Completer):
    """
    Custom completer for the project CLI.
    Handles top-level commands, subcommands, and path completions.
    """

    PATH_COMMANDS: ClassVar[set[str]] = {"/file", "/folder", "/unload-folder"}
    LOADED_FILE_COMMANDS: ClassVar[set[str]] = {
        "/show",
        "/unload",
        "/pin",
        "/unpin",
        "/fix",
        "/refactor",
        "/patch",
    }
    SNIPPET_COMMANDS: ClassVar[set[str]] = {"/snippet"}

    def __init__(
        self,
        get_commands: Callable[[], list[str]],
        get_loaded_files: Callable[[], list[str]],
        get_snippets: Callable[[], list[str]],
    ):
        self.get_commands = get_commands
        self.get_loaded_files = get_loaded_files
        self.get_snippets = get_snippets
        self.path_completer = PathCompleter(expanduser=True)

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        text = document.text_before_cursor

        if not text.startswith("/"):
            return

        parts = text.split()
        if not parts:
            return

        cmd = parts[0]

        if len(parts) == 1 and not text.endswith(" "):
            yield from self._complete_command(text)
            return

        remaining_text = text[len(cmd) :].lstrip()

        if cmd in self.PATH_COMMANDS:
            yield from self._complete_path_args(remaining_text, complete_event)
        elif cmd in self.LOADED_FILE_COMMANDS:
            yield from self._complete_file_args(remaining_text)
        elif cmd in self.SNIPPET_COMMANDS:
            yield from self._complete_snippet_args(remaining_text)

    def _complete_command(self, text: str) -> Iterable[Completion]:
        commands = self.get_commands()
        for c in commands:
            if c.startswith(text):
                yield Completion(c, start_position=-len(text))

    def _complete_path_args(
        self, remaining_text: str, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        sub_doc = Document(remaining_text, cursor_position=len(remaining_text))
        for completion in self.path_completer.get_completions(sub_doc, complete_event):
            yield completion

    def _complete_file_args(self, remaining_text: str) -> Iterable[Completion]:
        loaded_files = self.get_loaded_files()
        for f in loaded_files:
            if f.lower().startswith(remaining_text.lower()):
                display = os.path.basename(f)
                yield Completion(
                    f, start_position=-len(remaining_text), display=display
                )

    def _complete_snippet_args(self, remaining_text: str) -> Iterable[Completion]:
        subparts = remaining_text.split()
        subcommands = ["save", "list", "show", "del"]

        if len(subparts) == 0 or (
            len(subparts) == 1 and not remaining_text.endswith(" ")
        ):
            for sc in subcommands:
                if sc.startswith(remaining_text):
                    yield Completion(sc, start_position=-len(remaining_text))

        elif len(subparts) >= 1:
            subcmd = subparts[0]
            if subcmd in ["show", "del"]:
                snippet_arg = remaining_text[len(subcmd) :].lstrip()
                snippets = self.get_snippets()
                for s in snippets:
                    if s.lower().startswith(snippet_arg.lower()):
                        yield Completion(s, start_position=-len(snippet_arg))


def setup_autocomplete(dispatcher: Any) -> FuzzyCompleter:
    """
    Sets up the prompt_toolkit completer using the dispatcher's state.
    """
    completer = CLICompleter(
        get_commands=dispatcher.get_all_commands,
        get_loaded_files=dispatcher.get_loaded_paths,
        get_snippets=dispatcher.get_snippet_names,
    )
    # Wrap in FuzzyCompleter for better matching experience
    return FuzzyCompleter(completer)
