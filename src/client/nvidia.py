"""NVIDIA Build API / OpenAI-compatible provider."""

from __future__ import annotations

import time
from typing import Any, AsyncIterator, Iterator

from openai import APIConnectionError, APIError, AsyncOpenAI, OpenAI, RateLimitError

from .base import ModelProvider, StreamChunk


class NvidiaProvider(ModelProvider):
    """Provider for NVIDIA AI Foundation Models via OpenAI-compatible endpoint."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        max_retries: int = 3,
        retry_delay: float = 1.5,
    ):
        self._base_url = base_url
        self._api_key = api_key
        self._client = OpenAI(base_url=base_url, api_key=api_key)
        self._model = model
        self._max_retries = max_retries
        self._retry_delay = retry_delay

    @property
    def name(self) -> str:
        return f"nvidia:{self._model}"

    def stream(
        self,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
    ) -> Iterator[StreamChunk]:
        last_exc: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                completion = self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,  # type: ignore
                    temperature=temperature,
                    max_tokens=max_tokens,
                    extra_body={
                        "chat_template_kwargs": {
                            "enable_thinking": True,
                            "clear_thinking": False,
                        }
                    },
                    stream=True,
                )
                yield from self._parse_stream(completion)
                return
            except (APIConnectionError, RateLimitError) as e:
                last_exc = e
                wait = self._retry_delay * (2**attempt)
                print(
                    f"\n[Retry {attempt + 1}/{self._max_retries}] {e}. "
                    f"Waiting {wait:.1f}s…"
                )
                time.sleep(wait)
            except APIError as e:
                raise RuntimeError(f"API error: {e}") from e
        raise RuntimeError(
            f"All {self._max_retries} retries failed: {last_exc}"
        ) from last_exc

    @property
    def _async_client(self) -> AsyncOpenAI:
        """Lazily create an async OpenAI client."""
        if not hasattr(self, "_async_openai_client"):
            self._async_openai_client = AsyncOpenAI(
                base_url=self._base_url,
                api_key=self._api_key,
            )
        return self._async_openai_client

    async def async_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncIterator[StreamChunk]:
        """Async version of stream for Textual Workers."""
        import asyncio

        for attempt in range(self._max_retries):
            try:
                response = await self._async_client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True,
                )
                async for chunk in response:
                    if not getattr(chunk, "choices", None):
                        continue
                    first = chunk.choices[0] if chunk.choices else None
                    if not first or getattr(first, "delta", None) is None:
                        continue
                    delta = chunk.choices[0].delta
                    reasoning = getattr(delta, "reasoning_content", None) or ""
                    content = getattr(delta, "content", None) or ""
                    if reasoning or content:
                        yield StreamChunk(content=content, reasoning=reasoning)
                return
            except Exception:
                if attempt < self._max_retries - 1:
                    delay = self._retry_delay * (2**attempt)
                    await asyncio.sleep(delay)
                else:
                    raise

    @staticmethod
    def _parse_stream(completion: Any) -> Iterator[StreamChunk]:
        for chunk in completion:
            if not getattr(chunk, "choices", None):
                continue
            if not chunk.choices or getattr(chunk.choices[0], "delta", None) is None:
                continue
            delta = chunk.choices[0].delta
            reasoning = getattr(delta, "reasoning_content", None) or ""
            content = getattr(delta, "content", None) or ""
            if reasoning or content:
                yield StreamChunk(content=content, reasoning=reasoning)
