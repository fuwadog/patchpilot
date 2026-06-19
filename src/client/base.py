"""Abstract model provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator, Iterator


class StreamChunk:
    __slots__ = ("content", "reasoning")

    def __init__(self, content: str = "", reasoning: str = ""):
        self.content = content
        self.reasoning = reasoning


class ModelProvider(ABC):
    """Base interface all model providers must implement."""

    @abstractmethod
    def stream(
        self,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
    ) -> Iterator[StreamChunk]:
        """Yield StreamChunk objects for each token as it arrives."""
        ...

    @abstractmethod
    def async_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncIterator[StreamChunk]:
        """Async variant of stream for use with Textual Workers."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name."""
        ...
