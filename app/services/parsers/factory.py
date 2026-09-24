"""Parser factory for resolving document format parsers."""

from pathlib import Path
from app.services.parsers.base import BaseParser
from app.services.parsers.docx import DOCXParser
from app.services.parsers.pdf import PDFParser
from app.services.parsers.pptx import PPTXParser
from app.services.parsers.txt import TXTParser


class ParserFactory:
    """Factory resolving appropriate parser for supported file formats."""

    @staticmethod
    def get_parser(filename: str) -> BaseParser:
        ext = Path(filename).suffix.lower()

        if ext == ".pdf":
            return PDFParser()
        elif ext in (".ppt", ".pptx"):
            return PPTXParser()
        elif ext == ".docx":
            return DOCXParser()
        elif ext == ".txt":
            return TXTParser()
        else:
            raise ValueError(
                f"Unsupported document format: '{ext}'. Supported formats: .pdf, .ppt, .pptx, .docx, .txt"
            )
