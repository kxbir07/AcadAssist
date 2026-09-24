"""Document summarization contract supporting multiple academic study modes."""

from typing import Any
from sqlalchemy.orm import Session

from app.models.document import Chunk, Document


VALID_SUMMARY_MODES = {"quick", "concise", "detailed", "exam", "revision", "bullet_points"}


def summarize_document(
    document_id: str,
    user_id: str,
    mode: str = "quick",
    db: Session | None = None,
) -> dict[str, Any]:
    """Retrieve document content, enforce user ownership, and prepare context for summarization.

    Supported modes:
        - quick / concise: High-level overview and main concepts.
        - detailed: Comprehensive breakdown section-by-section.
        - exam: High-yield concepts, definitions, and key exam questions/topics.
        - revision / bullet_points: Bullet-point formula/keyword quick reference.

    Returns:
        Structured context and summary payload integration-ready for downstream AI.
    """
    normalized_mode = (mode or "quick").strip().lower()
    if normalized_mode not in VALID_SUMMARY_MODES:
        raise ValueError(f"Invalid mode '{mode}'. Supported modes: {', '.join(sorted(VALID_SUMMARY_MODES))}")

    canonical_mode = "quick" if normalized_mode == "concise" else ("revision" if normalized_mode == "bullet_points" else normalized_mode)

    if db is None:
        raise ValueError("Database session is required to retrieve document.")

    # 1. Ownership enforcement
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    if not doc:
        raise FileNotFoundError(f"Document '{document_id}' not found.")
    if doc.user_id != user_id:
        raise PermissionError("Access denied: You do not own this document.")

    # 2. Retrieve chunks
    chunks = (
        db.query(Chunk)
        .filter(Chunk.document_id == document_id, Chunk.user_id == user_id)
        .order_by(Chunk.chunk_index)
        .all()
    )

    if not chunks:
        # Document not yet processed or empty
        return {
            "document_id": document_id,
            "title": doc.title,
            "filename": doc.filename,
            "mode": mode,
            "status": doc.status,
            "summary": f"Document '{doc.title}' is currently {doc.status}. Please process the document first.",
            "sections": [],
            "key_points": [],
            "sources": [],
            "content": "",
        }

    # Extract distinct sections and key excerpts
    sections: list[dict[str, Any]] = []
    seen_sections = set()
    full_content_parts: list[str] = []

    sources = [
        {
            "chunk_id": c.chunk_id,
            "document_title": doc.title,
            "filename": doc.filename,
            "page_number": c.page_number or 1,
            "content_snippet": (c.content[:200] + "...") if len(c.content) > 200 else c.content,
        }
        for c in chunks
    ]

    for c in chunks:
        full_content_parts.append(c.content)
        sec_name = c.section_title or (f"Page {c.page_number}" if c.page_number else f"Chunk {c.chunk_index + 1}")
        if sec_name not in seen_sections:
            seen_sections.add(sec_name)
            first_sentence = c.content.split(". ")[0].strip()
            sections.append({
                "section": sec_name,
                "page": c.page_number,
                "slide": c.slide_number,
                "overview": first_sentence[:200],
            })

    full_text = "\n\n".join(full_content_parts)

    # Attempt AI-powered summarization if Microsoft Foundry is configured
    ai_summary: str | None = None
    try:
        from app.azure.foundry import FoundryProjectManager
        from config.settings import get_settings

        mgr = FoundryProjectManager()
        if mgr.is_configured:
            client = mgr.get_openai_client()
            settings = get_settings()

            mode_instructions = {
                "quick": "Provide a clear, high-level summary covering the core concepts and architecture in 2-3 concise paragraphs.",
                "detailed": "Provide a comprehensive, section-by-section breakdown of all major mechanisms, protocols, and technical details.",
                "exam": "Provide an exam-oriented high-yield review highlighting definitions, comparisons, key trade-offs, and critical exam topics.",
                "revision": "Provide a quick revision summary formatted as clear bullet points covering key facts, equations, and rules.",
            }
            instruction = mode_instructions.get(canonical_mode, mode_instructions["quick"])

            prompt = (
                f"You are an expert academic tutor. Summarize the following study document '{doc.title}' ({doc.filename}).\n"
                f"Instructions: {instruction}\n"
                f"Ground your summary strictly in the provided text. Do not invent details not present in the material.\n\n"
                f"--- BEGIN DOCUMENT CONTENT ---\n{full_text[:8000]}\n--- END DOCUMENT CONTENT ---"
            )

            resp = client.chat.completions.create(
                model=settings.foundry_model_deployment,
                messages=[
                    {"role": "system", "content": "You are AcadAssist, an expert academic study assistant."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
            )
            ai_summary = resp.choices[0].message.content
    except Exception:
        ai_summary = None

    if ai_summary:
        summary_text = ai_summary
    else:
        # Grounded structured fallback based on actual sections and chunk content
        if canonical_mode == "quick":
            summary_text = (
                f"Overview of '{doc.title}': Covers {len(sections)} main sections across "
                f"{len(chunks)} chunks. Main themes include {', '.join([s['section'] for s in sections[:4]])}."
            )
        elif canonical_mode == "exam":
            summary_text = (
                f"Exam High-Yield Review for '{doc.title}': Focus on key concepts in "
                f"{', '.join([s['section'] for s in sections[:5]])}. Pay attention to core definitions and mechanisms."
            )
        elif canonical_mode == "revision":
            summary_text = (
                f"Quick Revision Sheet for '{doc.title}': Key points and definitions organized by section."
            )
        else:  # detailed
            summary_text = (
                f"Detailed Analysis of '{doc.title}': Full breakdown of {len(chunks)} chunks across "
                f"{len(sections)} sections, preserving page/slide boundaries."
            )

    return {
        "document_id": document_id,
        "title": doc.title,
        "filename": doc.filename,
        "mode": mode,
        "status": doc.status,
        "total_chunks": len(chunks),
        "sections": sections,
        "summary": summary_text,
        "sources": sources,
        "content": full_text,
    }
