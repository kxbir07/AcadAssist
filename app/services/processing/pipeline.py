"""Document processing pipeline orchestrator."""

import json
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.document import Chunk, Document
from app.services.parsers.factory import ParserFactory
from app.services.processing.chunker import AcademicChunker
from app.services.processing.normalizer import TextNormalizer
from app.services.rag.embedding import EmbeddingService
from app.services.rag.search import AzureSearchService
from app.services.storage.azure_storage import AzureStorageService

logger = logging.getLogger(__name__)


class DocumentProcessingService:
    """Orchestrates end-to-end processing: parse -> normalize -> chunk -> embed -> index."""

    def __init__(
        self,
        storage_service: AzureStorageService | None = None,
        embedding_service: EmbeddingService | None = None,
        search_service: AzureSearchService | None = None,
    ):
        self.storage_service = storage_service or AzureStorageService()
        self.embedding_service = embedding_service or EmbeddingService()
        self.search_service = search_service or AzureSearchService()
        self.chunker = AcademicChunker()

    def process_document(self, document_id: str, user_id: str, db: Session) -> Document:
        """Execute the complete document processing pipeline with robust status transitions."""
        doc = db.query(Document).filter(Document.document_id == document_id).first()
        if not doc:
            raise FileNotFoundError(f"Document with ID '{document_id}' not found.")

        # Strict user ownership check
        if doc.user_id != user_id:
            raise PermissionError("Access denied: You do not own this document.")

        # Transition status to processing
        doc.status = "processing"
        db.commit()
        db.refresh(doc)

        try:
            logger.info(f"Starting processing for document {doc.document_id} ({doc.filename})")

            # 1. Retrieve raw document bytes from storage
            file_bytes = self.storage_service.get_file(doc.storage_path)

            # 2. Select parser and extract document units
            parser = ParserFactory.get_parser(doc.filename)
            extracted_doc = parser.parse(file_bytes, doc.filename)

            # 3. Normalize extracted units
            normalized_units = TextNormalizer.normalize_units(extracted_doc.units)
            if not normalized_units:
                raise ValueError("Document contains no readable text content.")

            # 4. Chunk document preserving provenance
            chunks = self.chunker.chunk_document(
                units=normalized_units,
                document_id=doc.document_id,
                user_id=doc.user_id,
                course_id=doc.course_id,
                subject_id=doc.subject_id,
                filename=doc.filename,
                document_title=doc.title,
            )

            if not chunks:
                raise ValueError("Chunking produced zero valid chunks.")

            # 5. Generate embeddings (1536-dim text-embedding-3-small)
            texts_to_embed = [c.content for c in chunks]
            vectors = self.embedding_service.embed_texts(texts_to_embed)

            # 6. Save chunks in DB and attach vector JSON
            # First remove any prior chunks if re-processing
            db.query(Chunk).filter(Chunk.document_id == doc.document_id).delete()
            for chunk, vec in zip(chunks, vectors):
                chunk.visibility = getattr(doc, "visibility", "private")
                chunk.content_vector = json.dumps(vec)
                db.add(chunk)

            # 7. Index chunks in Azure AI Search (or local hybrid search index)
            self.search_service.index_chunks(chunks, vectors)

            # 8. Mark document as processed
            doc.status = "processed"
            doc.processing_error = None
            doc.processed_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(doc)
            logger.info(f"Successfully processed document {doc.document_id}: indexed {len(chunks)} chunks.")
            return doc

        except Exception as e:
            logger.error(f"Processing failed for document {doc.document_id}: {e}", exc_info=True)
            doc.status = "failed"
            doc.processing_error = str(e)
            db.commit()
            db.refresh(doc)
            raise e
