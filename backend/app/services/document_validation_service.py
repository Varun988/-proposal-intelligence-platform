from pathlib import Path

from app.core.exceptions import DocumentValidationError
from app.schemas.document_upload import (
    DocumentMediaType,
)

ALLOWED_DOCUMENT_EXTENSIONS = {
    ".pdf": DocumentMediaType.PDF,
    ".txt": DocumentMediaType.TEXT,
}

MAXIMUM_DOCUMENT_SIZE_BYTES = 20 * 1024 * 1024


class DocumentValidationService:
    """Validate uploaded filenames, media types, and binary content."""

    def __init__(
        self,
        maximum_file_size_bytes: int = (MAXIMUM_DOCUMENT_SIZE_BYTES),
    ) -> None:
        if maximum_file_size_bytes < 1:
            raise ValueError("Maximum document size must be at least one byte.")

        self._maximum_file_size_bytes = maximum_file_size_bytes

    def validate(
        self,
        original_file_name: str,
        declared_media_type: str | None,
        content: bytes,
    ) -> DocumentMediaType:
        """Validate one uploaded document."""

        safe_name = Path(original_file_name).name.strip()

        if not safe_name:
            raise DocumentValidationError("Document filename is required.")

        if not content:
            raise DocumentValidationError("Uploaded document cannot be empty.")

        if len(content) > self._maximum_file_size_bytes:
            raise DocumentValidationError("Uploaded document exceeds the maximum permitted size.")

        extension = Path(safe_name).suffix.casefold()

        expected_media_type = ALLOWED_DOCUMENT_EXTENSIONS.get(
            extension,
        )

        if expected_media_type is None:
            raise DocumentValidationError("Unsupported document extension.")

        if declared_media_type and declared_media_type != expected_media_type.value:
            raise DocumentValidationError(
                "Declared document media type does not match the filename extension."
            )

        self._validate_content_signature(
            media_type=expected_media_type,
            content=content,
        )

        return expected_media_type

    @staticmethod
    def _validate_content_signature(
        media_type: DocumentMediaType,
        content: bytes,
    ) -> None:
        """Perform basic file-signature validation."""

        if media_type is DocumentMediaType.PDF and not content.startswith(b"%PDF-"):
            raise DocumentValidationError("Uploaded PDF has an invalid file signature.")

        if media_type is DocumentMediaType.TEXT:
            try:
                content.decode("utf-8")
            except UnicodeDecodeError as error:
                raise DocumentValidationError("Uploaded text document must use UTF-8.") from error
