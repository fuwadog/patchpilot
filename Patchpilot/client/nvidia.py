"""NVIDIA Build API / OpenAI-compatible provider."""
from __future__ import annotations
import time
from typing import Iterator

from openai import OpenAI, APIError, APIConnectionError, RateLimitError

from .base import ModelProvider, StreamChunk


class NvidiaProvider(ModelProvider):
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        max_retries: int = 3,
        retry_delay: float = 1.5,
    ):
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
                    messages=messages,
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
                wait = self._retry_delay * (2 ** attempt)
                print(f"\n[Retry {attempt + 1}/{self._max_retries}] {e}. Waiting {wait:.1f}s…")
                time.sleep(wait)
            except APIError as e:
                raise RuntimeError(f"API error: {e}") from e
        raise RuntimeError(f"All {self._max_retries} retries failed: {last_exc}") from last_exc

    @staticmethod
    def _parse_stream(completion) -> Iterator[StreamChunk]:
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


class OllamaProvider(ModelProvider):
    """
    Ollama local provider (OpenAI-compatible endpoint).
    Usage: set base_url='http://localhost:11434/v1', api_key='ollama'
    """

    def __init__(self, model: str, base_url: str = "http://localhost:11434/v1"):
        self._client = OpenAI(base_url=base_url, api_key="ollama")
        self._model = model

    @property
    def name(self) -> str:
        return f"ollama:{self._model}"

    def stream(
        self,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
    ) -> Iterator[StreamChunk]:
        completion = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        for chunk in completion:
            if not getattr(chunk, "choices", None):
                continue
            delta = chunk.choices[0].delta
            content = getattr(delta, "content", None) or ""
            if content:
                yield StreamChunk(content=content)
