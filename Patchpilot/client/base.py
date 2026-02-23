"""Abstract model provider interface."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Iterator, Optional


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

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name."""
        ...
