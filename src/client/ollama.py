"""Ollama local provider (OpenAI-compatible endpoint)."""

from __future__ import annotations

from typing import Iterator

from openai import OpenAI

from .base import ModelProvider, StreamChunk


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
            messages=messages,  # type: ignore
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        for chunk in completion:
            choices = getattr(chunk, "choices", None)
            if not choices:
                continue
            delta = choices[0].delta
            content = getattr(delta, "content", None) or ""
            if content:
                yield StreamChunk(content=content)
