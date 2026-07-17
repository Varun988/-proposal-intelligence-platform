from pathlib import Path

from app.documents.registry import DocumentParserRegistry
from app.schemas.document import ExtractedDocument


class DocumentExtractionService:
    """Coordinate document parser selection and extraction."""

    def __init__(
        self,
        registry: DocumentParserRegistry,
    ) -> None:
        self._registry = registry

    def extract(
        self,
        file_path: str | Path,
    ) -> ExtractedDocument:
        """Extract a document using its registered parser."""

        normalized_path = Path(file_path).expanduser()

        parser = self._registry.get_parser(
            normalized_path,
        )

        return parser.parse(normalized_path)

    def supports(
        self,
        file_path: str | Path,
    ) -> bool:
        """Return whether the supplied document type is supported."""

        normalized_path = Path(file_path).expanduser()

        return normalized_path.suffix.lower() in self._registry.supported_extensions()

    def supported_extensions(self) -> tuple[str, ...]:
        """Return document extensions supported by the service."""

        return self._registry.supported_extensions()
