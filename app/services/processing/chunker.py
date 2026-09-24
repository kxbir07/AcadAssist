"""Configurable academic document chunker preserving provenance and metadata."""

import uuid
from datetime import datetime, timezone
from app.config import settings
from app.models.document import Chunk
from app.services.parsers.base import ExtractedUnit


class AcademicChunker:
    """Chunks normalized extracted document units while preserving metadata and page boundaries."""

    def __init__(self, chunk_size: int | None = None, chunk_overlap: int | None = None):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
        if self.chunk_overlap >= self.chunk_size:
            self.chunk_overlap = max(0, self.chunk_size // 4)

    def _split_text(self, text: str) -> list[str]:
        """Split text into overlapping segments respecting paragraph or sentence boundaries."""
        if len(text) <= self.chunk_size:
            return [text]

        chunks: list[str] = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = start + self.chunk_size
            if end >= text_len:
                chunk = text[start:].strip()
                if chunk:
                    chunks.append(chunk)
                break

            # Find boundary near end (paragraph, sentence, or whitespace)
            split_idx = -1
            search_window = text[max(start, end - 120):end]

            # Try paragraph break
            p_break = search_window.rfind("\n\n")
            if p_break != -1:
                split_idx = max(start, end - 120) + p_break + 2
            else:
                # Try sentence end (. ! ?)
                for sep in [". ", "? ", "! ", "\n"]:
                    s_break = search_window.rfind(sep)
                    if s_break != -1:
                        split_idx = max(start, end - 120) + s_break + len(sep)
                        break

            # Fall back to space boundary
            if split_idx == -1:
                space_break = search_window.rfind(" ")
                if space_break != -1:
                    split_idx = max(start, end - 120) + space_break + 1
                else:
                    split_idx = end

            chunk = text[start:split_idx].strip()
            if chunk:
                chunks.append(chunk)

            # Advance start with overlap
            new_start = split_idx - self.chunk_overlap
            if new_start <= start:
                new_start = split_idx
            start = new_start

        return chunks

    def chunk_document(
        self,
        units: list[ExtractedUnit],
        document_id: str,
        user_id: str,
        course_id: str,
        subject_id: str,
        filename: str,
        document_title: str,
    ) -> list[Chunk]:
        """Generate structured Chunk records from extracted document units."""
        raw_chunks: list[dict] = []

        for unit in units:
            content = unit.content.strip()
            if not content:
                continue

            text_segments = self._split_text(content)
            for segment in text_segments:
                seg_clean = segment.strip()
                if not seg_clean:
                    continue
                raw_chunks.append({
                    "content": seg_clean,
                    "page_number": unit.page_number,
                    "slide_number": unit.slide_number,
                    "title": unit.title or document_title,
                    "section_title": unit.section_title,
                    "content_type": unit.content_type,
                })

        total = len(raw_chunks)
        now = datetime.now(timezone.utc)
        result_chunks: list[Chunk] = []

        for idx, item in enumerate(raw_chunks):
            chunk = Chunk(
                chunk_id=str(uuid.uuid4()),
                document_id=document_id,
                user_id=user_id,
                course_id=course_id,
                subject_id=subject_id,
                content=item["content"],
                title=item["title"],
                section_title=item["section_title"],
                document_title=document_title,
                filename=filename,
                page_number=item["page_number"],
                slide_number=item["slide_number"],
                chunk_index=idx,
                total_chunks=total,
                content_type=item["content_type"],
                created_at=now,
                content_vector=None,
            )
            result_chunks.append(chunk)

        return result_chunks
