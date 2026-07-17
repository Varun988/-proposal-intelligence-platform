from abc import ABC, abstractmethod
from pathlib import Path

from app.schemas.document import ExtractedDocument


class BaseDocumentParser(ABC):
    """Contract implemented by document parsers."""

    @property
    @abstractmethod
    def supported_extensions(self) -> tuple[str, ...]:
        """Return the file extensions supported by the parser."""

    @abstractmethod
    def can_parse(self, file_path: Path) -> bool:
        """Return whether this parser supports the supplied file."""

    @abstractmethod
    def parse(self, file_path: Path) -> ExtractedDocument:
        """Extract structured content from a document."""
