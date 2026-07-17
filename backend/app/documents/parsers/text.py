from pathlib import Path
from uuid import uuid4

from app.core.exceptions import (
    DocumentExtractionError,
    DocumentNotFoundError,
    UnsupportedDocumentError,
)
from app.documents.base import BaseDocumentParser
from app.schemas.document import (
    DocumentPage,
    DocumentType,
    ExtractedDocument,
)
from app.utils.checksum import calculate_sha256


class Utf8TextDocumentParser(BaseDocumentParser):
    """Extract UTF-8 text files as single-page documents."""

    @property
    def supported_extensions(self) -> tuple[str, ...]:
        """Return supported text-file extensions."""

        return (".txt",)

    def can_parse(self, file_path: Path) -> bool:
        """Return whether the file has a supported extension."""

        return file_path.suffix.lower() in self.supported_extensions

    def parse(self, file_path: Path) -> ExtractedDocument:
        """Extract one UTF-8 text document."""

        normalized_path = file_path.expanduser().resolve()
        self._validate_file(normalized_path)

        try:
            text = normalized_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as error:
            raise DocumentExtractionError(
                f"Text document must use UTF-8: {normalized_path.name}"
            ) from error
        except OSError as error:
            raise DocumentExtractionError(
                f"Unable to read text document: {normalized_path.name}"
            ) from error

        return ExtractedDocument(
            document_id=str(uuid4()),
            file_name=normalized_path.name,
            file_path=normalized_path,
            document_type=DocumentType.TEXT,
            mime_type="text/plain",
            checksum_sha256=calculate_sha256(normalized_path),
            page_count=1,
            pages=[
                DocumentPage(
                    page_number=1,
                    text=text.strip(),
                )
            ],
        )

    def _validate_file(self, file_path: Path) -> None:
        """Validate the source path and extension."""

        if not file_path.exists():
            raise DocumentNotFoundError(f"Document not found: {file_path.name}")
        if not file_path.is_file():
            raise DocumentNotFoundError(f"Document path is not a file: {file_path.name}")
        if not self.can_parse(file_path):
            raise UnsupportedDocumentError(
                f"Unsupported document type: {file_path.suffix or 'unknown'}"
            )
