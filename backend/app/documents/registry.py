from pathlib import Path

from app.core.exceptions import (
    DocumentParserRegistrationError,
    UnsupportedDocumentError,
)
from app.documents.base import BaseDocumentParser


class DocumentParserRegistry:
    """Registry that selects document parsers by file extension."""

    def __init__(self) -> None:
        self._parsers: dict[str, BaseDocumentParser] = {}

    def register(
        self,
        parser: BaseDocumentParser,
    ) -> None:
        """Register a parser for each supported file extension."""

        supported_extensions = parser.supported_extensions

        if not supported_extensions:
            raise DocumentParserRegistrationError(
                "Document parser must support at least one extension."
            )

        for extension in supported_extensions:
            normalized_extension = self._normalize_extension(
                extension,
            )

            if normalized_extension in self._parsers:
                registered_parser = self._parsers[normalized_extension]

                raise DocumentParserRegistrationError(
                    "A document parser is already registered for "
                    f"'{normalized_extension}': "
                    f"{registered_parser.__class__.__name__}."
                )

            self._parsers[normalized_extension] = parser

    def get_parser(
        self,
        file_path: Path,
    ) -> BaseDocumentParser:
        """Return the parser registered for the supplied file."""

        extension = self._normalize_extension(
            file_path.suffix,
        )
        parser = self._parsers.get(extension)

        if parser is None:
            raise UnsupportedDocumentError(
                f"No document parser is registered for '{extension or 'unknown'}'."
            )

        return parser

    def supported_extensions(self) -> tuple[str, ...]:
        """Return all registered extensions in stable order."""

        return tuple(sorted(self._parsers))

    @staticmethod
    def _normalize_extension(
        extension: str,
    ) -> str:
        """Normalize a file extension for registry lookup."""

        normalized_extension = extension.strip().lower()

        if not normalized_extension:
            return ""

        if not normalized_extension.startswith("."):
            normalized_extension = f".{normalized_extension}"

        return normalized_extension
