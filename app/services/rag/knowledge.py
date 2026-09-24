"""Knowledge search integration contract for AcadAssist."""

import logging
from app.services.rag.embedding import EmbeddingService
from app.services.rag.search import AzureSearchService

logger = logging.getLogger(__name__)

# Shared singletons for search and embedding services
_embedding_service: EmbeddingService | None = None
_search_service: AzureSearchService | None = None


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


def get_search_service() -> AzureSearchService:
    global _search_service
    if _search_service is None:
        _search_service = AzureSearchService()
    return _search_service


def set_search_service(service: AzureSearchService) -> None:
    """Override search service instance (e.g. during testing)."""
    global _search_service
    _search_service = service


def search_knowledge(
    user_id: str,
    query: str,
    course_id: str | None = None,
    subject_id: str | None = None,
    top_k: int = 5,
) -> dict:
    """Search the Knowledge Base using hybrid keyword + vector retrieval with user isolation.

    Args:
        user_id: ID of the student making the request (strictly enforced server-side).
        query: Natural language question or search query.
        course_id: Optional course filter.
        subject_id: Optional subject filter.
        top_k: Maximum number of relevant chunks to retrieve (default: 5).

    Returns:
        dict: {"results": [...]} conforming to AcadAssist RAG integration contract.
    """
    if not user_id or not user_id.strip():
        raise ValueError("user_id is required for knowledge search.")
    if not query or not query.strip():
        return {"results": []}

    # Clamp top_k to safe range
    k = max(1, min(int(top_k), 50))

    embedding_service = get_embedding_service()
    search_service = get_search_service()

    query_vector = embedding_service.embed_text(query)

    results = search_service.search_hybrid(
        query=query,
        user_id=user_id,
        query_vector=query_vector,
        course_id=course_id,
        subject_id=subject_id,
        top_k=k,
    )

    return {"results": results}
