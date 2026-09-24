"""Tests for embedding service configuration and dimensions."""

import math
from app.config import settings
from app.services.rag.embedding import EmbeddingService, LocalDeterministicEmbeddingProvider


def test_embedding_configuration():
    assert settings.EMBEDDING_MODEL == "text-embedding-3-small"
    assert settings.EMBEDDING_DIMENSIONS == 1536

    service = EmbeddingService()
    assert service.model_name == "text-embedding-3-small"
    assert service.dimensions == 1536


def test_embedding_dimensions_and_unit_normalization():
    service = EmbeddingService()
    text = "Operating systems deadlock detection and Banker's algorithm"
    vector = service.embed_text(text)

    # Strictly 1536 dimensions
    assert len(vector) == 1536

    # Unit normalized for cosine similarity
    norm = math.sqrt(sum(x * x for x in vector))
    assert abs(norm - 1.0) < 1e-3


def test_embedding_batch_processing():
    service = EmbeddingService()
    texts = [
        "First chapter on process scheduling",
        "Second chapter on virtual memory",
        "Third chapter on file systems",
    ]
    vectors = service.embed_texts(texts)

    assert len(vectors) == 3
    for vec in vectors:
        assert len(vec) == 1536
        norm = math.sqrt(sum(x * x for x in vec))
        assert abs(norm - 1.0) < 1e-3


def test_embedding_consistency_between_chunk_and_query():
    service = EmbeddingService()
    chunk_text = "Deadlock prevention requires negating one of the four Coffman conditions."
    query_text = "Deadlock prevention Coffman conditions"

    chunk_vec = service.embed_text(chunk_text)
    query_vec = service.embed_text(query_text)

    # Cosine similarity between chunk and query
    dot_product = sum(a * b for a, b in zip(chunk_vec, query_vec))
    assert dot_product > 0.0  # Positive semantic relevance
