"""Unit tests for Azure AI Search infrastructure and index schema."""

import pytest
from app.azure.search import (
    INDEX_NAME,
    VECTOR_DIMENSIONS,
    AzureSearchManager,
    build_acadassist_index_schema,
)
from azure.search.documents.indexes.models import VectorSearchAlgorithmMetric


def test_search_index_schema_fields():
    """Verify all required fields exist in the index schema including visibility."""
    index = build_acadassist_index_schema()
    assert index.name == INDEX_NAME

    field_names = [f.name for f in index.fields]
    expected_fields = [
        "id",
        "chunk_id",
        "user_id",
        "visibility",
        "course_id",
        "subject_id",
        "document_id",
        "content",
        "title",
        "section_title",
        "document_title",
        "filename",
        "page_number",
        "slide_number",
        "chunk_index",
        "total_chunks",
        "content_type",
        "created_at",
        "content_vector",
    ]

    assert len(field_names) == 19
    for expected in expected_fields:
        assert expected in field_names, f"Missing expected field: {expected}"


def test_search_index_vector_configuration():
    """Verify vector search dimensions and cosine metric."""
    index = build_acadassist_index_schema()
    vector_field = next(f for f in index.fields if f.name == "content_vector")

    assert vector_field.vector_search_dimensions == VECTOR_DIMENSIONS
    assert len(index.vector_search.algorithms) == 1
    algo = index.vector_search.algorithms[0]
    assert algo.parameters.metric == VectorSearchAlgorithmMetric.COSINE


def test_search_manager_initialization():
    """Verify SearchManager endpoint and index configuration."""
    manager = AzureSearchManager(
        endpoint="https://testsearch.search.windows.net",
        index_name="custom-index",
    )
    assert manager.endpoint == "https://testsearch.search.windows.net"
    assert manager.index_name == "custom-index"


def test_search_manager_missing_endpoint():
    """Verify error on missing search endpoint."""
    manager = AzureSearchManager(endpoint=None)
    with pytest.raises(ValueError, match="Azure Search endpoint not configured"):
        manager.get_search_client()
