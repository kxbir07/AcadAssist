"""Common parser interfaces and standardized data representations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ExtractedUnit:
    """Standardized extracted unit of document content (e.g. page, slide, section)."""

    content: str
    page_number: int | None = None
    slide_number: int | None = None
    title: str | None = None
    section_title: str | None = None
    content_type: str = "text"  # "page", "slide", "paragraph", "text"


@dataclass
class ExtractedDocument:
    """Complete extracted representation of a parsed document."""

    title: str
    file_type: str
    units: list[ExtractedUnit] = field(default_factory=list)
    raw_metadata: dict = field(default_factory=dict)


class BaseParser(ABC):
    """Abstract parser base class."""

    @abstractmethod
    def parse(self, file_bytes: bytes, filename: str) -> ExtractedDocument:
        """Parse raw file bytes into a standardized ExtractedDocument."""
        pass
