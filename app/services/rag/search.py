"""Azure AI Search service implementing hybrid retrieval and server-side user security."""

import json
import logging
import math
import re
from datetime import datetime, timezone
from typing import Any

from app.config import settings
from app.models.document import Chunk

logger = logging.getLogger(__name__)


class LocalHybridSearchIndex:
    """In-memory hybrid search index providing exact BM25 + cosine vector search for dev/testing."""

    def __init__(self):
        # docs: dict[str, dict[str, Any]] keyed by chunk_id
        self._docs: dict[str, dict[str, Any]] = {}

    def index_documents(self, documents: list[dict[str, Any]]) -> None:
        for doc in documents:
            chunk_id = doc["chunk_id"]
            self._docs[chunk_id] = doc

    def delete_by_document_id(self, document_id: str, user_id: str) -> int:
        to_delete = [
            cid for cid, doc in self._docs.items()
            if doc.get("document_id") == document_id and doc.get("user_id") == user_id
        ]
        for cid in to_delete:
            del self._docs[cid]
        return len(to_delete)

    def update_chunks_visibility(self, document_id: str, visibility: str) -> int:
        """Update visibility field for all chunks belonging to document_id."""
        updated = 0
        for doc in self._docs.values():
            if doc.get("document_id") == document_id:
                doc["visibility"] = visibility
                updated += 1
        return updated

    @staticmethod
    def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        if norm1 <= 0.0 or norm2 <= 0.0:
            return 0.0
        return max(0.0, min(1.0, dot / (norm1 * norm2)))

    @staticmethod
    def _bm25_score(query_tokens: list[str], content: str, title: str, section: str) -> float:
        text = f"{title} {section} {content}".lower()
        if not query_tokens or not text:
            return 0.0

        score = 0.0
        text_tokens = re.findall(r"\w+", text)
        doc_len = len(text_tokens) or 1
        avg_doc_len = 100.0
        k1 = 1.5
        b = 0.75

        for q in query_tokens:
            q_lower = q.lower()
            tf = text_tokens.count(q_lower)
            if tf > 0:
                idf = 1.5
                num = tf * (k1 + 1)
                den = tf + k1 * (1 - b + b * (doc_len / avg_doc_len))
                score += idf * (num / den)
                # Boost if in title or section
                if q_lower in title.lower():
                    score += 2.0
                if q_lower in section.lower():
                    score += 1.5

        return score

    def search_hybrid(
        self,
        query: str,
        user_id: str,
        query_vector: list[float],
        course_id: str | None = None,
        subject_id: str | None = None,
        top_k: int = 5,
        document_id: str | None = None,
    ) -> list[dict[str, Any]]:
        query_tokens = [t for t in re.findall(r"\w+", query) if len(t) > 2]
        scored_candidates = []
        for doc in self._docs.values():
            # Mandatory server-side user isolation and visibility control
            is_owner = doc.get("user_id") == user_id
            is_public = doc.get("visibility") == "public"
            if not (is_owner or is_public):
                continue

            # Strict document filter
            if document_id and doc.get("document_id") != document_id:
                continue

            # Optional course and subject filters
            if not document_id:
                if course_id and doc.get("course_id") != course_id:
                    continue
                if subject_id and doc.get("subject_id") != subject_id:
                    continue

            # 1. BM25 / Keyword score
            keyword_score = self._bm25_score(
                query_tokens,
                content=doc.get("content", ""),
                title=doc.get("document_title", ""),
                section=doc.get("section_title", "") or "",
            )

            # 2. Vector cosine similarity
            vector_score = self._cosine_similarity(query_vector, doc.get("content_vector", []))

            # 3. Hybrid ranking (normalized combination)
            hybrid_score = (0.5 * vector_score) + (0.5 * min(1.0, keyword_score / 5.0))

            # Filter out noise / non-matching candidates
            if hybrid_score < 0.1:
                continue

            scored_candidates.append({
                "chunk_id": doc.get("chunk_id"),
                "document_id": doc.get("document_id"),
                "course_id": doc.get("course_id"),
                "subject_id": doc.get("subject_id"),
                "content": doc.get("content"),
                "document_title": doc.get("document_title"),
                "section_title": doc.get("section_title"),
                "filename": doc.get("filename"),
                "page_number": doc.get("page_number"),
                "slide_number": doc.get("slide_number"),
                "score": round(float(hybrid_score), 4),
                "raw_score": hybrid_score,
            })

        # Sort descending by hybrid score
        scored_candidates.sort(key=lambda x: x["raw_score"], reverse=True)

        results = []
        for item in scored_candidates[:top_k]:
            item_copy = dict(item)
            item_copy.pop("raw_score", None)
            results.append(item_copy)

        return results


class AzureSearchService:
    """Azure AI Search service managing knowledge indexing and hybrid retrieval."""

    def __init__(self):
        self.endpoint = settings.AZURE_SEARCH_ENDPOINT or settings.AZURE_ENDPOINT
        self.api_key = settings.AZURE_SEARCH_KEY or settings.AZURE_API_KEY
        self.index_name = settings.AZURE_SEARCH_INDEX_NAME
        self.dimensions = settings.EMBEDDING_DIMENSIONS
        self.local_index: LocalHybridSearchIndex | None = None
        self.search_client = None

        has_credentials = bool(self.endpoint and (self.api_key or settings.AZURE_SEARCH_ENDPOINT))

        if settings.is_production():
            if not self.endpoint:
                raise ValueError("AZURE_SEARCH_ENDPOINT is required in production.")
            self._init_azure_client()
        else:
            if has_credentials:
                try:
                    self._init_azure_client()
                except Exception as e:
                    logger.warning(f"Could not connect to Azure AI Search, using local fallback: {e}")
                    self.local_index = LocalHybridSearchIndex()
            else:
                logger.info("Azure Search credentials not provided. Using local hybrid search index for dev/testing.")
                self.local_index = LocalHybridSearchIndex()

    def _init_azure_client(self):
        from azure.search.documents import SearchClient
        from azure.search.documents.indexes import SearchIndexClient
        from azure.search.documents.indexes.models import (
            CorsOptions,
            HnswAlgorithmConfiguration,
            SearchableField,
            SearchField,
            SearchFieldDataType,
            SearchIndex,
            SimpleField,
            VectorSearch,
            VectorSearchProfile,
        )

        if self.api_key:
            from azure.core.credentials import AzureKeyCredential
            credential = AzureKeyCredential(self.api_key)
        else:
            from app.azure.credentials import get_azure_credential
            credential = get_azure_credential()

        index_client = SearchIndexClient(endpoint=self.endpoint, credential=credential)

        # Ensure the index exists and has the authorization fields required by RAG.
        # `visibility` is part of the security filter, so an existing index created
        # before this field was introduced must be updated before it is used.
        try:
            existing_index = index_client.get_index(self.index_name)
        except Exception:
            logger.info(f"Creating Azure AI Search index '{self.index_name}'...")
            existing_index = None

        if existing_index is not None:
            existing_field_names = {field.name for field in existing_index.fields}
            if "visibility" not in existing_field_names:
                logger.info(
                    "Updating Azure AI Search index '%s' to add filterable visibility field.",
                    self.index_name,
                )
                existing_index.fields.append(
                    SimpleField(
                        name="visibility",
                        type=SearchFieldDataType.String,
                        filterable=True,
                    )
                )
                index_client.create_or_update_index(existing_index)
        else:
            fields = [
                SimpleField(name="id", type=SearchFieldDataType.String, key=True),
                SimpleField(name="chunk_id", type=SearchFieldDataType.String, filterable=True),
                SimpleField(name="user_id", type=SearchFieldDataType.String, filterable=True),
                SimpleField(name="visibility", type=SearchFieldDataType.String, filterable=True),
                SimpleField(name="course_id", type=SearchFieldDataType.String, filterable=True),
                SimpleField(name="subject_id", type=SearchFieldDataType.String, filterable=True),
                SimpleField(name="document_id", type=SearchFieldDataType.String, filterable=True),
                SearchableField(name="content", type=SearchFieldDataType.String),
                SearchableField(name="title", type=SearchFieldDataType.String),
                SearchableField(name="section_title", type=SearchFieldDataType.String),
                SearchableField(name="document_title", type=SearchFieldDataType.String),
                SearchableField(name="filename", type=SearchFieldDataType.String),
                SimpleField(name="page_number", type=SearchFieldDataType.Int32, filterable=True),
                SimpleField(name="slide_number", type=SearchFieldDataType.Int32, filterable=True),
                SimpleField(name="chunk_index", type=SearchFieldDataType.Int32, filterable=True),
                SimpleField(name="total_chunks", type=SearchFieldDataType.Int32),
                SimpleField(name="content_type", type=SearchFieldDataType.String),
                SimpleField(name="created_at", type=SearchFieldDataType.DateTimeOffset),
                SearchField(
                    name="content_vector",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True,
                    vector_search_dimensions=self.dimensions,
                    vector_search_profile_name="vector-profile",
                ),
            ]
            vector_search = VectorSearch(
                algorithms=[HnswAlgorithmConfiguration(name="hnsw-config", parameters={"metric": "cosine"})],
                profiles=[VectorSearchProfile(name="vector-profile", algorithm_configuration_name="hnsw-config")],
            )
            index = SearchIndex(name=self.index_name, fields=fields, vector_search=vector_search)
            index_client.create_or_update_index(index)

        self.search_client = SearchClient(
            endpoint=self.endpoint,
            index_name=self.index_name,
            credential=credential,
        )

    def index_chunks(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        """Upload chunk documents and vectors to Azure AI Search index (or local index)."""
        if not chunks:
            return

        documents = []
        for chunk, vector in zip(chunks, vectors):
            doc = {
                "id": chunk.chunk_id,
                "chunk_id": chunk.chunk_id,
                "user_id": chunk.user_id,
                "visibility": getattr(chunk, "visibility", "private"),
                "course_id": chunk.course_id,
                "subject_id": chunk.subject_id,
                "document_id": chunk.document_id,
                "content": chunk.content,
                "title": chunk.title or chunk.document_title or "",
                "section_title": chunk.section_title or "",
                "document_title": chunk.document_title or "",
                "filename": chunk.filename,
                "page_number": chunk.page_number,
                "slide_number": chunk.slide_number,
                "chunk_index": chunk.chunk_index,
                "total_chunks": chunk.total_chunks,
                "content_type": chunk.content_type,
                "created_at": chunk.created_at.isoformat(),
                "content_vector": vector,
            }
            documents.append(doc)

        if self.local_index is not None:
            self.local_index.index_documents(documents)
            return

        # Upload in batches to Azure Search
        batch_size = 500
        for i in range(0, len(documents), batch_size):
            batch = documents[i : i + batch_size]
            self.search_client.upload_documents(documents=batch)

    def delete_chunks_by_document(self, document_id: str, user_id: str) -> None:
        """Clean up all chunks for a document belonging to user_id."""
        if self.local_index is not None:
            self.local_index.delete_by_document_id(document_id, user_id)
            return

        # Query chunk IDs for document_id and user_id to delete
        filter_expr = f"document_id eq '{document_id}' and user_id eq '{user_id}'"
        results = self.search_client.search(
            search_text="",
            filter=filter_expr,
            select=["id"],
        )
        keys_to_delete = [{"id": r["id"]} for r in results]
        if keys_to_delete:
            self.search_client.delete_documents(documents=keys_to_delete)

    def update_chunks_visibility(self, document_id: str, visibility: str) -> int:
        """Update visibility field for all chunks of a document in search index."""
        if self.local_index is not None:
            return self.local_index.update_chunks_visibility(document_id, visibility)

        filter_expr = f"document_id eq '{document_id}'"
        results = self.search_client.search(
            search_text="",
            filter=filter_expr,
            select=["id"],
        )
        keys_to_update = [{"id": r["id"], "visibility": visibility} for r in results]
        if keys_to_update:
            self.search_client.merge_documents(documents=keys_to_update)
            return len(keys_to_update)
        return 0

    def search_hybrid(
        self,
        query: str,
        user_id: str,
        query_vector: list[float],
        course_id: str | None = None,
        subject_id: str | None = None,
        top_k: int = 5,
        document_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Perform hybrid search enforcing user isolation server-side."""
        if self.local_index is not None:
            return self.local_index.search_hybrid(
                query=query,
                user_id=user_id,
                query_vector=query_vector,
                course_id=course_id,
                subject_id=subject_id,
                top_k=top_k,
                document_id=document_id,
            )

        from azure.search.documents.models import VectorizedQuery

        # Build server-side OData security filter: owner user_id or public visibility
        filter_parts = [f"(user_id eq '{user_id}' or visibility eq 'public')"]
        if document_id:
            filter_parts.append(f"document_id eq '{document_id}'")
        else:
            if course_id:
                filter_parts.append(f"course_id eq '{course_id}'")
            if subject_id:
                filter_parts.append(f"subject_id eq '{subject_id}'")
        odata_filter = " and ".join(filter_parts)

        vector_query = VectorizedQuery(
            vector=query_vector,
            k_nearest_neighbors=top_k,
            fields="content_vector",
        )

        results = self.search_client.search(
            search_text=query,
            vector_queries=[vector_query],
            filter=odata_filter,
            top=top_k,
            select=[
                "chunk_id",
                "document_id",
                "course_id",
                "subject_id",
                "content",
                "document_title",
                "section_title",
                "filename",
                "page_number",
                "slide_number",
            ],
        )

        output: list[dict[str, Any]] = []
        for r in results:
            output.append({
                "chunk_id": r["chunk_id"],
                "document_id": r["document_id"],
                "course_id": r["course_id"],
                "subject_id": r["subject_id"],
                "content": r["content"],
                "document_title": r["document_title"],
                "section_title": r.get("section_title"),
                "filename": r["filename"],
                "page_number": r.get("page_number"),
                "slide_number": r.get("slide_number"),
                "score": round(float(r["@search.score"]), 4),
            })
        return output
