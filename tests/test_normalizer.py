"""Unit tests for text normalizer."""

from app.services.parsers.base import ExtractedUnit
from app.services.processing.normalizer import TextNormalizer


def test_normalize_whitespace_and_blank_lines():
    raw_text = "Operating   Systems   Overview\n\n\n\n\nProcess    Management\n   is vital."
    normalized = TextNormalizer.normalize_text(raw_text)

    # Excessive blank lines collapsed to double newline
    assert "\n\n\n" not in normalized
    assert "Operating Systems Overview\n\nProcess Management\nis vital." == normalized


def test_normalize_hyphenated_line_breaks():
    raw_text = "Deadlock preven-\ntion techniques in multi-\nprocessing environments."
    normalized = TextNormalizer.normalize_text(raw_text)

    assert "prevention" in normalized
    assert "multiprocessing" in normalized


def test_normalize_control_characters():
    raw_text = "Header text\x00\x07 with unprintable\x0b characters."
    normalized = TextNormalizer.normalize_text(raw_text)

    assert "\x00" not in normalized
    assert "\x07" not in normalized
    assert "Header text with unprintable characters." == normalized


def test_normalize_extracted_unit():
    unit = ExtractedUnit(
        content="   Memory   Management   \n\n\n\nVirtual   Memory.  ",
        page_number=3,
        title="  OS  Unit  2  ",
        section_title="  Section  A  ",
        content_type="page",
    )

    norm_unit = TextNormalizer.normalize_unit(unit)
    assert norm_unit is not None
    assert norm_unit.content == "Memory Management\n\nVirtual Memory."
    assert norm_unit.title == "OS Unit 2"
    assert norm_unit.section_title == "Section A"
    assert norm_unit.page_number == 3


def test_normalize_empty_unit_returns_none():
    unit = ExtractedUnit(content="   \n\n   ", page_number=1)
    assert TextNormalizer.normalize_unit(unit) is None
