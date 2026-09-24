"""Plain text (TXT) parser integrating with the common document pipeline."""

from pathlib import Path
from app.services.parsers.base import BaseParser, ExtractedDocument, ExtractedUnit


class TXTParser(BaseParser):
    """Parser for plain text files splitting by logical paragraphs/sections."""

    def parse(self, file_bytes: bytes, filename: str) -> ExtractedDocument:
        doc_title = Path(filename).stem
        try:
            text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = file_bytes.decode("latin-1", errors="ignore")

        # Split into blocks based on blank lines
        blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
        units: list[ExtractedUnit] = []

        for idx, block in enumerate(blocks):
            # Detect potential heading if first line is short
            lines = [l.strip() for l in block.splitlines() if l.strip()]
            first_line = lines[0] if lines else None
            section_title = first_line[:100] if first_line and len(first_line) < 80 else None

            units.append(
                ExtractedUnit(
                    content=block,
                    page_number=idx + 1,
                    slide_number=None,
                    title=doc_title,
                    section_title=section_title,
                    content_type="paragraph",
                )
            )

        if not units and text.strip():
            units.append(
                ExtractedUnit(
                    content=text.strip(),
                    page_number=1,
                    slide_number=None,
                    title=doc_title,
                    section_title="Full Text",
                    content_type="text",
                )
            )

        return ExtractedDocument(
            title=doc_title,
            file_type="txt",
            units=units,
            raw_metadata={"character_count": len(text)},
        )
