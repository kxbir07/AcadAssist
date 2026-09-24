"""PDF parser implementation preserving page structure."""

import io
from pathlib import Path
from pypdf import PdfReader

from app.services.parsers.base import BaseParser, ExtractedDocument, ExtractedUnit


class PDFParser(BaseParser):
    """Parser for PDF documents extracting text per page."""

    def parse(self, file_bytes: bytes, filename: str) -> ExtractedDocument:
        stream = io.BytesIO(file_bytes)
        reader = PdfReader(stream)

        doc_title = Path(filename).stem
        if reader.metadata and reader.metadata.title:
            doc_title = str(reader.metadata.title).strip() or doc_title

        units: list[ExtractedUnit] = []

        for idx, page in enumerate(reader.pages):
            page_num = idx + 1
            text = page.extract_text() or ""
            text = text.strip()
            if not text:
                continue

            # Detect potential section or title from first non-empty line
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            first_line = lines[0] if lines else None
            section_title = first_line[:120] if first_line and len(first_line) < 120 else None

            units.append(
                ExtractedUnit(
                    content=text,
                    page_number=page_num,
                    slide_number=None,
                    title=doc_title,
                    section_title=section_title,
                    content_type="page",
                )
            )

        return ExtractedDocument(
            title=doc_title,
            file_type="pdf",
            units=units,
            raw_metadata={"page_count": len(reader.pages)},
        )
