"""Session manager – orchestrates provider streaming and conversation history."""
from __future__ import annotations
from typing import Optional

from client.base import ModelProvider
from context.manager import ContextManager
from cli.display import Display


class SessionManager:
    """
    Drives a single interactive session:
    - Sends messages to the model provider
    - Updates conversation history in ContextManager
    - Delegates display to the Display helper
    """

    def __init__(
        self,
        provider: ModelProvider,
        context: ContextManager,
        display: Display,
        temperature: float,
        max_tokens: int,
    ):
        self._provider = provider
        self._ctx = context
        self._display = display
        self._temperature = temperature
        self._max_tokens = max_tokens

    def send(self, user_message: str, record_in_history: bool = True) -> Optional[str]:
        """
        Send a user message, stream the response, and return the full assistant reply.

        Args:
            user_message: The user's text.
            record_in_history: If True, appends user+assistant to conversation history.
                               Pass False for internal prompts (e.g. /fix generates a
                               structured prompt that should still be recorded).
        """
        if record_in_history:
            self._ctx.add_user(user_message)

        messages = self._ctx.build_messages(
            ephemeral_user_content=None if record_in_history else user_message
        )

        full_response = ""
        try:
            for chunk in self._provider.stream(messages, self._temperature, self._max_tokens):
                if chunk.reasoning:
                    self._display.reasoning(chunk.reasoning)
                if chunk.content:
                    self._display.stream(chunk.content)
                    full_response += chunk.content
        except KeyboardInterrupt:
            self._display.info("\n[Stream interrupted by user]")
        except RuntimeError as e:
            self._display.error(str(e))

        self._display.newline()

        if full_response:
            self._ctx.add_assistant(full_response)

        return full_response or None

    def reset(self) -> None:
        self._ctx.reset_convo()
