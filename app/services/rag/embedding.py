"""Embedding service providing text-embedding-3-small (1536 dimensions)."""

import hashlib
import json
import logging
import math
from typing import Protocol

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingProvider(Protocol):
    """Protocol for embedding providers."""

    def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        ...


class AzureOpenAIEmbeddingProvider:
    """Production provider using Azure OpenAI / OpenAI text-embedding-3-small."""

    def __init__(self):
        self.endpoint = settings.AZURE_OPENAI_ENDPOINT or settings.AZURE_ENDPOINT
        self.api_key = settings.AZURE_OPENAI_API_KEY or settings.AZURE_API_KEY or settings.OPENAI_API_KEY
        self.model = settings.EMBEDDING_MODEL
        self.dimensions = settings.EMBEDDING_DIMENSIONS

        if not self.api_key:
            raise ValueError("Azure OpenAI API key is missing.")

    def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        # Standard OpenAI-compatible embeddings endpoint
        if self.endpoint:
            url = f"{self.endpoint.rstrip('/')}/openai/deployments/{self.model}/embeddings?api-version=2024-02-01"
            headers = {"api-key": self.api_key, "Content-Type": "application/json"}
        else:
            url = "https://api.openai.com/v1/embeddings"
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        payload = {
            "input": texts,
            "model": self.model,
            "dimensions": self.dimensions,
        }

        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return [item["embedding"] for item in data["data"]]


class LocalDeterministicEmbeddingProvider:
    """Local deterministic provider for development and testing producing 1536-dimensional vectors."""

    def __init__(self, dimensions: int = 1536):
        self.dimensions = dimensions
        self.model = settings.EMBEDDING_MODEL

    def _embed_single(self, text: str) -> list[float]:
        vec = [0.0] * self.dimensions
        text_lower = text.lower().strip()
        if not text_lower:
            return vec

        # Tokenize and hash n-grams into vector slots
        words = text_lower.split()
        for word in words:
            # Word hashing
            h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
            slot = h % self.dimensions
            weight = 1.0 + (len(word) / 10.0)
            vec[slot] += weight

            # Bigram hashing for adjacent words
            if len(word) > 3:
                for i in range(len(word) - 2):
                    sub = word[i : i + 3]
                    sub_h = int(hashlib.sha256(sub.encode("utf-8")).hexdigest(), 16)
                    vec[sub_h % self.dimensions] += 0.3

        # Normalize to unit vector for cosine similarity
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0.0:
            vec = [x / norm for x in vec]
        return vec

    def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_single(t) for t in texts]


class EmbeddingService:
    """Centralized Embedding Service managing vector dimensions and provider selection."""

    def __init__(self):
        self.model_name = settings.EMBEDDING_MODEL
        self.dimensions = settings.EMBEDDING_DIMENSIONS
        self.provider: EmbeddingProvider

        raw_key = (
            settings.AZURE_OPENAI_API_KEY or settings.AZURE_API_KEY or settings.OPENAI_API_KEY or ""
        ).strip()
        is_placeholder = raw_key.startswith("YOUR_") or "PLACEHOLDER" in raw_key.upper()
        has_credentials = bool(raw_key and not is_placeholder)

        if settings.is_production():
            if not has_credentials:
                raise ValueError(
                    f"Production environment requires credentials for embedding model '{self.model_name}'."
                )
            self.provider = AzureOpenAIEmbeddingProvider()
        else:
            if has_credentials:
                try:
                    self.provider = AzureOpenAIEmbeddingProvider()
                except Exception as e:
                    logger.warning(f"Could not initialize Azure OpenAI provider, using local fallback: {e}")
                    self.provider = LocalDeterministicEmbeddingProvider(dimensions=self.dimensions)
            else:
                logger.info(
                    f"Using local deterministic embedding provider for model '{self.model_name}' ({self.dimensions} dims)."
                )
                self.provider = LocalDeterministicEmbeddingProvider(dimensions=self.dimensions)

    def embed_text(self, text: str) -> list[float]:
        """Generate embedding vector for a single string."""
        try:
            results = self.provider.generate_embeddings([text])
            return results[0] if results else [0.0] * self.dimensions
        except Exception as e:
            if not settings.is_production() and not isinstance(self.provider, LocalDeterministicEmbeddingProvider):
                logger.warning(f"Embedding failed via primary provider ({e}); falling back to local provider.")
                self.provider = LocalDeterministicEmbeddingProvider(dimensions=self.dimensions)
                results = self.provider.generate_embeddings([text])
                return results[0] if results else [0.0] * self.dimensions
            raise

    def get_embedding(self, text: str) -> list[float]:
        """Compatibility alias for embed_text."""
        return self.embed_text(text)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for a batch of strings."""
        if not texts:
            return []
        try:
            return self.provider.generate_embeddings(texts)
        except Exception as e:
            if not settings.is_production() and not isinstance(self.provider, LocalDeterministicEmbeddingProvider):
                logger.warning(f"Batch embedding failed via primary provider ({e}); falling back to local provider.")
                self.provider = LocalDeterministicEmbeddingProvider(dimensions=self.dimensions)
                return self.provider.generate_embeddings(texts)
            raise
