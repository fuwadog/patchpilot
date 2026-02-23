#!/usr/bin/env python3
"""
main.py – CLI entry point.

All business logic lives in the modules below. This file only:
1. Reads config / prompts for API key
2. Wires components together
3. Runs the input loop
"""
from __future__ import annotations
import sys
import os

# Make package imports work when running from the project root
sys.path.insert(0, os.path.dirname(__file__))

from config import Config
from client.nvidia import NvidiaProvider
from context.manager import ContextManager
from session.manager import SessionManager
from files.manager import FileManager
from files.operations import PatchManager, SnippetManager
from cli.display import Display
from cli.commands import CommandDispatcher
from cli.autocomplete import setup_autocomplete
from prompt_toolkit import prompt


def resolve_api_key(cfg: Config) -> str:
    key = cfg.API_KEY
    if not key:
        try:
            key = input("Enter API key (or set OPENAI_API_KEY env var): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nNo API key provided. Exiting.")
            sys.exit(1)
    return key


def build_app() -> CommandDispatcher:
    cfg = Config()
    api_key = resolve_api_key(cfg)

    display = Display()

    provider = NvidiaProvider(
        api_key=api_key,
        base_url=cfg.BASE_URL,
        model=cfg.MODEL,
        max_retries=cfg.MAX_RETRIES,
        retry_delay=cfg.RETRY_DELAY,
    )

    context = ContextManager(
        system_prompt=cfg.SYSTEM_PROMPT,
        max_total_tokens=cfg.MAX_TOTAL_TOKENS,
        max_file_tokens=cfg.MAX_FILE_TOKENS,
        max_convo_messages=cfg.MAX_CONVO_MESSAGES,
    )

    session = SessionManager(
        provider=provider,
        context=context,
        display=display,
        temperature=cfg.TEMPERATURE,
        max_tokens=cfg.MAX_RESPONSE_TOKENS,
    )

    file_mgr = FileManager(
        context=context,
        max_files=cfg.MAX_FILES,
        default_extensions=cfg.DEFAULT_EXTENSIONS,
    )

    patch_mgr = PatchManager(
        backup=cfg.BACKUP_ON_WRITE,
        diff_preview=cfg.DIFF_PREVIEW,
    )

    snippets = SnippetManager()

    dispatcher = CommandDispatcher(
        session=session,
        files=file_mgr,
        context=context,
        patch=patch_mgr,
        snippets=snippets,
        display=display,
        max_file_chars=cfg.MAX_FILE_TOKENS,
    )

    return dispatcher


def main() -> None:
    dispatcher = build_app()
    display = Display()

    display.info("Interactive Chat Started")
    display.info("Type /help for commands.")
    display.separator()

    completer = setup_autocomplete(dispatcher)

    while True:
        try:
            # Use prompt_toolkit instead of standard input()
            user_input = prompt("\nYou: ", completer=completer)
        except (EOFError, KeyboardInterrupt):
            display.info("\nExiting.")
            break

        should_continue = dispatcher.dispatch(user_input)
        if not should_continue:
            break


if __name__ == "__main__":
    main()
