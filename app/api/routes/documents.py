"""Document management, access control, and processing API routes."""

import hashlib
import logging
import mimetypes
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.api.deps import get_db, get_processing_service, get_search, get_storage
from app.config import settings
from app.core.auth import get_current_user
from app.models.document import Chunk, Document
from app.models.shared import User
from app.schemas.document import (
    DocumentListResponse,
    DocumentProcessResponse,
    DocumentResponse,
    DocumentSummaryRequest,
    DocumentSummaryResponse,
)
from app.services.document_access import can_access_document, verify_document_access
from app.services.processing.pipeline import DocumentProcessingService
from app.services.rag.search import AzureSearchService
from app.services.rag.summarizer import summarize_document
from app.services.storage.azure_storage import AzureStorageService

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    course_id: str = Form(...),
    subject_id: str = Form(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    visibility: str = Form("private"),
    user_id: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    storage: AzureStorageService = Depends(get_storage),
):
    """Upload, deduplicate, and record a new academic document under the authenticated user's ownership."""
    # Server-derived trusted user identity
    owner_id = current_user.user_id

    raw_name = file.filename or ""
    safe_filename = Path(raw_name).name.strip()
    if not safe_filename:
        raise HTTPException(status_code=400, detail="Filename is required.")

    ext = Path(safe_filename).suffix.lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension '{ext}'. Allowed extensions: {', '.join(settings.ALLOWED_EXTENSIONS)}",
        )

    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty (0 bytes).")
    if len(file_bytes) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds max size of {settings.MAX_UPLOAD_SIZE_BYTES} bytes.",
        )

    # Compute SHA-256 checksum for content integrity and deduplication
    checksum = hashlib.sha256(file_bytes).hexdigest()

    # Deduplication: Check if identical document was already uploaded by this user
    existing = (
        db.query(Document)
        .filter(
            Document.user_id == owner_id,
            Document.checksum == checksum,
            Document.status != "failed",
        )
        .first()
    )
    if existing:
        logger.info(f"Duplicate upload detected for user {owner_id}, document {existing.document_id}")
        return existing

    # Normalize visibility
    clean_visibility = "public" if visibility.strip().lower() == "public" else "private"

    # Save to storage (Azure Blob or local fallback)
    try:
        storage_path = storage.save_file(file_bytes, safe_filename, owner_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save document to storage: {e}")

    doc_title = title.strip() if title and title.strip() else Path(safe_filename).stem

    doc = Document(
        user_id=owner_id,
        course_id=course_id,
        subject_id=subject_id,
        filename=safe_filename,
        file_type=ext.replace(".", ""),
        title=doc_title,
        description=description,
        storage_path=storage_path,
        visibility=clean_visibility,
        checksum=checksum,
        size_bytes=len(file_bytes),
        status="uploaded",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return doc


@router.get("", response_model=DocumentListResponse)
def list_documents(
    course_id: Optional[str] = Query(None, description="Optional course filter"),
    subject_id: Optional[str] = Query(None, description="Optional subject filter"),
    visibility: Optional[str] = Query(None, description="Filter by visibility (private/public)"),
    user_id: Optional[str] = Query(None, description="Optional user scope (cannot bypass authorization)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List documents accessible to the authenticated user (owned documents + public documents)."""
    # Scope to documents owned by the user OR marked as public
    query = db.query(Document).filter(
        (Document.user_id == current_user.user_id) | (Document.visibility == "public")
    )

    if course_id:
        query = query.filter(Document.course_id == course_id)
    if subject_id:
        query = query.filter(Document.subject_id == subject_id)
    if visibility:
        query = query.filter(Document.visibility == visibility.strip().lower())

    docs = query.order_by(Document.uploaded_at.desc()).all()
    return DocumentListResponse(documents=docs, total=len(docs))


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: str,
    user_id: Optional[str] = Query(None, description="Optional parameter, server validates identity"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve metadata for a specific document with centralized access control."""
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    verify_document_access(current_user, doc, require_owner=False)
    return doc


class DocumentVisibilityRequest(BaseModel):
    visibility: str = Field(..., description="Target visibility: 'public' or 'private'")


@router.patch("/{document_id}/visibility", response_model=DocumentResponse)
@router.put("/{document_id}/visibility", response_model=DocumentResponse)
def update_document_visibility(
    document_id: str,
    payload: DocumentVisibilityRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    search: AzureSearchService = Depends(get_search),
):
    """Update document visibility and synchronize visibility across all indexed chunks."""
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    verify_document_access(current_user, doc, require_owner=True)

    new_vis = payload.visibility.strip().lower()
    if new_vis not in ("public", "private"):
        raise HTTPException(status_code=400, detail="Visibility must be 'public' or 'private'.")

    old_vis = doc.visibility

    # Update search index first; if search synchronization fails, raise explicit error
    try:
        search.update_chunks_visibility(document_id, new_vis)
    except Exception as exc:
        logger.error("Failed to synchronize visibility for document '%s': %s", document_id, exc)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to synchronize chunk visibility in search index: {exc}",
        )

    # Update database records with compensation on failure
    try:
        doc.visibility = new_vis
        db.query(Chunk).filter(Chunk.document_id == document_id).update({"visibility": new_vis})
        db.commit()
        db.refresh(doc)
    except Exception as exc:
        logger.error("Database update failed for doc '%s'; reverting search index visibility: %s", document_id, exc)
        db.rollback()
        try:
            search.update_chunks_visibility(document_id, old_vis)
        except Exception as rev_exc:
            logger.critical("Failed to revert search index visibility for doc '%s': %s", document_id, rev_exc)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to persist document visibility update: {exc}",
        )

    return doc


@router.get("/{document_id}/download")
def download_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    storage: AzureStorageService = Depends(get_storage),
):
    """Securely stream or download document binary content with access verification."""
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    verify_document_access(current_user, doc, require_owner=False)

    try:
        file_bytes = storage.get_file(doc.storage_path)
    except Exception as e:
        logger.error(f"Failed to retrieve file from storage: {e}")
        raise HTTPException(status_code=500, detail="Could not retrieve file from storage.")

    media_type, _ = mimetypes.guess_type(doc.filename)
    media_type = media_type or "application/octet-stream"

    return Response(
        content=file_bytes,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{doc.filename}"'},
    )


@router.delete("/{document_id}")
def delete_document(
    document_id: str,
    user_id: Optional[str] = Query(None, description="Optional parameter, server validates identity"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    storage: AzureStorageService = Depends(get_storage),
    search: AzureSearchService = Depends(get_search),
):
    """Delete document from storage, search index, and database, strictly requiring ownership."""
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    verify_document_access(current_user, doc, require_owner=True)

    # 1. Clean up storage
    try:
        storage.delete_file(doc.storage_path)
    except Exception as e:
        logger.warning(f"Storage file cleanup exception for document {document_id}: {e}")

    # 2. Clean up search index
    search.delete_chunks_by_document(document_id, doc.user_id)

    # 3. Clean up DB chunks and document record
    db.query(Chunk).filter(Chunk.document_id == document_id).delete()
    db.delete(doc)
    db.commit()

    return {"status": "success", "message": f"Document '{document_id}' and all associated chunks deleted."}


@router.post("/{document_id}/process", response_model=DocumentProcessResponse)
def process_document_endpoint(
    document_id: str,
    user_id: Optional[str] = Query(None, description="Optional parameter, server validates identity"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    pipeline: DocumentProcessingService = Depends(get_processing_service),
):
    """Run full parsing, chunking, embedding, and indexing pipeline on an uploaded document."""
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    verify_document_access(current_user, doc, require_owner=True)

    try:
        processed_doc = pipeline.process_document(document_id, doc.user_id, db)
        return DocumentProcessResponse(
            document_id=processed_doc.document_id,
            status=processed_doc.status,
            message="Document successfully processed and indexed into knowledge base.",
            processed_at=processed_doc.processed_at,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Document file not found.")
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden: You do not own this document.")
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=f"Processing error: {ve}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document processing failed: {e}")


@router.post("/{document_id}/summarize", response_model=DocumentSummaryResponse)
def summarize_document_endpoint(
    document_id: str,
    body: DocumentSummaryRequest,
    user_id: Optional[str] = Query(None, description="Optional parameter, server validates identity"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Prepare structured document summary context according to requested mode."""
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    verify_document_access(current_user, doc, require_owner=False)

    try:
        summary_data = summarize_document(
            document_id=document_id,
            user_id=doc.user_id,
            mode=body.mode,
            db=db,
        )
        return DocumentSummaryResponse(**summary_data)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found.")
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden: Access denied to this document.")
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summarization preparation failed: {e}")


__all__ = ["router"]
