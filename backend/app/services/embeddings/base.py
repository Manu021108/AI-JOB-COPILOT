from __future__ import annotations

from typing import Protocol


class EmbeddingError(Exception):
    """Raised when embeddings cannot be produced."""


class EmbeddingProvider(Protocol):
    """Abstraction over embedding backends (local, hosted, etc.).

    Matching logic depends only on this interface, so storage can be swapped
    later (e.g. pgvector, Qdrant) without touching the matchers.
    """

    name: str

    def generate_embedding(self, text: str) -> list[float]: ...

    def generate_embeddings(self, texts: list[str]) -> list[list[float]]: ...


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return max(-1.0, min(1.0, dot / (norm_a * norm_b)))


def normalize_score(cosine: float) -> float:
    """Maps cosine similarity (-1..1) onto a 0..100 score."""
    return (cosine + 1.0) / 2.0 * 100.0