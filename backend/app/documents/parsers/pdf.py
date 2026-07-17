from pathlib import Path
from uuid import uuid4

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.core.exceptions import (
    DocumentExtractionError,
    DocumentNotFoundError,
    EncryptedDocumentError,
    UnsupportedDocumentError,
)
from app.documents.base import BaseDocumentParser
from app.schemas.document import (
    DocumentMetadata,
    DocumentPage,
    DocumentType,
    ExtractedDocument,
)
from app.utils.checksum import calculate_sha256


class PypdfPDFParser(BaseDocumentParser):
    """Extract page-aware text and metadata from PDF documents."""

    @property
    def supported_extensions(self) -> tuple[str, ...]:
        """Return supported PDF extensions."""

        return (".pdf",)

    def can_parse(self, file_path: Path) -> bool:
        """Return whether the file has a supported PDF extension."""

        return file_path.suffix.lower() in self.supported_extensions

    def parse(self, file_path: Path) -> ExtractedDocument:
        """Extract pages and metadata from a PDF file."""

        normalized_path = file_path.expanduser().resolve()

        self._validate_file(normalized_path)

        try:
            reader = PdfReader(
                normalized_path,
                strict=False,
            )

            self._validate_encryption(reader)

            pages = [
                self._extract_page(
                    page=page,
                    page_number=index + 1,
                )
                for index, page in enumerate(reader.pages)
            ]

            if not pages:
                raise DocumentExtractionError("The PDF document contains no pages.")

            return ExtractedDocument(
                document_id=str(uuid4()),
                file_name=normalized_path.name,
                file_path=normalized_path,
                document_type=DocumentType.PDF,
                mime_type="application/pdf",
                checksum_sha256=calculate_sha256(
                    normalized_path,
                ),
                page_count=len(pages),
                pages=pages,
                metadata=self._extract_metadata(reader),
            )
        except (
            DocumentExtractionError,
            EncryptedDocumentError,
        ):
            raise
        except PdfReadError as error:
            raise DocumentExtractionError(
                f"Unable to read PDF document: {normalized_path.name}"
            ) from error
        except Exception as error:
            raise DocumentExtractionError(
                f"PDF extraction failed: {normalized_path.name}"
            ) from error

    def _validate_file(self, file_path: Path) -> None:
        """Validate that the source file exists and is supported."""

        if not file_path.exists():
            raise DocumentNotFoundError(f"Document not found: {file_path.name}")

        if not file_path.is_file():
            raise DocumentNotFoundError(f"Document path is not a file: {file_path.name}")

        if not self.can_parse(file_path):
            raise UnsupportedDocumentError(
                f"Unsupported document type: {file_path.suffix or 'unknown'}"
            )

    @staticmethod
    def _validate_encryption(reader: PdfReader) -> None:
        """Reject password-protected PDFs that cannot be opened."""

        if not reader.is_encrypted:
            return

        try:
            decrypt_result = reader.decrypt("")
        except Exception as error:
            raise EncryptedDocumentError(
                "The PDF document is encrypted and cannot be opened."
            ) from error

        if decrypt_result == 0:
            raise EncryptedDocumentError("The PDF document requires a password.")

    @staticmethod
    def _extract_page(
        page: object,
        page_number: int,
    ) -> DocumentPage:
        """Extract text and dimensions from one PDF page."""

        extracted_text = page.extract_text() or ""

        media_box = page.mediabox

        return DocumentPage(
            page_number=page_number,
            text=extracted_text.strip(),
            width=float(media_box.width),
            height=float(media_box.height),
        )

    @staticmethod
    def _extract_metadata(
        reader: PdfReader,
    ) -> DocumentMetadata:
        """Extract standard PDF document metadata."""

        metadata = reader.metadata

        if metadata is None:
            return DocumentMetadata()

        return DocumentMetadata(
            title=metadata.title,
            author=metadata.author,
            subject=metadata.subject,
            creator=metadata.creator,
            producer=metadata.producer,
        )
