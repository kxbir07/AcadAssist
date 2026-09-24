"""Document parsers package."""

from app.services.parsers.base import BaseParser, ExtractedDocument, ExtractedUnit
from app.services.parsers.docx import DOCXParser
from app.services.parsers.factory import ParserFactory
from app.services.parsers.pdf import PDFParser
from app.services.parsers.pptx import PPTXParser
from app.services.parsers.txt import TXTParser

__all__ = [
    "BaseParser",
    "ExtractedDocument",
    "ExtractedUnit",
    "PDFParser",
    "PPTXParser",
    "DOCXParser",
    "TXTParser",
    "ParserFactory",
]
