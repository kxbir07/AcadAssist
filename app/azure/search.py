"""Azure AI Search Infrastructure Integration and Index Management.

Responsible for creating and managing the AcadAssist vector search index and executing
hybrid retrieval (BM25 + vector search) with mandatory user isolation and visibility control.
"""

import logging
from typing import List, Optional
from azure.core.credentials import TokenCredential
from azure.core.exceptions import ResourceNotFoundError
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    HnswParameters,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
    VectorSearch,
    VectorSearchAlgorithmMetric,
    VectorSearchProfile,
)

from config.settings import get_settings
from app.azure.credentials import get_azure_credential

logger = logging.getLogger(__name__)

INDEX_NAME = "acadassist-index"
VECTOR_DIMENSIONS = 1536
VECTOR_PROFILE_NAME = "acadassist-vector-profile"
VECTOR_ALGORITHM_NAME = "acadassist-hnsw-config"
EMBEDDING_MODEL_NAME = "text-embedding-3-small"


def build_acadassist_index_schema(index_name: str = INDEX_NAME) -> SearchIndex:
    """Build the SearchIndex schema for AcadAssist knowledge retrieval.

    Supports:
    - BM25 keyword search across content, title, section_title, document_title, filename
    - Vector search on 1536-dimensional content_vector using Cosine distance HNSW
    - Metadata filtering by user_id, visibility, course_id, subject_id, document_id
    """
    fields: List[SearchField] = [
        # Primary identifier
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        # Chunk, user, and visibility identifiers for security filtering
        SimpleField(name="chunk_id", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="user_id", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="visibility", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="course_id", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="subject_id", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="document_id", type=SearchFieldDataType.String, filterable=True),
        # Searchable textual content (BM25)
        SearchableField(name="content", type=SearchFieldDataType.String, analyzer_name="standard.lucene"),
        SearchableField(name="title", type=SearchFieldDataType.String, analyzer_name="standard.lucene"),
        SearchableField(name="section_title", type=SearchFieldDataType.String, analyzer_name="standard.lucene"),
        SearchableField(name="document_title", type=SearchFieldDataType.String, analyzer_name="standard.lucene"),
        SearchableField(name="filename", type=SearchFieldDataType.String, filterable=True),
        # Locational and structural metadata
        SimpleField(name="page_number", type=SearchFieldDataType.Int32, filterable=True, sortable=True),
        SimpleField(name="slide_number", type=SearchFieldDataType.Int32, filterable=True, sortable=True),
        SimpleField(name="chunk_index", type=SearchFieldDataType.Int32, filterable=True, sortable=True),
        SimpleField(name="total_chunks", type=SearchFieldDataType.Int32, filterable=True),
        SimpleField(name="content_type", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="created_at", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
        # 1536-dimension Cosine vector field for text-embedding-3-small embeddings
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            vector_search_dimensions=VECTOR_DIMENSIONS,
            vector_search_profile_name=VECTOR_PROFILE_NAME,
        ),
    ]

    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name=VECTOR_ALGORITHM_NAME,
                parameters=HnswParameters(metric=VectorSearchAlgorithmMetric.COSINE),
            )
        ],
        profiles=[
            VectorSearchProfile(
                name=VECTOR_PROFILE_NAME,
                algorithm_configuration_name=VECTOR_ALGORITHM_NAME,
            )
        ],
    )

    return SearchIndex(name=index_name, fields=fields, vector_search=vector_search)


_DEFAULT = object()


class AzureSearchManager:
    """Manager for Azure AI Search index lifecycle and client provision."""

    def __init__(
        self,
        endpoint: Optional[str] = _DEFAULT,
        index_name: Optional[str] = _DEFAULT,
        credential: Optional[TokenCredential] = None,
    ):
        settings = get_settings()
        self.endpoint = settings.azure_search_endpoint if endpoint is _DEFAULT else endpoint
        self.index_name = settings.azure_search_index if index_name is _DEFAULT else index_name
        self.credential = credential or get_azure_credential()
        self._index_client: Optional[SearchIndexClient] = None
        self._search_client: Optional[SearchClient] = None

    def get_index_client(self) -> SearchIndexClient:
        """Get or initialize SearchIndexClient for index management."""
        if self._index_client is None:
            if not self.endpoint:
                raise ValueError("Azure Search endpoint not configured. Set AZURE_SEARCH_ENDPOINT.")
            logger.info("Connecting SearchIndexClient to %s", self.endpoint)
            self._index_client = SearchIndexClient(
                endpoint=self.endpoint,
                credential=self.credential,
            )
        return self._index_client

    def get_search_client(self) -> SearchClient:
        """Get or initialize SearchClient for document querying."""
        if self._search_client is None:
            if not self.endpoint:
                raise ValueError("Azure Search endpoint not configured. Set AZURE_SEARCH_ENDPOINT.")
            self._search_client = SearchClient(
                endpoint=self.endpoint,
                index_name=self.index_name,
                credential=self.credential,
            )
        return self._search_client

    def create_or_update_index(self) -> SearchIndex:
        """Create or update the AcadAssist search index in Azure AI Search."""
        index_client = self.get_index_client()
        index_schema = build_acadassist_index_schema(self.index_name)
        result = index_client.create_or_update_index(index_schema)
        logger.info("Created or updated search index '%s' successfully", result.name)
        return result

    def index_exists(self) -> bool:
        """Check if the search index exists."""
        index_client = self.get_index_client()
        try:
            index_client.get_index(self.index_name)
            return True
        except ResourceNotFoundError:
            return False
        except Exception as exc:
            logger.warning("Error checking index existence: %s", exc)
            return False

    def search(
        self,
        user_id: str,
        query: str,
        course_id: Optional[str] = None,
        subject_id: Optional[str] = None,
        vector: Optional[List[float]] = None,
        top_k: int = 5,
    ) -> List[dict]:
        """Perform hybrid BM25 + vector search enforcing owner OR public visibility filter."""
        if not user_id or not user_id.strip():
            raise ValueError("user_id filter is mandatory for search_knowledge")

        search_client = self.get_search_client()
        # Enforce server-side security filter: owner OR public visibility
        filter_parts = [f"(user_id eq '{user_id.strip()}' or visibility eq 'public')"]
        if course_id:
            filter_parts.append(f"course_id eq '{course_id.strip()}'")
        if subject_id:
            filter_parts.append(f"subject_id eq '{subject_id.strip()}'")
        filter_expr = " and ".join(filter_parts)

        vector_queries = None
        if vector:
            try:
                from azure.search.documents.models import VectorizedQuery
                vector_queries = [
                    VectorizedQuery(
                        vector=vector,
                        k_nearest_neighbors=top_k,
                        fields="content_vector",
                    )
                ]
            except ImportError:
                logger.warning("VectorizedQuery could not be imported; proceeding with text search")

        results = search_client.search(
            search_text=query,
            filter=filter_expr,
            vector_queries=vector_queries,
            top=top_k,
        )
        return list(results)


__all__ = [
    "INDEX_NAME",
    "VECTOR_DIMENSIONS",
    "VECTOR_PROFILE_NAME",
    "VECTOR_ALGORITHM_NAME",
    "EMBEDDING_MODEL_NAME",
    "build_acadassist_index_schema",
    "AzureSearchManager",
]
