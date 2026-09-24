"""PowerPoint (PPT/PPTX) parser preserving slide numbers and structure."""

import io
import re
from pathlib import Path
from pptx import Presentation

from app.services.parsers.base import BaseParser, ExtractedDocument, ExtractedUnit


class PPTXParser(BaseParser):
    """Parser for PowerPoint presentations extracting text per slide."""

    def parse(self, file_bytes: bytes, filename: str) -> ExtractedDocument:
        doc_title = Path(filename).stem
        stream = io.BytesIO(file_bytes)

        units: list[ExtractedUnit] = []
        file_ext = Path(filename).suffix.lower()

        try:
            prs = Presentation(stream)
            for idx, slide in enumerate(prs.slides):
                slide_num = idx + 1
                slide_title = None
                slide_texts: list[str] = []

                # Extract title shape if available
                if slide.shapes.title and slide.shapes.title.has_text_frame:
                    title_text = slide.shapes.title.text_frame.text.strip()
                    if title_text:
                        slide_title = title_text

                # Extract text from all shapes
                for shape in slide.shapes:
                    if shape.has_text_frame:
                        for paragraph in shape.text_frame.paragraphs:
                            p_text = paragraph.text.strip()
                            if p_text and p_text != slide_title:
                                slide_texts.append(p_text)
                    elif shape.has_table:
                        for row in shape.table.rows:
                            row_texts = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                            if row_texts:
                                slide_texts.append(" | ".join(row_texts))

                # Extract notes if available
                if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
                    notes_text = slide.notes_slide.notes_text_frame.text.strip()
                    if notes_text:
                        slide_texts.append(f"[Notes: {notes_text}]")

                combined_content = "\n".join(slide_texts).strip()
                if slide_title:
                    full_content = f"{slide_title}\n{combined_content}" if combined_content else slide_title
                else:
                    full_content = combined_content

                if full_content.strip():
                    units.append(
                        ExtractedUnit(
                            content=full_content,
                            page_number=None,
                            slide_number=slide_num,
                            title=doc_title,
                            section_title=slide_title,
                            content_type="slide",
                        )
                    )

            return ExtractedDocument(
                title=doc_title,
                file_type=file_ext.replace(".", ""),
                units=units,
                raw_metadata={"slide_count": len(prs.slides)},
            )

        except Exception:
            # Fallback for legacy binary .ppt files or corrupted XML packaging
            return self._parse_legacy_ppt(file_bytes, filename)

    def _parse_legacy_ppt(self, file_bytes: bytes, filename: str) -> ExtractedDocument:
        """Heuristic parser for legacy binary PowerPoint (.ppt) files."""
        doc_title = Path(filename).stem
        # Extract unicode or ascii printable strings
        text_matches = re.findall(rb"[\x20-\x7E]{4,}", file_bytes)
        decoded = [m.decode("latin1", errors="ignore").strip() for m in text_matches]
        # Filter out common binary artifacts
        clean_lines = [line for line in decoded if len(line) > 3 and not line.startswith("Microsoft")]

        content = "\n".join(clean_lines).strip()
        units = []
        if content:
            units.append(
                ExtractedUnit(
                    content=content,
                    page_number=None,
                    slide_number=1,
                    title=doc_title,
                    section_title="Presentation Content",
                    content_type="slide",
                )
            )

        return ExtractedDocument(
            title=doc_title,
            file_type="ppt",
            units=units,
            raw_metadata={"parsed_as": "legacy_ppt_fallback"},
        )
