from __future__ import annotations
import os
from typing import Iterable, Callable

from prompt_toolkit.completion import Completer, Completion, CompleteEvent, PathCompleter, FuzzyCompleter
from prompt_toolkit.document import Document

class CLICompleter(Completer):
    """
    Custom completer for the project CLI.
    Handles top-level commands, subcommands, and path completions.
    """
    def __init__(
        self,
        get_commands: Callable[[], list[str]],
        get_loaded_files: Callable[[], list[str]],
        get_snippets: Callable[[], list[str]]
    ):
        self.get_commands = get_commands
        self.get_loaded_files = get_loaded_files
        self.get_snippets = get_snippets
        self.path_completer = PathCompleter(expanduser=True)

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        text = document.text_before_cursor
        
        # Only suggest if it looks like a command
        if not text.startswith("/"):
            return

        parts = text.split()
        if not parts:
            return

        cmd = parts[0]

        # Case 1: Completing the top-level command itself
        if len(parts) == 1 and not text.endswith(" "):
            commands = self.get_commands()
            for c in commands:
                if c.startswith(text):
                    yield Completion(c, start_position=-len(text))
            return

        # Case 2: Completing arguments/subcommands
        remaining_text = text[len(cmd):].lstrip()
        
        # Mapping commands to their arg types
        path_commands = {"/file", "/folder", "/unload-folder"}
        loaded_file_commands = {"/show", "/unload", "/pin", "/unpin", "/fix", "/refactor", "/patch"}
        snippet_commands = {"/snippet"}

        if cmd in path_commands:
            # Use PathCompleter for generic file system paths
            # We need to adjust the document for PathCompleter to work on just the arg part
            sub_doc = Document(remaining_text, cursor_position=len(remaining_text))
            for completion in self.path_completer.get_completions(sub_doc, complete_event):
                yield completion

        elif cmd in loaded_file_commands:
            # Suggest only loaded files
            loaded_files = self.get_loaded_files()
            for f in loaded_files:
                # Use basename or relative path for better UX if possible, 
                # but here we use what's in the store (usually absolute)
                if f.lower().startswith(remaining_text.lower()):
                    # Find a good display label (last part of path)
                    display = os.path.basename(f)
                    yield Completion(f, start_position=-len(remaining_text), display=display)

        elif cmd in snippet_commands:
            subparts = remaining_text.split()
            subcommands = ["save", "list", "show", "del"]
            
            # If we are completing the subcommand itself
            if len(subparts) == 0 or (len(subparts) == 1 and not remaining_text.endswith(" ")):
                for sc in subcommands:
                    if sc.startswith(remaining_text):
                        yield Completion(sc, start_position=-len(remaining_text))
            
            # If we are completing a snippet name for specific subcommands
            elif len(subparts) >= 1:
                subcmd = subparts[0]
                if subcmd in ["show", "del"]:
                    snippet_arg = remaining_text[len(subcmd):].lstrip()
                    snippets = self.get_snippets()
                    for s in snippets:
                        if s.lower().startswith(snippet_arg.lower()):
                            yield Completion(s, start_position=-len(snippet_arg))

def setup_autocomplete(dispatcher):
    """
    Sets up the prompt_toolkit completer using the dispatcher's state.
    """
    completer = CLICompleter(
        get_commands=dispatcher.get_all_commands,
        get_loaded_files=dispatcher.get_loaded_paths,
        get_snippets=dispatcher.get_snippet_names
    )
    # Wrap in FuzzyCompleter for better matching experience
    return FuzzyCompleter(completer)
