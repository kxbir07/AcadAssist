"""Unit tests for academic document chunking."""

from app.services.parsers.base import ExtractedUnit
from app.services.processing.chunker import AcademicChunker


def test_chunker_short_document():
    chunker = AcademicChunker(chunk_size=500, chunk_overlap=100)
    units = [
        ExtractedUnit(
            content="Short introduction to operating systems concepts.",
            page_number=1,
            title="OS Intro",
            section_title="Overview",
            content_type="page",
        )
    ]

    chunks = chunker.chunk_document(
        units=units,
        document_id="doc-123",
        user_id="user-456",
        course_id="course-789",
        subject_id="subj-101",
        filename="intro.pdf",
        document_title="OS Intro",
    )

    assert len(chunks) == 1
    c = chunks[0]
    assert c.chunk_index == 0
    assert c.total_chunks == 1
    assert c.page_number == 1
    assert c.user_id == "user-456"
    assert c.course_id == "course-789"
    assert c.subject_id == "subj-101"
    assert c.document_id == "doc-123"
    assert c.filename == "intro.pdf"
    assert "Short introduction" in c.content


def test_chunker_long_document_and_overlap():
    chunker = AcademicChunker(chunk_size=100, chunk_overlap=30)
    long_text = (
        "Process synchronization is the coordination of execution of multiple processes. "
        "Critical section problem requires mutual exclusion, progress, and bounded waiting. "
        "Semaphores and mutex locks are common synchronization tools used in operating systems."
    )
    units = [
        ExtractedUnit(
            content=long_text,
            page_number=5,
            slide_number=None,
            title="Sync",
            section_title="Critical Section",
            content_type="page",
        )
    ]

    chunks = chunker.chunk_document(
        units=units,
        document_id="doc-sync-1",
        user_id="user-1",
        course_id="c-1",
        subject_id="s-1",
        filename="sync.pdf",
        document_title="Synchronization",
    )

    assert len(chunks) > 1
    assert all(c.total_chunks == len(chunks) for c in chunks)
    for i, c in enumerate(chunks):
        assert c.chunk_index == i
        assert c.page_number == 5
        assert c.user_id == "user-1"
        assert len(c.content.strip()) > 0


def test_chunker_multi_page_preserves_page_numbers():
    chunker = AcademicChunker(chunk_size=200, chunk_overlap=50)
    units = [
        ExtractedUnit(content="Page one content regarding scheduling algorithms.", page_number=1),
        ExtractedUnit(content="Page two content regarding memory paging and segmentation.", page_number=2),
        ExtractedUnit(content="Page three content regarding disk storage management.", page_number=3),
    ]

    chunks = chunker.chunk_document(
        units=units,
        document_id="doc-pages",
        user_id="user-1",
        course_id="c-1",
        subject_id="s-1",
        filename="os.pdf",
        document_title="OS",
    )

    assert len(chunks) == 3
    assert chunks[0].page_number == 1
    assert chunks[1].page_number == 2
    assert chunks[2].page_number == 3
    assert all(c.total_chunks == 3 for c in chunks)


def test_chunker_multi_slide_preserves_slide_numbers():
    chunker = AcademicChunker(chunk_size=200, chunk_overlap=50)
    units = [
        ExtractedUnit(content="Slide one: TCP 3-way handshake.", slide_number=1, content_type="slide"),
        ExtractedUnit(content="Slide two: UDP connectionless datagrams.", slide_number=2, content_type="slide"),
    ]

    chunks = chunker.chunk_document(
        units=units,
        document_id="doc-slides",
        user_id="user-1",
        course_id="c-1",
        subject_id="s-1",
        filename="net.pptx",
        document_title="Networks",
    )

    assert len(chunks) == 2
    assert chunks[0].slide_number == 1
    assert chunks[1].slide_number == 2
