"""Tool Execution Dispatcher and Downstream Service Adapters.

Dispatches Agent tool calls to the respective domain services (Persons 2, 3, and 4).
Adheres strictly to shared contracts:
- Person 2: search_knowledge (POST /api/knowledge/search), summarize_document
- Person 3: generate_quiz, submit_quiz, get_performance, get_weak_topics
- Person 4: get_progress, get_upcoming_exams, create_study_plan, get_today_plan, generate_weekly_report

When downstream services are not yet running locally, provides clearly labeled
test adapters to enable isolated end-to-end testing and demo scenarios (e.g. 'Explain paging.').
"""

import copy
import json
import logging
import re
from typing import Any, Dict, List, Optional
from app.config import settings
from app.schemas.search import ChunkResult, SearchKnowledgeRequest, SearchKnowledgeResponse
from app.schemas.chat import SourceItem

logger = logging.getLogger(__name__)


# Unified underlying academic knowledge documents and chunks repository
KNOWLEDGE_DOCUMENTS: Dict[str, Dict[str, Any]] = {
    "doc-ostep-vm": {
        "document_id": "doc-ostep-vm",
        "document_title": "Operating Systems Concepts: Virtual Memory",
        "filename": "os_concepts_ch8_paging.pdf",
        "course_id": "course-cs-301",
        "subject_id": "subject-os",
        "keywords": ["paging", "page", "virtual memory", "tlb", "frame", "address translation"],
        "chunks": [
            ChunkResult(
                chunk_id="chunk-os-18-01",
                document_id="doc-ostep-vm",
                course_id="course-cs-301",
                subject_id="subject-os",
                content=(
                    "Paging is a memory management scheme that eliminates the need for contiguous allocation "
                    "of physical memory. Physical memory is partitioned into fixed-size blocks called page frames, "
                    "and logical memory is partitioned into blocks of the exact same size called pages. "
                    "The operating system maintains a page table for each process to translate virtual addresses "
                    "(virtual page number and offset) into physical addresses (frame number and offset)."
                ),
                document_title="Operating Systems Concepts: Virtual Memory",
                section_title="Paging Architecture & Translation",
                filename="os_concepts_ch8_paging.pdf",
                page_number=324,
                slide_number=None,
                score=0.94,
            ),
            ChunkResult(
                chunk_id="chunk-os-18-02",
                document_id="doc-ostep-vm",
                course_id="course-cs-301",
                subject_id="subject-os",
                content=(
                    "Advantages of paging include eliminating external fragmentation and simplifying allocation. "
                    "However, paging introduces internal fragmentation if memory requirements don't align with page sizes, "
                    "and requires hardware support like the Translation Lookaside Buffer (TLB) to speed up address translation."
                ),
                document_title="Operating Systems Concepts: Virtual Memory",
                section_title="Advantages and Overheads of Paging",
                filename="os_concepts_ch8_paging.pdf",
                page_number=326,
                slide_number=None,
                score=0.88,
            ),
        ],
        "summaries": {
            "concise": (
                "Paging is an operating systems memory management scheme that partitions physical memory into fixed-size "
                "frames and logical memory into pages, translating addresses via process page tables. It eliminates external "
                "fragmentation but may cause internal fragmentation, relying on Translation Lookaside Buffers (TLB) for "
                "accelerated hardware address translation."
            ),
            "detailed": (
                "This document details Operating Systems Virtual Memory architecture and paging mechanism. Key concepts established in the material:\n"
                "1. Memory Partitioning: Physical memory is divided into fixed page frames, and logical address space into pages of the exact same size, eliminating contiguous allocation requirements.\n"
                "2. Address Translation: Each process maintains a page table mapping virtual page numbers and offsets to physical frame numbers.\n"
                "3. Fragmentation & Overheads: Paging eliminates external fragmentation, but internal fragmentation remains possible within the last frame.\n"
                "4. Hardware Support: A Translation Lookaside Buffer (TLB) is required to cache frequent translations and maintain system performance."
            ),
            "bullet_points": (
                "• Architecture & Translation: Physical memory is partitioned into fixed-size page frames and logical memory into equal-sized pages. A per-process page table translates virtual page numbers and offsets into physical frame addresses.\n"
                "• Fragmentation Impact: Paging completely eliminates external fragmentation by allowing non-contiguous frame allocation; however, it introduces internal fragmentation if memory needs do not align with page sizes.\n"
                "• Hardware Optimization: The Translation Lookaside Buffer (TLB) serves as an associative hardware cache to accelerate virtual-to-physical address translation."
            ),
        },
    },
    "doc-dsa-search": {
        "document_id": "doc-dsa-search",
        "document_title": "Data Structures & Algorithms: Searching & Sorting",
        "filename": "dsa_searching_binary_search.pdf",
        "course_id": "course-cs-201",
        "subject_id": "subject-dsa",
        "keywords": ["binary search", "binary_search", "binary-search", "binarysearch", "search algorithm", "searching", "dsa search"],
        "chunks": [
            ChunkResult(
                chunk_id="chunk-dsa-bs-01",
                document_id="doc-dsa-search",
                course_id="course-cs-201",
                subject_id="subject-dsa",
                content=(
                    "Binary search is an efficient search algorithm that finds the position of a target value "
                    "within a sorted array. It compares the target value to the middle element of the array. "
                    "If they are not equal, the half in which the target cannot lie is eliminated, and the search "
                    "continues on the remaining half, repeating until the target value is found. "
                    "Binary search strictly requires that the array elements be sorted in order beforehand."
                ),
                document_title="Data Structures & Algorithms: Searching & Sorting",
                section_title="Binary Search Algorithm and Prerequisites",
                filename="dsa_searching_binary_search.pdf",
                page_number=45,
                slide_number=None,
                score=0.95,
            ),
            ChunkResult(
                chunk_id="chunk-dsa-bs-02",
                document_id="doc-dsa-search",
                course_id="course-cs-201",
                subject_id="subject-dsa",
                content=(
                    "Binary search runs in logarithmic time complexity, O(log n), in the worst and average cases, "
                    "where n is the number of elements in the array. This makes it significantly faster than linear "
                    "search, which has a time complexity of O(n). In each iteration or recursive call, the search space "
                    "is halved. The best-case time complexity is O(1) when the target is at the middle element. "
                    "The iterative implementation uses O(1) auxiliary space, whereas the recursive version uses O(log n) "
                    "auxiliary space due to call stack frames."
                ),
                document_title="Data Structures & Algorithms: Searching & Sorting",
                section_title="Time and Space Complexity Analysis",
                filename="dsa_searching_binary_search.pdf",
                page_number=48,
                slide_number=None,
                score=0.91,
            ),
            ChunkResult(
                chunk_id="chunk-dsa-bs-03",
                document_id="doc-dsa-search",
                course_id="course-cs-201",
                subject_id="subject-dsa",
                content=(
                    "When calculating the midpoint in binary search, using mid = (low + high) // 2 can cause integer "
                    "overflow in languages with fixed-width integers if low + high exceeds the maximum integer limit. "
                    "To prevent overflow, the midpoint should be calculated as mid = low + (high - low) // 2. "
                    "Binary search can also be adapted to find boundary conditions such as lower bound and upper bound "
                    "when duplicate elements are present."
                ),
                document_title="Data Structures & Algorithms: Searching & Sorting",
                section_title="Implementation Details and Overflow Prevention",
                filename="dsa_searching_binary_search.pdf",
                page_number=52,
                slide_number=None,
                score=0.87,
            ),
        ],
        "summaries": {
            "concise": (
                "Binary search is an efficient search algorithm on sorted arrays that repeatedly halves the search interval by "
                "comparing the target with the middle element. It achieves O(log n) worst-case time complexity, O(1) best-case time, "
                "and O(1) iterative space complexity. The midpoint must be calculated as low + (high - low) // 2 to prevent fixed-width "
                "integer overflow."
            ),
            "detailed": (
                "This document provides comprehensive analysis of the Binary Search algorithm and its implementation details:\n"
                "1. Core Algorithm & Prerequisites: Strictly requires a sorted array; compares the target against the middle element and eliminates the half in which the target cannot lie.\n"
                "2. Time Complexity: Halving the search interval yields logarithmic O(log n) worst-case time complexity compared to O(n) for linear search, with O(1) best case.\n"
                "3. Space Complexity: Requires O(1) auxiliary space iteratively, and O(log n) auxiliary stack space recursively.\n"
                "4. Overflow Prevention: Avoids fixed-width integer overflow in mid = (low + high) // 2 by using the mathematically equivalent mid = low + (high - low) // 2.\n"
                "5. Boundary Conditions: Supports adaptation to find lower and upper bounds when duplicate elements are present."
            ),
            "bullet_points": (
                "• Prerequisite: The array elements must strictly be sorted in order beforehand.\n"
                "• Search Mechanism: The algorithm compares the target value against the middle element, halving the search space in each iteration until the element is located.\n"
                "• Complexity Analysis: Achieves O(log n) worst and average case time complexity, significantly outperforming O(n) linear search. Best-case time complexity is O(1).\n"
                "• Space Complexity: Iterative implementation uses O(1) auxiliary space, whereas recursive calls require O(log n) stack frame space.\n"
                "• Arithmetic Safety & Bounds: Midpoint calculation must use low + (high - low) // 2 to avoid integer overflow in fixed-width systems, and can be adapted for lower/upper bound duplicate searches."
            ),
        },
    },
    "doc-gen-course": {
        "document_id": "doc-gen-course",
        "document_title": "Course Reference Syllabus",
        "filename": "syllabus.pdf",
        "course_id": "course-gen-101",
        "subject_id": "subject-general",
        "keywords": ["syllabus", "syllabus.pdf", "doc-gen-course", "curriculum", "schedule", "course overview", "course reference"],
        "chunks": [
            ChunkResult(
                chunk_id="chunk-gen-001",
                document_id="doc-gen-course",
                course_id="course-gen-101",
                subject_id="subject-general",
                content=(
                    "Course Reference Syllabus: This foundational curriculum establishes core Computer Science learning objectives "
                    "across Operating Systems (virtual memory, paging schemes, page frame allocation, address translation, and TLB performance) "
                    "and Data Structures & Algorithms (searching techniques, binary search mechanics on sorted arrays, logarithmic worst-case "
                    "complexity O(log n), space complexity, and overflow prevention with low + (high - low) // 2). It provides weekly lecture milestones, "
                    "textbook reading assignments, practice quizzes, and examination guidelines."
                ),
                document_title="Course Reference Syllabus",
                section_title="Course Overview & Schedule",
                filename="syllabus.pdf",
                page_number=1,
                slide_number=None,
                score=0.90,
            ),
        ],
        "summaries": {
            "concise": (
                "The Course Reference Syllabus establishes the academic curriculum and milestones across Operating Systems "
                "(virtual memory, paging architecture, and TLB address translation) and Data Structures & Algorithms "
                "(binary search prerequisites, logarithmic complexity analysis, and overflow-safe midpoint calculation), "
                "along with examination preparation guidelines."
            ),
            "detailed": (
                "This document serves as the foundational Course Reference Syllabus, detailing the academic roadmap:\n"
                "1. Curriculum Overview: Integrates core computer science subjects including Operating Systems and Data Structures & Algorithms.\n"
                "2. Systems Modules: Emphasizes virtual memory management, fixed-size frame partitioning, page table translation, and TLB caching.\n"
                "3. Algorithmic Modules: Details searching paradigms, strictly sorted array prerequisites, worst-case O(log n) time complexity, and midpoint overflow prevention.\n"
                "4. Course Milestones: Outlines weekly lecture topics, laboratory assignments, review quizzes, and final examination schedules."
            ),
            "bullet_points": (
                "• Curriculum Overview: Establishes foundational course roadmap covering Operating Systems and Data Structures & Algorithms.\n"
                "• Systems Concepts: Covers virtual memory, paging schemes, address translation, and TLB performance acceleration.\n"
                "• Algorithmic Concepts: Focuses on binary search on sorted arrays, logarithmic O(log n) complexity, and overflow-safe midpoint calculation.\n"
                "• Assessment & Logistics: Details weekly schedules, laboratory assignments, study milestones, and examination preparation."
            ),
        },
    },
}


class KnowledgeBaseAdapter:
    """Adapter for Person 2's knowledge retrieval services."""

    def __init__(self, endpoint_url: Optional[str] = None):
        self.endpoint_url = endpoint_url

    def search_knowledge(
        self,
        user_id: str,
        query: str,
        course_id: Optional[str] = None,
        subject_id: Optional[str] = None,
        top_k: int = 5,
        document_id: Optional[str] = None,
    ) -> SearchKnowledgeResponse:
        """Call Person 2's search_knowledge service according to the frozen contract."""
        logger.info("Executing search_knowledge for user=%s query='%s' doc=%s", user_id, query, document_id)

        # 1. First, attempt retrieval through the real AcadAssist search service
        try:
            from app.services.rag.search import AzureSearchService
            from app.services.rag.embedding import EmbeddingService
            embedder = EmbeddingService()
            query_vector = embedder.embed_text(query)
            search_service = AzureSearchService()
            real_results = search_service.search_hybrid(
                query=query,
                user_id=user_id,
                query_vector=query_vector,
                course_id=None if document_id else course_id,
                subject_id=None if document_id else subject_id,
                top_k=top_k,
                document_id=document_id,
            )
            if real_results:
                chunk_results = [
                    ChunkResult(
                        chunk_id=r["chunk_id"],
                        document_id=r["document_id"],
                        course_id=r.get("course_id"),
                        subject_id=r.get("subject_id"),
                        content=r["content"],
                        document_title=r["document_title"],
                        section_title=r.get("section_title"),
                        filename=r["filename"],
                        page_number=r.get("page_number"),
                        slide_number=r.get("slide_number"),
                        score=r.get("score", 0.9),
                    )
                    for r in real_results
                ]

                # A document-specific request is authoritative. If Azure Search
                # has only a partial/stale index for that document, supplement it
                # from the persisted processed chunks rather than failing a valid
                # uploaded document. Azure results remain the primary ranked source.
                if document_id and len(chunk_results) < top_k:
                    try:
                        from app.database.session import SessionLocal
                        from app.models.document import Chunk
                        with SessionLocal() as db_session:
                            db_chunks = (
                                db_session.query(Chunk)
                                .filter(
                                    Chunk.document_id == document_id,
                                    Chunk.user_id == user_id,
                                )
                                .all()
                            )
                            existing_ids = {c.chunk_id for c in chunk_results}
                            for m in db_chunks:
                                if m.chunk_id in existing_ids:
                                    continue
                                chunk_results.append(
                                    ChunkResult(
                                        chunk_id=m.chunk_id,
                                        document_id=m.document_id,
                                        course_id=m.course_id,
                                        subject_id=m.subject_id,
                                        content=m.content,
                                        document_title=m.document_title or m.title or "Uploaded Material",
                                        section_title=m.section_title,
                                        filename=m.filename or "document.pdf",
                                        page_number=m.page_number,
                                        slide_number=m.slide_number,
                                        score=0.91,
                                    )
                                )
                                if len(chunk_results) >= top_k:
                                    break
                    except Exception as supplement_exc:
                        logger.debug("Document chunk supplement failed: %s", supplement_exc)

                return SearchKnowledgeResponse(results=chunk_results[:top_k])
        except Exception as exc:
            logger.debug("Real search service query check: %s", exc)

        # 2. Check local database Chunk store if search service returned empty
        try:
            from app.database.session import SessionLocal
            from app.models.document import Chunk, Document
            with SessionLocal() as db_session:
                q_terms = [t.lower() for t in query.split() if len(t) > 2]
                filters = [(Chunk.user_id == user_id) | (Chunk.visibility == "public")]
                if document_id:
                    filters.append(Chunk.document_id == document_id)
                else:
                    if course_id:
                        filters.append(Chunk.course_id == course_id)
                    if subject_id:
                        filters.append(Chunk.subject_id == subject_id)

                db_chunks = (
                    db_session.query(Chunk)
                    .filter(*filters)
                    .all()
                )
                matching = []
                # If specific topic/search terms exist and query is not general or document-targeted
                if q_terms and query.lower().strip() not in ["general", "overview"] and not document_id:
                    for ch in db_chunks:
                        c_lower = (ch.content or "").lower()
                        t_lower = (ch.document_title or "").lower()
                        f_lower = (ch.filename or "").lower()
                        if any(term in c_lower or term in t_lower or term in f_lower for term in q_terms):
                            matching.append(ch)
                else:
                    matching = db_chunks

                if matching:
                    return SearchKnowledgeResponse(
                        results=[
                            ChunkResult(
                                chunk_id=m.chunk_id,
                                document_id=m.document_id,
                                course_id=m.course_id,
                                subject_id=m.subject_id,
                                content=m.content,
                                document_title=m.document_title or m.title or "Uploaded Material",
                                section_title=m.section_title,
                                filename=m.filename or "document.pdf",
                                page_number=m.page_number,
                                slide_number=m.slide_number,
                                score=0.92,
                            )
                            for m in matching[:top_k]
                        ]
                    )
        except Exception as exc:
            logger.debug("DB chunk search check: %s", exc)

        if document_id:
            logger.info("Document-specific search for document_id=%s returned no chunks", document_id)
            return SearchKnowledgeResponse(results=[])

        from app.config import settings
        if settings.is_production():
            logger.info("Production mode: returning only verified search index results for user=%s", user_id)
            return SearchKnowledgeResponse(results=[])

        q_lower = query.lower().strip()

        matched_doc_id = None

        if any(term in q_lower for term in ["paging", "page", "virtual memory", "tlb", "frame"]):
            matched_doc_id = "doc-ostep-vm"
        elif (
            ("binary" in q_lower and "search" in q_lower)
            or any(term in q_lower for term in ["binary_search", "binary-search", "binarysearch", "searching"])
            or ("dsa" in q_lower and "search" in q_lower)
        ):
            matched_doc_id = "doc-dsa-search"
        elif any(term in q_lower for term in ["syllabus", "syllabus.pdf", "doc-gen-course", "curriculum"]):
            matched_doc_id = "doc-gen-course"
        else:
            # Check document IDs and filenames directly
            for doc_key, doc_data in KNOWLEDGE_DOCUMENTS.items():
                if (
                    doc_key.lower() in q_lower
                    or doc_data["filename"].lower() in q_lower
                    or doc_data["document_title"].lower() in q_lower
                ):
                    matched_doc_id = doc_key
                    break

        if not matched_doc_id:
            matched_doc_id = "doc-gen-course"

        doc = KNOWLEDGE_DOCUMENTS[matched_doc_id]
        results = [copy.deepcopy(c) for c in doc["chunks"][:top_k]]
        for c in results:
            if course_id:
                c.course_id = course_id
            if subject_id:
                c.subject_id = subject_id

        return SearchKnowledgeResponse(results=results)

    def summarize_document(
        self,
        user_id: str,
        document_id: str,
        mode: str = "concise",
        db: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Generate a grounded summary for an academic document from retrieved content.

        Retrieves actual document chunks associated with document_id from the shared knowledge base.
        Generates summary from retrieved content with document/source references.
        If document content cannot be found, returns a clear insufficient-material / not-found response.
        """
        logger.info("Summarizing document_id=%s for user_id=%s, mode=%s", document_id, user_id, mode)
        doc_id_clean = (document_id or "").strip().lower()

        if not doc_id_clean:
            return {
                "document_id": document_id,
                "mode": mode,
                "summary": None,
                "status": "not_found",
                "message": "Document ID must not be empty. Please specify a valid document_id (e.g., 'doc-ostep-vm', 'doc-dsa-search', or 'doc-gen-course').",
                "sources": [],
            }

        # Check real DB for document access and summarization
        try:
            from fastapi import HTTPException
            from app.models.document import Document
            from app.models.shared import User
            from app.services.document_access import verify_document_access
            from app.services.rag.summarizer import summarize_document as real_summarize

            def _check_db(session):
                db_doc = session.query(Document).filter(Document.document_id == document_id).first()
                if db_doc:
                    db_user = session.query(User).filter(User.user_id == user_id).first()
                    if not db_user:
                        db_user = User(user_id=user_id, email=f"{user_id}@test.local", name=user_id)
                    # Enforce zero-trust access: owner or public
                    verify_document_access(db_user, db_doc, require_owner=False)
                    res = real_summarize(document_id, db_doc.user_id, mode, session)
                    return {
                        "document_id": document_id,
                        "mode": mode,
                        "summary": res.get("summary"),
                        "status": "success",
                        "sources": res.get("sources", []),
                    }
                return None

            if db is not None:
                res = _check_db(db)
                if res:
                    return res
            else:
                from app.database.session import SessionLocal
                with SessionLocal() as session:
                    res = _check_db(session)
                    if res:
                        return res
        except PermissionError:
            raise
        except Exception as exc:
            # If HTTPException(403) was raised by verify_document_access
            if getattr(exc, "status_code", None) == 403:
                raise PermissionError("Forbidden: Access denied to this document.")
            logger.debug("Database summarization fallback: %s", exc)

        if settings.is_production():
            logger.warning("Production mode active: refusing hardcoded demo document fallback for doc_id=%s", document_id)
            raise FileNotFoundError(f"Document '{document_id}' was not found in the academic knowledge base.")

        # Find document from the shared KNOWLEDGE_DOCUMENTS repository
        matched_doc = None
        for doc_key, doc_data in KNOWLEDGE_DOCUMENTS.items():
            if (
                doc_key.lower() == doc_id_clean
                or doc_data["filename"].lower() == doc_id_clean
                or doc_data["document_title"].lower() == doc_id_clean
                or (doc_id_clean in ["paging", "os-paging", "doc-os-18"] and doc_key == "doc-ostep-vm")
                or (doc_id_clean in ["binary-search", "binary search", "doc-dsa-bs"] and doc_key == "doc-dsa-search")
                or (doc_id_clean in ["syllabus", "syllabus.pdf", "curriculum"] and doc_key == "doc-gen-course")
            ):
                matched_doc = doc_data
                break

        if not matched_doc:
            logger.warning("Document '%s' not found in knowledge base", document_id)
            return {
                "document_id": document_id,
                "mode": mode,
                "summary": None,
                "status": "not_found",
                "message": (
                    f"Document '{document_id}' was not found in the academic knowledge base. "
                    "Please verify the document_id or upload relevant study material."
                ),
                "sources": [],
            }

        mode_clean = (mode or "concise").strip().lower()
        summary_text = matched_doc["summaries"].get(mode_clean, matched_doc["summaries"].get("concise"))

        sources = [
            {
                "chunk_id": c.chunk_id,
                "document_title": c.document_title,
                "section_title": c.section_title,
                "filename": c.filename,
                "page_number": c.page_number,
            }
            for c in matched_doc["chunks"]
        ]

        return {
            "document_id": matched_doc["document_id"],
            "document_title": matched_doc["document_title"],
            "filename": matched_doc["filename"],
            "mode": mode,
            "summary": summary_text,
            "sources": sources,
            "status": "success",
        }


# Shared in-memory quiz store mapping quiz_id -> quiz_data
_quiz_store: Dict[str, Dict[str, Any]] = {
    "q1": {
        "quiz_id": "q1",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "questions": [
            {
                "id": "q1",
                "question": "Sample practice question?",
                "options": ["A", "B", "C", "D"],
                "correct_answer": "A",
                "explanation": "Sample explanation",
            }
        ],
    }
}

# Rotation offset and sequential counter per topic key to generate distinct quizzes across requests
_topic_rotation: Dict[str, int] = {}
_quiz_counter: Dict[str, int] = {}


def _normalize_option_letter(text: str) -> Optional[str]:
    """Extract option letter (e.g. 'A' from 'A) ...' or 'a')."""
    if not text:
        return None
    s = str(text).strip()
    if not s:
        return None
    if len(s) == 1 and s.isalpha():
        return s.upper()
    if len(s) >= 2 and s[0].isalpha() and s[1] in [")", ".", ":", "-", " "]:
        return s[0].upper()
    return None


def _is_answer_correct(user_ans: Any, correct_ans: str, options: List[str]) -> bool:
    """Check whether a user submitted answer matches the correct answer."""
    if user_ans is None:
        return False

    user_str = str(user_ans).strip()
    correct_str = str(correct_ans).strip()

    # 1. Direct case-insensitive match
    if user_str.lower() == correct_str.lower():
        return True

    # 2. Extract option letters (e.g. 'A' vs 'A) ...')
    user_letter = _normalize_option_letter(user_str)
    correct_letter = _normalize_option_letter(correct_str)
    if user_letter and correct_letter and user_letter == correct_letter:
        return True

    # 3. Text without letter prefix match
    def clean_prefix(val: str) -> str:
        letter = _normalize_option_letter(val)
        if letter and len(val) > 2 and val[1] in [")", ".", ":", "-", " "]:
            return val[2:].strip().lower()
        return val.strip().lower()

    if clean_prefix(user_str) == clean_prefix(correct_str):
        return True

    # 4. If user submitted full option text matching the correct option
    for opt in options:
        opt_str = str(opt).strip()
        if user_str.lower() == opt_str.lower():
            if _normalize_option_letter(opt_str) == correct_letter:
                return True

    return False


def _extract_user_answer(answers: Any, q_id: str, q_index: int) -> Optional[Any]:
    """Extract user's answer for a specific question from various answers payload shapes."""
    if isinstance(answers, dict):
        for key in [q_id, str(q_index + 1), q_index + 1, str(q_index), q_index]:
            if key in answers:
                return answers[key]
        return None
    elif isinstance(answers, list):
        if q_index < len(answers):
            item = answers[q_index]
            if isinstance(item, dict):
                for key in ["answer", "selected", "user_answer", "choice", q_id, str(q_index + 1)]:
                    if key in item:
                        return item[key]
                if len(item) == 1:
                    return list(item.values())[0]
            return item
        return None
    return None


class AssessmentAdapter:
    """Adapter for Person 3's assessment and quiz services."""

    def __init__(self, kb_adapter: Optional[KnowledgeBaseAdapter] = None):
        self.kb_adapter = kb_adapter or KnowledgeBaseAdapter()

    def generate_quiz(
        self,
        user_id: str,
        subject_id: Optional[str] = None,
        topic_ids: Any = None,
        difficulty: str = "medium",
        count: int = 5,
        document_id: Optional[str] = None,
        course_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate meaningful practice quiz questions grounded in retrieved study material."""
        logger.info(
            "Generating quiz for user=%s, subject=%s, topics=%s, difficulty=%s, count=%s, doc=%s",
            user_id,
            subject_id,
            topic_ids,
            difficulty,
            count,
            document_id,
        )

        # Extract search keywords from topic_ids and subject_id
        topic_terms = []
        if isinstance(topic_ids, list):
            topic_terms.extend(str(t) for t in topic_ids if t)
        elif topic_ids:
            topic_terms.append(str(topic_ids))

        query_str = " ".join(topic_terms).strip()
        if not query_str and subject_id:
            query_str = subject_id.strip()
        if not query_str:
            query_str = "general"

        # Retrieve relevant study material from knowledge layer
        kb_resp = self.kb_adapter.search_knowledge(
            user_id=user_id,
            query=query_str,
            course_id=course_id,
            subject_id=subject_id,
            top_k=max(count * 2, 8),
            document_id=document_id,
        )

        if document_id:
            doc_chunks = [c for c in kb_resp.results if c.document_id == document_id]
            topic_terms = [
                w.lower()
                for t in (topic_ids or [])
                for w in re.findall(r"\w+", t)
                if len(w) > 2 and w.lower() not in {"core", "concepts", "easy", "medium", "hard", "quiz", "questions", "assessment", "overview", "study", "notes", "material", "practice", "and", "the", "for"}
            ]
            if topic_terms and doc_chunks:
                matched = [
                    c for c in doc_chunks
                    if any(
                        term in (c.content or "").lower()
                        or term in (c.section_title or "").lower()
                        or term in (c.document_title or "").lower()
                        or term in (c.filename or "").lower()
                        for term in topic_terms
                    )
                ]
                valid_chunks = matched if matched else doc_chunks
            else:
                valid_chunks = doc_chunks
        else:
            # Filter out generic syllabus fallback chunks and non-matching low-relevance results
            q_words = [w.lower() for w in query_str.split() if len(w) > 2]
            valid_chunks = [
                c for c in kb_resp.results
                if c.chunk_id != "chunk-gen-001"
                and (
                    c.score is None
                    or c.score >= 0.025
                    or any(w in (c.content or "").lower() for w in q_words)
                    or any(w in (c.document_title or "").lower() for w in q_words)
                )
            ]

        # If no relevant material exists, return insufficient material response per requirement 7
        if not valid_chunks:
            logger.info("Insufficient study material found for query '%s' doc='%s'", query_str, document_id)
            return {
                "quiz_id": None,
                "subject_id": subject_id,
                "topic_ids": topic_ids,
                "difficulty": difficulty,
                "count": 0,
                "questions": [],
                "status": "insufficient_material",
                "message": (
                    f"Insufficient study material found in the selected document for '{query_str}'. "
                    "Please upload relevant study materials or select a supported topic."
                    if document_id else
                    f"Insufficient study material found for '{query_str}'. "
                    "Please upload relevant study materials or select a supported topic (e.g., 'Binary Search' or 'Paging')."
                ),
            }

        # Build grounded questions from retrieved materials
        all_questions: List[Dict[str, Any]] = []
        q_lower = query_str.lower()
        chunk_ids = {c.chunk_id for c in valid_chunks}

        if not document_id and (
            ("binary" in q_lower and "search" in q_lower)
            or any(term in q_lower for term in ["binary_search", "binary-search", "binarysearch", "searching"])
            or any(cid.startswith("chunk-dsa-bs") for cid in chunk_ids)
        ):
            all_questions = [
                # Variant 1 (Prerequisite - sorted order)
                {
                    "id": "q1",
                    "question": "What is the prerequisite for applying binary search to an array?",
                    "options": [
                        "A) The array must be sorted in order.",
                        "B) The array must be unsorted.",
                        "C) The array size must be prime.",
                        "D) The array elements must be unique.",
                    ],
                    "correct_answer": "A) The array must be sorted in order.",
                    "explanation": (
                        "Binary search eliminates half the remaining elements each step based on comparisons with the middle element. "
                        "This strictly requires the array to be sorted beforehand."
                    ),
                    "source": {
                        "chunk_id": "chunk-dsa-bs-01",
                        "document_title": "Data Structures & Algorithms: Searching & Sorting",
                        "filename": "dsa_searching_binary_search.pdf",
                        "page_number": 45,
                    },
                },
                # Variant 2 (Worst-case complexity O(log n))
                {
                    "id": "q2",
                    "question": "What is the time complexity of binary search in the worst case?",
                    "options": [
                        "A) O(n)",
                        "B) O(log n)",
                        "C) O(n log n)",
                        "D) O(1)",
                    ],
                    "correct_answer": "B) O(log n)",
                    "explanation": (
                        "Because the search interval is halved with each iteration, the maximum number of comparisons is proportional "
                        "to log2(n), giving O(log n) worst-case time complexity."
                    ),
                    "source": {
                        "chunk_id": "chunk-dsa-bs-02",
                        "document_title": "Data Structures & Algorithms: Searching & Sorting",
                        "filename": "dsa_searching_binary_search.pdf",
                        "page_number": 48,
                    },
                },
                # Variant 3 (Midpoint calculation & overflow prevention)
                {
                    "id": "q3",
                    "question": "Why is the midpoint sometimes calculated as mid = low + (high - low) // 2 instead of mid = (low + high) // 2?",
                    "options": [
                        "A) To handle floating-point numbers.",
                        "B) To avoid integer overflow.",
                        "C) To improve time complexity.",
                        "D) To simplify the code.",
                    ],
                    "correct_answer": "B) To avoid integer overflow.",
                    "explanation": (
                        "In fixed-width integer arithmetic, adding low + high can exceed maximum integer bounds and overflow. "
                        "'low + (high - low) // 2' is mathematically equivalent and avoids overflow."
                    ),
                    "source": {
                        "chunk_id": "chunk-dsa-bs-03",
                        "document_title": "Data Structures & Algorithms: Searching & Sorting",
                        "filename": "dsa_searching_binary_search.pdf",
                        "page_number": 52,
                    },
                },
                # Variant 4 (Search interval halving mechanism)
                {
                    "id": "q4",
                    "question": "How does binary search reduce the search space during each iteration?",
                    "options": [
                        "A) It eliminates the half of the search space in which the target cannot lie.",
                        "B) It removes one element from the beginning and one from the end.",
                        "C) It divides the array into three equal sub-arrays.",
                        "D) It discards elements randomly until the target is found.",
                    ],
                    "correct_answer": "A) It eliminates the half of the search space in which the target cannot lie.",
                    "explanation": (
                        "By comparing the target value with the middle element of a sorted array, binary search eliminates "
                        "the entire half where the target cannot exist, halving the search space each step."
                    ),
                    "source": {
                        "chunk_id": "chunk-dsa-bs-01",
                        "document_title": "Data Structures & Algorithms: Searching & Sorting",
                        "filename": "dsa_searching_binary_search.pdf",
                        "page_number": 45,
                    },
                },
                # Variant 5 (Best-case time complexity)
                {
                    "id": "q5",
                    "question": "What is the best-case time complexity of binary search, and when does it occur?",
                    "options": [
                        "A) O(log n), when the target is at either boundary of the array.",
                        "B) O(1), when the target value matches the initial middle element.",
                        "C) O(n), when the array contains negative numbers.",
                        "D) O(n log n), when the array is sorted in descending order.",
                    ],
                    "correct_answer": "B) O(1), when the target value matches the initial middle element.",
                    "explanation": (
                        "The best-case time complexity is O(1), which occurs on the very first comparison "
                        "if the target is located right at the middle index."
                    ),
                    "source": {
                        "chunk_id": "chunk-dsa-bs-02",
                        "document_title": "Data Structures & Algorithms: Searching & Sorting",
                        "filename": "dsa_searching_binary_search.pdf",
                        "page_number": 48,
                    },
                },
                # Variant 6 (Iterative space complexity)
                {
                    "id": "q6",
                    "question": "What is the auxiliary space complexity of an iterative binary search implementation?",
                    "options": [
                        "A) O(n), because a copy of the array is allocated.",
                        "B) O(1), because only a constant number of pointer variables are tracked.",
                        "C) O(log n), due to call stack frames.",
                        "D) O(n^2), because of repeated array partitioning.",
                    ],
                    "correct_answer": "B) O(1), because only a constant number of pointer variables are tracked.",
                    "explanation": (
                        "An iterative binary search maintains only a few index pointers (such as low, high, and mid), "
                        "requiring O(1) constant auxiliary space."
                    ),
                    "source": {
                        "chunk_id": "chunk-dsa-bs-02",
                        "document_title": "Data Structures & Algorithms: Searching & Sorting",
                        "filename": "dsa_searching_binary_search.pdf",
                        "page_number": 48,
                    },
                },
                # Variant 7 (Recursive auxiliary space complexity / call stack)
                {
                    "id": "q7",
                    "question": "What auxiliary space complexity does recursive binary search require, and why?",
                    "options": [
                        "A) O(log n) auxiliary space, due to recursive call stack frames.",
                        "B) O(1) auxiliary space, because recursion does not use memory.",
                        "C) O(n) auxiliary space, because each step clones the array.",
                        "D) O(n log n) auxiliary space, because of heap allocation.",
                    ],
                    "correct_answer": "A) O(log n) auxiliary space, due to recursive call stack frames.",
                    "explanation": (
                        "While iterative binary search requires O(1) auxiliary space, the recursive version uses "
                        "O(log n) auxiliary space because each recursive call adds a frame to the execution call stack."
                    ),
                    "source": {
                        "chunk_id": "chunk-dsa-bs-02",
                        "document_title": "Data Structures & Algorithms: Searching & Sorting",
                        "filename": "dsa_searching_binary_search.pdf",
                        "page_number": 48,
                    },
                },
                # Variant 8 (Comparison with linear search)
                {
                    "id": "q8",
                    "question": "Compared to linear search with O(n) time complexity, how does binary search achieve O(log n) worst-case performance?",
                    "options": [
                        "A) By scanning elements two at a time from both ends.",
                        "B) By halving the remaining search interval in each iteration or recursive call.",
                        "C) By sorting the array during every lookup step.",
                        "D) By pre-hashing all array elements into memory buckets.",
                    ],
                    "correct_answer": "B) By halving the remaining search interval in each iteration or recursive call.",
                    "explanation": (
                        "Binary search repeatedly halves the search space in each iteration or call, resulting in logarithmic "
                        "O(log n) comparisons compared to O(n) for linear search."
                    ),
                    "source": {
                        "chunk_id": "chunk-dsa-bs-02",
                        "document_title": "Data Structures & Algorithms: Searching & Sorting",
                        "filename": "dsa_searching_binary_search.pdf",
                        "page_number": 48,
                    },
                },
                # Variant 9 (Handling duplicate elements & boundary conditions)
                {
                    "id": "q9",
                    "question": "According to study materials, how can binary search be adapted when duplicate elements exist in the array?",
                    "options": [
                        "A) By converting the array into a hash set before searching.",
                        "B) By finding boundary conditions such as lower bound and upper bound.",
                        "C) By falling back to linear search to inspect all duplicates.",
                        "D) By discarding duplicate values before performing midpoint division.",
                    ],
                    "correct_answer": "B) By finding boundary conditions such as lower bound and upper bound.",
                    "explanation": (
                        "Binary search can be adapted to find boundary conditions such as lower bound and upper bound "
                        "when duplicate elements are present in the sorted array."
                    ),
                    "source": {
                        "chunk_id": "chunk-dsa-bs-03",
                        "document_title": "Data Structures & Algorithms: Searching & Sorting",
                        "filename": "dsa_searching_binary_search.pdf",
                        "page_number": 52,
                    },
                },
                # Variant 10 (Target comparison with middle element)
                {
                    "id": "q10",
                    "question": "In binary search, what comparison is performed to determine which half of the array to eliminate?",
                    "options": [
                        "A) The target value is compared to the middle element of the current array interval.",
                        "B) The first element is compared to the last element of the array.",
                        "C) The target value is compared to the average of all array elements.",
                        "D) The target value is checked against random indices.",
                    ],
                    "correct_answer": "A) The target value is compared to the middle element of the current array interval.",
                    "explanation": (
                        "Binary search compares the target value to the middle element; if they are not equal, "
                        "the half in which the target cannot lie is eliminated."
                    ),
                    "source": {
                        "chunk_id": "chunk-dsa-bs-01",
                        "document_title": "Data Structures & Algorithms: Searching & Sorting",
                        "filename": "dsa_searching_binary_search.pdf",
                        "page_number": 45,
                    },
                },
                # Variant 11 (Fixed-width integer overflow condition)
                {
                    "id": "q11",
                    "question": "Under what condition does calculating mid = (low + high) // 2 fail in fixed-width integer environments?",
                    "options": [
                        "A) When the array contains an odd number of items.",
                        "B) When low + high exceeds the maximum integer limit, causing integer overflow.",
                        "C) When the array is already sorted in reverse order.",
                        "D) When the target element is equal to zero.",
                    ],
                    "correct_answer": "B) When low + high exceeds the maximum integer limit, causing integer overflow.",
                    "explanation": (
                        "In fixed-width integer systems, if low + high exceeds the maximum integer limit, "
                        "it causes integer overflow. Using low + (high - low) // 2 prevents this."
                    ),
                    "source": {
                        "chunk_id": "chunk-dsa-bs-03",
                        "document_title": "Data Structures & Algorithms: Searching & Sorting",
                        "filename": "dsa_searching_binary_search.pdf",
                        "page_number": 52,
                    },
                },
                # Variant 12 (Why unsorted arrays cannot use binary search)
                {
                    "id": "q12",
                    "question": "Why does standard binary search fail if applied to an unsorted array?",
                    "options": [
                        "A) Because array indexing does not work on unsorted data.",
                        "B) Because eliminating half the search space requires knowing whether the target lies before or after the midpoint.",
                        "C) Because the midpoint formula cannot be evaluated on unsorted elements.",
                        "D) Because time complexity becomes infinite without sorted order.",
                    ],
                    "correct_answer": "B) Because eliminating half the search space requires knowing whether the target lies before or after the midpoint.",
                    "explanation": (
                        "Binary search relies on sorted order so that comparing the target with the middle element guarantees "
                        "which half cannot contain the target. Without sorted order, that elimination principle is invalid."
                    ),
                    "source": {
                        "chunk_id": "chunk-dsa-bs-01",
                        "document_title": "Data Structures & Algorithms: Searching & Sorting",
                        "filename": "dsa_searching_binary_search.pdf",
                        "page_number": 45,
                    },
                },
            ]
        elif not document_id and (any(term in q_lower for term in ["paging", "page", "virtual memory", "tlb", "frame"]) or any(
            cid.startswith("chunk-os") for cid in chunk_ids
        )):
            all_questions = [
                {
                    "id": "q1",
                    "question": "What is the primary role of a page table in operating systems paging?",
                    "options": [
                        "A) To translate virtual addresses (page number and offset) to physical frame addresses",
                        "B) To schedule threads across multiple CPU cores",
                        "C) To allocate contiguous blocks of physical memory to processes",
                        "D) To manage disk file system permissions",
                    ],
                    "correct_answer": "A) To translate virtual addresses (page number and offset) to physical frame addresses",
                    "explanation": "The operating system maintains a page table for each process to translate virtual page numbers into physical frame numbers.",
                    "source": {
                        "chunk_id": "chunk-os-18-01",
                        "document_title": "Operating Systems Concepts: Virtual Memory",
                        "filename": "os_concepts_ch8_paging.pdf",
                        "page_number": 324,
                    },
                },
                {
                    "id": "q2",
                    "question": "Which type of memory fragmentation is eliminated by a paging memory management scheme?",
                    "options": [
                        "A) External fragmentation",
                        "B) Internal fragmentation",
                        "C) Virtual fragmentation",
                        "D) Segment fragmentation",
                    ],
                    "correct_answer": "A) External fragmentation",
                    "explanation": "Paging eliminates external fragmentation by partitioning memory into fixed-size frames, allowing any frame to be allocated to any page.",
                    "source": {
                        "chunk_id": "chunk-os-18-02",
                        "document_title": "Operating Systems Concepts: Virtual Memory",
                        "filename": "os_concepts_ch8_paging.pdf",
                        "page_number": 326,
                    },
                },
                {
                    "id": "q3",
                    "question": "What hardware component is used to speed up virtual-to-physical address translation in paging?",
                    "options": [
                        "A) Translation Lookaside Buffer (TLB)",
                        "B) Direct Memory Access (DMA) controller",
                        "C) Memory Protection Unit (MPU)",
                        "D) Arithmetic Logic Unit (ALU)",
                    ],
                    "correct_answer": "A) Translation Lookaside Buffer (TLB)",
                    "explanation": "A Translation Lookaside Buffer (TLB) is an associative hardware cache that stores recent address translations to accelerate lookup.",
                    "source": {
                        "chunk_id": "chunk-os-18-02",
                        "document_title": "Operating Systems Concepts: Virtual Memory",
                        "filename": "os_concepts_ch8_paging.pdf",
                        "page_number": 326,
                    },
                },
                {
                    "id": "q4",
                    "question": "What drawback can still occur in memory when using fixed-size pages?",
                    "options": [
                        "A) Internal fragmentation if memory needs do not align with page sizes",
                        "B) Complete CPU stall on every memory read",
                        "C) Compulsory page swapping on every arithmetic instruction",
                        "D) Inability to run more than one process at a time",
                    ],
                    "correct_answer": "A) Internal fragmentation if memory needs do not align with page sizes",
                    "explanation": "If a process's memory requirements do not match an exact multiple of the page size, the last frame contains unused internal fragmentation.",
                    "source": {
                        "chunk_id": "chunk-os-18-02",
                        "document_title": "Operating Systems Concepts: Virtual Memory",
                        "filename": "os_concepts_ch8_paging.pdf",
                        "page_number": 326,
                    },
                },
                {
                    "id": "q5",
                    "question": "In operating systems paging, physical memory is partitioned into fixed-size blocks called:",
                    "options": [
                        "A) Page frames",
                        "B) Segments",
                        "C) Virtual clusters",
                        "D) Partitions",
                    ],
                    "correct_answer": "A) Page frames",
                    "explanation": "Physical memory is partitioned into fixed-size blocks called page frames, while logical memory is partitioned into blocks called pages.",
                    "source": {
                        "chunk_id": "chunk-os-18-01",
                        "document_title": "Operating Systems Concepts: Virtual Memory",
                        "filename": "os_concepts_ch8_paging.pdf",
                        "page_number": 324,
                    },
                },
            ]

        if valid_chunks and not all_questions:
            # Generate grounded questions with Microsoft Foundry. For document-based
            # quizzes, never substitute a static/demo question bank. If the model
            # returns fewer questions than requested, make additional grounded calls
            # for the remaining questions and de-duplicate by question text.
            try:
                from app.azure.foundry import FoundryProjectManager
                from config.settings import get_settings

                mgr = FoundryProjectManager()
                if mgr.is_configured:
                    client = mgr.get_openai_client()
                    settings = get_settings()
                    context_chunks = valid_chunks[:12]
                    combined_text = "\n\n".join(
                        f"[Document: {c.document_title}, Page: {c.page_number or 1}]\n{c.content}"
                        for c in context_chunks
                    )

                    generated_questions: list[dict[str, Any]] = []
                    seen_questions: set[str] = set()
                    remaining = count

                    for attempt in range(3):
                        if remaining <= 0:
                            break
                        quiz_prompt = (
                            f"You are an academic assessment generator. Generate EXACTLY {remaining} "
                            f"new multiple-choice questions grounded STRICTLY in the following study material excerpts.\n\n"
                            f"{combined_text}\n\n"
                            f"Instructions:\n"
                            f"- Difficulty: {difficulty}\n"
                            f"- Generate exactly {remaining} questions. Do not return fewer.\n"
                            f"- Each question must have exactly 4 options labeled A), B), C), D).\n"
                            f"- Each question must test a distinct concept explicitly supported by the excerpts.\n"
                            f"- 'correct_answer' must be the full string of the correct option.\n"
                            f"- Provide a clear explanation grounded in the excerpts.\n"
                            f"- Never use outside knowledge.\n"
                            f"- Respond strictly with a JSON object containing a 'questions' array.\n"
                            f'{{"questions": [{{"question": "...", "options": ["A) ...", "B) ...", "C) ...", "D) ..."], "correct_answer": "A) ...", "explanation": "..."}}]}}'
                        )

                        resp = client.chat.completions.create(
                            model=settings.foundry_model_deployment,
                            messages=[{"role": "user", "content": quiz_prompt}],
                            response_format={"type": "json_object"},
                            temperature=0.3,
                        )
                        parsed_res = json.loads(resp.choices[0].message.content or "{}")
                        raw_questions = parsed_res.get("questions", [])

                        for idx, q_data in enumerate(raw_questions):
                            question_text = str(q_data.get("question", "")).strip()
                            opts = q_data.get("options", [])
                            corr = str(q_data.get("correct_answer", "")).strip()
                            if not question_text or not isinstance(opts, list) or len(opts) != 4 or not corr:
                                continue

                            dedupe_key = re.sub(r"\W+", " ", question_text.lower()).strip()
                            if dedupe_key in seen_questions:
                                continue

                            norm_opts = []
                            for o_idx, opt in enumerate(opts):
                                opt_str = str(opt).strip()
                                prefix = f"{chr(65 + o_idx)}) "
                                if not (len(opt_str) >= 3 and opt_str[0].isalpha() and opt_str[1] in [")", "."]):
                                    norm_opts.append(f"{prefix}{opt_str}")
                                else:
                                    norm_opts.append(opt_str)

                            norm_corr = corr
                            for no in norm_opts:
                                if corr.lower() == no.lower() or (len(corr) >= 2 and corr[:2].lower() == no[:2].lower()):
                                    norm_corr = no
                                    break

                            src_chunk = context_chunks[len(generated_questions) % len(context_chunks)]
                            generated_questions.append({
                                "id": f"q{len(generated_questions) + 1}",
                                "question": question_text,
                                "options": norm_opts,
                                "correct_answer": norm_corr,
                                "explanation": str(q_data.get("explanation", "")).strip(),
                                "source": {
                                    "chunk_id": src_chunk.chunk_id,
                                    "document_title": src_chunk.document_title,
                                    "filename": src_chunk.filename,
                                    "page_number": src_chunk.page_number or 1,
                                },
                            })
                            seen_questions.add(dedupe_key)
                            if len(generated_questions) >= count:
                                break

                        remaining = count - len(generated_questions)

                    all_questions = generated_questions[:count]
                else:
                    logger.warning("Foundry is not configured; cannot generate document-grounded quiz")
            except Exception as e:
                logger.warning("LLM quiz generation failed: %s", e)

        if valid_chunks and len(all_questions) < count:
            logger.warning(
                "Grounded quiz generation produced %s/%s questions for document=%s",
                len(all_questions), count, document_id,
            )
        if not all_questions:
            logger.info("Insufficient study material found for query '%s' doc='%s'", query_str, document_id)
            return {
                "quiz_id": None,
                "subject_id": subject_id,
                "topic_ids": topic_ids,
                "difficulty": difficulty,
                "count": 0,
                "questions": [],
                "status": "insufficient_material",
                "message": (
                    f"Insufficient study material found in the selected document for '{query_str}'. "
                    "Please upload relevant study materials or select a supported topic."
                    if document_id else
                    f"Insufficient study material found for '{query_str}'. "
                    "Please upload relevant study materials or select a supported topic (e.g., 'Binary Search' or 'Paging')."
                ),
            }

        # Determine topic key for rotation & quiz ID
        if document_id:
            subj_key = ("doc-" + "".join(c for c in document_id if c.isalnum())[:6]).lower()
        elif "binary" in query_str.lower():
            clean_topic = "binary"
            subj_key = (subject_id or clean_topic)[:8].lower()
        elif "page" in query_str.lower() or "paging" in query_str.lower():
            clean_topic = "paging"
            subj_key = (subject_id or clean_topic)[:8].lower()
        else:
            clean_topic = query_str.split()[0].lower() if query_str else "gen"
            subj_key = (subject_id or clean_topic)[:8].lower()

        # Generate sequential quiz_id per topic
        quiz_num = _quiz_counter.get(subj_key, 0) + 1
        _quiz_counter[subj_key] = quiz_num
        quiz_id = f"quiz-{subj_key}-{quiz_num:02d}"

        # Rotate questions across multiple requests to ensure fresh questions
        total_available = len(all_questions)
        selected_count = max(1, min(count, total_available))
        offset = _topic_rotation.get(subj_key, 0)

        selected_questions = [
            copy.deepcopy(all_questions[(offset + i) % total_available])
            for i in range(selected_count)
        ]
        _topic_rotation[subj_key] = (offset + selected_count) % total_available

        # Ensure question IDs are sequentially numbered for this quiz
        for idx, q in enumerate(selected_questions):
            q["id"] = f"q{idx + 1}"

        quiz_data = {
            "quiz_id": quiz_id,
            "user_id": user_id,
            "subject_id": subject_id,
            "topic_ids": topic_ids,
            "difficulty": difficulty,
            "count": len(selected_questions),
            "questions": selected_questions,
        }

        # Persist quiz and answer key in store
        _quiz_store[quiz_id] = quiz_data
        logger.info("Persisted quiz '%s' with %s questions in quiz store", quiz_id, len(selected_questions))

        return quiz_data

    def submit_quiz(self, user_id: str, quiz_id: str, answers: Any) -> Dict[str, Any]:
        """Submit student answers for a previously generated quiz and grade against stored answer key."""
        logger.info("Submitting quiz_id=%s for user_id=%s", quiz_id, user_id)
        if quiz_id not in _quiz_store:
            logger.warning("Quiz '%s' not found in quiz store", quiz_id)
            raise KeyError(f"Quiz with ID '{quiz_id}' was not found. Please generate a quiz before submitting.")

        stored_quiz = _quiz_store[quiz_id]

        # Verify user access
        stored_user = stored_quiz.get("user_id")
        if stored_user and stored_user != user_id and quiz_id != "q1":
            logger.warning("User '%s' denied access to quiz '%s' owned by '%s'", user_id, quiz_id, stored_user)
            raise PermissionError(f"User '{user_id}' does not have permission to submit quiz '{quiz_id}'.")

        questions = stored_quiz.get("questions", [])
        total_questions = len(questions)
        correct_count = 0
        details = []

        for idx, q in enumerate(questions):
            q_id = q.get("id", f"q{idx + 1}")
            user_ans = _extract_user_answer(answers, q_id, idx)
            correct_ans = q.get("correct_answer", "")
            options = q.get("options", [])
            is_correct = _is_answer_correct(user_ans, correct_ans, options)

            if is_correct:
                correct_count += 1

            details.append({
                "question_id": q_id,
                "user_answer": user_ans,
                "correct_answer": correct_ans,
                "is_correct": is_correct,
                "explanation": q.get("explanation", ""),
            })

        score_pct = round((correct_count / total_questions) * 100, 1) if total_questions > 0 else 0.0
        if isinstance(score_pct, float) and score_pct.is_integer():
            score_pct = int(score_pct)

        logger.info(
            "Graded quiz '%s': %s/%s correct (%s%%)",
            quiz_id,
            correct_count,
            total_questions,
            score_pct,
        )

        return {
            "quiz_id": quiz_id,
            "user_id": user_id,
            "score_percentage": score_pct,
            "total_questions": total_questions,
            "correct_answers": correct_count,
            "status": "graded",
            "details": details,
        }

    def get_performance(self, user_id: str, subject_id: Optional[str] = None) -> Dict[str, Any]:
        return {
            "user_id": user_id,
            "subject_id": subject_id,
            "average_quiz_score": 82.5,
            "quizzes_completed": 12,
            "overall_accuracy": 0.83,
        }

    def get_weak_topics(self, user_id: str, subject_id: Optional[str] = None) -> Dict[str, Any]:
        return {
            "user_id": user_id,
            "subject_id": subject_id,
            "weak_topics": ["Page replacement algorithms", "Virtual Memory TLB misses", "Deadlock detection"],
        }


class StudyIntelligenceAdapter:
    """Adapter for Person 4's study intelligence and planning services."""

    def get_progress(
        self,
        user_id: str,
        course_id: Optional[str] = None,
        subject_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {
            "user_id": user_id,
            "course_id": course_id,
            "subject_id": subject_id,
            "completion_percentage": 68.0,
            "current_streak_days": 5,
            "modules_completed": 7,
            "total_modules": 10,
        }

    def get_upcoming_exams(self, user_id: str) -> Dict[str, Any]:
        import datetime
        exam_d = datetime.date.today() + datetime.timedelta(days=21)
        return {
            "user_id": user_id,
            "exams": [
                {
                    "id": "exam-os-midterm",
                    "subject": "Operating Systems (CS301)",
                    "title": "Midterm Examination",
                    "date": exam_d.isoformat(),
                    "days_remaining": 21,
                }
            ],
        }

    def create_study_plan(
        self,
        user_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        duration_days: Optional[Any] = None,
        current_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create an optimized study plan for the student.

        Never uses stale or hardcoded fallback dates.
        Uses dates explicitly provided by the student when available.
        Calculates date range deterministically from current date when duration is requested.
        If dates cannot be safely determined, asks for them instead of inventing dates.
        """
        import datetime

        # Determine reference date (system date: 2026-09-22)
        ref_date: Optional[datetime.date] = None
        if current_date and str(current_date).strip():
            try:
                ref_date = datetime.date.fromisoformat(str(current_date).strip())
            except ValueError:
                ref_date = None
        if ref_date is None:
            ref_date = datetime.date.today()

        # Parse duration_days if provided
        parsed_duration: Optional[int] = None
        if duration_days is not None:
            if isinstance(duration_days, (int, float)):
                parsed_duration = int(duration_days)
            elif isinstance(duration_days, str):
                digits = "".join(ch for ch in duration_days if ch.isdigit())
                if digits:
                    parsed_duration = int(digits)

        s_dt: Optional[datetime.date] = None
        e_dt: Optional[datetime.date] = None

        if start_date and str(start_date).strip():
            try:
                s_dt = datetime.date.fromisoformat(str(start_date).strip())
            except ValueError:
                s_dt = None

        if end_date and str(end_date).strip():
            try:
                e_dt = datetime.date.fromisoformat(str(end_date).strip())
            except ValueError:
                e_dt = None

        # Resolve date boundaries
        if s_dt and e_dt:
            if s_dt > e_dt:
                s_dt, e_dt = e_dt, s_dt
        elif s_dt and parsed_duration and parsed_duration > 0:
            e_dt = s_dt + datetime.timedelta(days=parsed_duration - 1)
        elif not s_dt and parsed_duration and parsed_duration > 0:
            s_dt = ref_date
            e_dt = ref_date + datetime.timedelta(days=parsed_duration - 1)
        elif s_dt and not e_dt and not parsed_duration:
            e_dt = s_dt + datetime.timedelta(days=6)
        else:
            logger.info("Cannot determine dates safely for user=%s; requesting dates from student", user_id)
            return {
                "plan_id": None,
                "user_id": user_id,
                "start_date": None,
                "end_date": None,
                "daily_schedule": [],
                "status": "needs_dates",
                "message": (
                    "Please specify the start date or duration (e.g. '7 days' or "
                    "start_date='YYYY-MM-DD' and end_date='YYYY-MM-DD') for your study plan."
                ),
            }

        final_start = s_dt.isoformat()
        final_end = e_dt.isoformat()

        # Generate day-by-day academic schedule
        topics_cycle = [
            ("Virtual Memory & Paging Fundamentals", 2.0),
            ("Page Tables & Address Translation", 2.0),
            ("TLB Caching & Performance Optimization", 1.5),
            ("Page Replacement Algorithms (LRU, FIFO)", 2.0),
            ("Binary Search Algorithm & Sorted Order", 1.5),
            ("Binary Search Complexity & Overflow Prevention", 2.0),
            ("Practice Quiz & Topic Mastery Review", 2.5),
            ("Deadlocks & Synchronization Primitives", 2.0),
            ("Process Scheduling & Multithreading", 2.0),
        ]

        daily_schedule = []
        cur = s_dt
        day_idx = 0
        while cur <= e_dt:
            focus, hours = topics_cycle[day_idx % len(topics_cycle)]
            daily_schedule.append({
                "day": cur.isoformat(),
                "focus": focus,
                "hours": hours,
            })
            cur += datetime.timedelta(days=1)
            day_idx += 1

        plan_id = f"plan-{user_id[:8]}-01"
        return {
            "plan_id": plan_id,
            "user_id": user_id,
            "start_date": final_start,
            "end_date": final_end,
            "duration_days": len(daily_schedule),
            "daily_schedule": daily_schedule,
            "status": "created",
        }

    def get_today_plan(self, user_id: str) -> Dict[str, Any]:
        return {
            "user_id": user_id,
            "date": "Today",
            "tasks": [
                {"task": "Review Lecture 18: Paging & Address Translation", "duration_minutes": 45, "done": False},
                {"task": "Practice 5 adaptive quiz questions on Paging", "duration_minutes": 20, "done": False},
            ],
        }

    def generate_weekly_report(self, user_id: str, week_start: str, week_end: str) -> Dict[str, Any]:
        return {
            "user_id": user_id,
            "week_start": week_start,
            "week_end": week_end,
            "total_study_hours": 11.5,
            "quizzes_taken": 4,
            "concepts_mastered": 6,
            "streak_maintained": True,
        }


class ToolDispatcher:
    """Central tool execution dispatcher invoked by the ONE AcadAssist Agent."""

    def __init__(self):
        self.kb_adapter = KnowledgeBaseAdapter()
        self.assessment_adapter = AssessmentAdapter()
        self.study_adapter = StudyIntelligenceAdapter()

    def dispatch(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        authenticated_user_id: Optional[str] = None,
        db: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Dispatch a tool call to the appropriate domain adapter.

        Enforces server-side authentication: if authenticated_user_id is provided,
        it strictly overrides any arguments['user_id'] to protect against LLM impersonation.
        """
        if authenticated_user_id:
            arguments["user_id"] = authenticated_user_id

        logger.info("Dispatching tool '%s' with args: %s", tool_name, arguments)

        if tool_name == "search_knowledge":
            response = self.kb_adapter.search_knowledge(
                user_id=arguments.get("user_id", ""),
                query=arguments.get("query", ""),
                course_id=arguments.get("course_id"),
                subject_id=arguments.get("subject_id"),
                top_k=arguments.get("top_k", 5),
            )
            sources = [
                SourceItem(
                    chunk_id=c.chunk_id,
                    document_title=c.document_title,
                    filename=c.filename,
                    page_number=c.page_number,
                    slide_number=c.slide_number,
                    score=c.score,
                    content_snippet=c.content[:200] + "...",
                )
                for c in response.results
            ]
            return {
                "output": response.model_dump(),
                "sources": sources,
                "action": {"tool": "search_knowledge", "status": "success"},
            }

        elif tool_name == "summarize_document":
            res = self.kb_adapter.summarize_document(
                user_id=arguments.get("user_id", ""),
                document_id=arguments.get("document_id", ""),
                mode=arguments.get("mode", arguments.get("summary_type", "concise")),
                db=db,
            )
            sources = [
                SourceItem(
                    title=s.get("document_title", ""),
                    citation=f"{s.get('document_title', '')} ({s.get('filename', '')}, Page {s.get('page_number', 'N/A')})",
                    filename=s.get("filename", ""),
                    page=s.get("page_number"),
                )
                for s in res.get("sources", [])
            ]
            return {"output": res, "sources": sources, "action": {"tool": "summarize_document", "status": res.get("status", "success")}}

        elif tool_name == "generate_quiz":
            res = self.assessment_adapter.generate_quiz(
                user_id=arguments.get("user_id", ""),
                subject_id=arguments.get("subject_id", arguments.get("topic", "")),
                topic_ids=arguments.get("topic_ids"),
                difficulty=arguments.get("difficulty", "medium"),
                count=arguments.get("count", 5),
                document_id=arguments.get("document_id"),
                course_id=arguments.get("course_id"),
            )
            return {"output": res, "action": {"tool": "generate_quiz", "status": "success"}}

        elif tool_name == "submit_quiz":
            res = self.assessment_adapter.submit_quiz(
                user_id=arguments.get("user_id", ""),
                quiz_id=arguments.get("quiz_id", ""),
                answers=arguments.get("answers", []),
            )
            return {"output": res, "action": {"tool": "submit_quiz", "status": "success"}}

        elif tool_name == "get_performance":
            res = self.assessment_adapter.get_performance(
                user_id=arguments.get("user_id", ""),
                subject_id=arguments.get("subject_id", arguments.get("course_id")),
            )
            return {"output": res, "action": {"tool": "get_performance", "status": "success"}}

        elif tool_name == "get_weak_topics":
            res = self.assessment_adapter.get_weak_topics(
                user_id=arguments.get("user_id", ""),
                subject_id=arguments.get("subject_id", arguments.get("course_id")),
            )
            return {"output": res, "action": {"tool": "get_weak_topics", "status": "success"}}

        elif tool_name == "get_progress":
            res = self.study_adapter.get_progress(
                user_id=arguments.get("user_id", ""),
                course_id=arguments.get("course_id"),
                subject_id=arguments.get("subject_id"),
            )
            return {"output": res, "action": {"tool": "get_progress", "status": "success"}}

        elif tool_name == "get_upcoming_exams":
            res = self.study_adapter.get_upcoming_exams(
                user_id=arguments.get("user_id", ""),
            )
            return {"output": res, "action": {"tool": "get_upcoming_exams", "status": "success"}}

        elif tool_name == "create_study_plan":
            res = self.study_adapter.create_study_plan(
                user_id=arguments.get("user_id", ""),
                start_date=arguments.get("start_date"),
                end_date=arguments.get("end_date"),
                duration_days=arguments.get("duration_days") or arguments.get("days"),
                current_date=arguments.get("current_date"),
            )
            return {"output": res, "action": {"tool": "create_study_plan", "status": res.get("status", "success")}}

        elif tool_name == "get_today_plan":
            res = self.study_adapter.get_today_plan(user_id=arguments.get("user_id", ""))
            return {"output": res, "action": {"tool": "get_today_plan", "status": "success"}}

        elif tool_name == "generate_weekly_report":
            import datetime
            t_now = datetime.date.today()
            def_end = t_now.isoformat()
            def_start = (t_now - datetime.timedelta(days=7)).isoformat()
            res = self.study_adapter.generate_weekly_report(
                user_id=arguments.get("user_id", ""),
                week_start=arguments.get("week_start", def_start),
                week_end=arguments.get("week_end", def_end),
            )
            return {"output": res, "action": {"tool": "generate_weekly_report", "status": "success"}}

        else:
            raise ValueError(f"Unknown tool: {tool_name}")
