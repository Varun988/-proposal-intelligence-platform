from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from pydantic import ValidationError

from app.api.dependencies import get_document_service
from app.core.exceptions import (
    DocumentNotFoundError,
    DocumentStorageError,
    DocumentValidationError,
)
from app.schemas.document_upload import (
    DocumentPurpose,
    DocumentStatusResponse,
    DocumentUploadMetadata,
    DocumentUploadResponse,
)
from app.services.document_service import DocumentService
from app.services.document_validation_service import (
    MAXIMUM_DOCUMENT_SIZE_BYTES,
)

router = APIRouter(
    prefix="/documents",
    tags=["documents"],
)


DocumentServiceDependency = Annotated[
    DocumentService,
    Depends(get_document_service),
]


@router.post(
    "",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "description": ("The uploaded document or its metadata failed validation."),
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": ("The document could not be stored."),
        },
    },
)
async def upload_document(
    document_service: DocumentServiceDependency,
    file: Annotated[
        UploadFile,
        File(description=("PDF or UTF-8 text document.")),
    ],
    purpose: Annotated[
        DocumentPurpose,
        Form(),
    ],
    vendor_name: Annotated[
        str | None,
        Form(),
    ] = None,
    assessment_id: Annotated[
        str | None,
        Form(),
    ] = None,
    source_name: Annotated[
        str | None,
        Form(),
    ] = None,
    is_public_source: Annotated[
        bool,
        Form(),
    ] = False,
) -> DocumentUploadResponse:
    """Validate and store one uploaded document."""

    original_file_name = file.filename or ""

    try:
        content = await file.read(
            MAXIMUM_DOCUMENT_SIZE_BYTES + 1,
        )

        try:
            metadata = DocumentUploadMetadata(
                purpose=purpose,
                vendor_name=vendor_name,
                assessment_id=assessment_id,
                source_name=source_name,
                is_public_source=is_public_source,
            )
        except ValidationError as error:
            raise HTTPException(
                status_code=(status.HTTP_422_UNPROCESSABLE_ENTITY),
                detail={
                    "error_code": ("document_metadata_invalid"),
                    "message": ("The document metadata failed validation."),
                    "details": {
                        "validation_error_count": len(error.errors()),
                    },
                },
            ) from error

        return await document_service.upload_document(
            original_file_name=original_file_name,
            declared_media_type=file.content_type,
            content=content,
            metadata=metadata,
        )

    except DocumentValidationError as error:
        raise HTTPException(
            status_code=(status.HTTP_422_UNPROCESSABLE_ENTITY),
            detail={
                "error_code": "document_validation_failed",
                "message": str(error),
                "details": {},
            },
        ) from error

    except DocumentStorageError as error:
        raise HTTPException(
            status_code=(status.HTTP_500_INTERNAL_SERVER_ERROR),
            detail={
                "error_code": "document_storage_failed",
                "message": str(error),
                "details": {},
            },
        ) from error

    finally:
        await file.close()


@router.get(
    "/{document_id}",
    response_model=DocumentStatusResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "Document not found.",
        },
    },
)
async def get_document_status(
    document_id: str,
    document_service: DocumentServiceDependency,
) -> DocumentStatusResponse:
    """Return the processing status of one document."""

    try:
        return await document_service.get_status(
            document_id,
        )
    except DocumentNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "document_not_found",
                "message": str(error),
                "document_id": document_id,
                "details": {},
            },
        ) from error
