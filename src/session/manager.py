"""Session manager – orchestrates provider streaming and conversation history."""

from __future__ import annotations

from typing import Any, AsyncIterator, Optional

from ..client.base import ModelProvider, StreamChunk
from ..context.manager import ContextManager


class _NullDisplay:
    """No-op display helper used when display=None (Textual mode).

    Swallows display calls instead of requiring if-self._display guards
    everywhere, which keeps McCabe complexity in check.
    """

    def __getattr__(self, _: str) -> object:
        return lambda *args: None


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
        display: Any,
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

        disp: Any = self._display if self._display else _NullDisplay()
        full_response = ""

        try:
            for chunk in self._provider.stream(
                messages, self._temperature, self._max_tokens
            ):
                if chunk.reasoning:
                    disp.reasoning(chunk.reasoning)
                if chunk.content:
                    disp.stream(chunk.content)
                    full_response += chunk.content
        except (KeyboardInterrupt, RuntimeError) as e:
            if not self._display:
                raise
            if isinstance(e, KeyboardInterrupt):
                disp.info("\n[Stream interrupted by user]")
            else:
                disp.error(str(e))

        disp.newline()

        if full_response:
            self._ctx.add_assistant(full_response)

        return full_response or None

    async def stream_async(self, user_input: str) -> AsyncIterator[StreamChunk]:
        """Async streaming for Textual app. Yields chunks without Display dependency."""
        self._ctx.add_user(user_input)
        messages = self._ctx.build_messages()

        full_response = ""
        async for chunk in self._provider.async_stream(
            messages, self._temperature, self._max_tokens
        ):
            if chunk.content:
                full_response += chunk.content
            yield chunk

        if full_response:
            self._ctx.add_assistant(full_response)

    def reset(self) -> None:
        self._ctx.reset_convo()
