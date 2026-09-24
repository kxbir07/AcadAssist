"""Text normalization preserving academic structure and boundaries."""

import re
import unicodedata
from app.services.parsers.base import ExtractedUnit


class TextNormalizer:
    """Normalizes raw extracted text while preserving academic document structure."""

    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalize a text string removing artifacts, whitespace bloat, and broken words."""
        if not text:
            return ""

        # Normalize unicode (decompose and recompose standard characters)
        text = unicodedata.normalize("NFKC", text)

        # Remove non-printable control characters (keep standard newlines and tabs)
        text = "".join(ch for ch in text if ch in ("\n", "\t", "\r") or unicodedata.category(ch)[0] != "C")

        # Normalize line endings to \n
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Fix hyphenated word breaks at end of line (e.g. 'schedul-\ning' -> 'scheduling')
        text = re.sub(r"(\w+)-\n(\w+)", r"\1\2", text)

        # Replace repeated horizontal spaces/tabs on each line with a single space
        lines = text.split("\n")
        cleaned_lines = []
        for line in lines:
            # Replace multiple whitespace with single space on each line
            clean_line = re.sub(r"[ \t]+", " ", line).strip()
            cleaned_lines.append(clean_line)

        # Join lines back
        normalized = "\n".join(cleaned_lines)

        # Collapse more than 2 consecutive blank lines into double newline (preserves paragraphs)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)

        return normalized.strip()

    @classmethod
    def normalize_unit(cls, unit: ExtractedUnit) -> ExtractedUnit | None:
        """Normalize an ExtractedUnit, returning None if the resulting content is empty."""
        cleaned_content = cls.normalize_text(unit.content)
        if not cleaned_content:
            return None

        cleaned_title = cls.normalize_text(unit.title) if unit.title else None
        cleaned_section = cls.normalize_text(unit.section_title) if unit.section_title else None

        return ExtractedUnit(
            content=cleaned_content,
            page_number=unit.page_number,
            slide_number=unit.slide_number,
            title=cleaned_title or unit.title,
            section_title=cleaned_section or unit.section_title,
            content_type=unit.content_type,
        )

    @classmethod
    def normalize_units(cls, units: list[ExtractedUnit]) -> list[ExtractedUnit]:
        """Normalize a collection of ExtractedUnits, omitting empty units."""
        result = []
        for u in units:
            norm = cls.normalize_unit(u)
            if norm:
                result.append(norm)
        return result
