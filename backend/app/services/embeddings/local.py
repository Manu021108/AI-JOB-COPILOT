from __future__ import annotations

import hashlib
import math
import re

from app.core.config import get_settings
from app.services.embeddings.base import EmbeddingError

_DETERMINISTIC_DIM = 384

_STOP_TOKENS = {
    "the", "and", "for", "with", "that", "this", "from", "into", "about",
    "have", "your", "you", "will", "were", "been", "our", "they", "them",
    "their", "have", "has", "had", "also", "but", "not", "are", "was", "were",
    "very", "just", "can", "per", "etc", "via", "across", "within", "using",
}


class LocalEmbeddingProvider:
    """Local sentence-transformers based provider (all-MiniLM-L6-v2 by default).

    The model is loaded lazily so the app can start without the optional
    dependency installed.
    """

    name = "sentence-transformers"

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover - depends on optional dep
            raise EmbeddingError("sentence-transformers is not installed.") from exc
        self.model_name = model_name
        self._model = SentenceTransformer(model_name)

    def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode([text or "" for text in texts], normalize_embeddings=True)
        return [v.tolist() for v in vectors]

    def generate_embedding(self, text: str) -> list[float]:
        return self.generate_embeddings([text])[0]


class DeterministicEmbeddingProvider:
    """Offline, deterministic bag-of-token embeddings.

    Produces stable vectors for the same text on any machine, so it is safe for
    development, CI and automated tests, and acts as a graceful fallback when
    sentence-transformers is unavailable. Cosine similarity therefore measures
    token overlap on normalized 0..100 scale.
    """

    name = "deterministic"

    def generate_embedding(self, text: str) -> list[float]:
        vector = [0.0] * _DETERMINISTIC_DIM
        for token in _tokenize(text):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=4).digest()
            index = int.from_bytes(digest, "little") % _DETERMINISTIC_DIM
            vector[index] += 1.0
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [value / norm for value in vector]

    def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        return [self.generate_embedding(text) for text in texts]


def build_embedding_provider():
    """Build the configured embedding provider, falling back to the
    deterministic offline implementation."""
    kind = (get_settings().embedding_provider or "").strip().lower()
    if kind in {"sentence-transformers", "local"}:
        try:
            model = get_settings().embedding_model or "all-MiniLM-L6-v2"
            return LocalEmbeddingProvider(model)
        except Exception:
            return DeterministicEmbeddingProvider()
    return DeterministicEmbeddingProvider()


def _tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    return [word for word in words if len(word) >= 3 and word not in _STOP_TOKENS]