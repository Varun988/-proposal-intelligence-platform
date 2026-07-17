from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class DocumentPurpose(StrEnum):
    """Business purpose assigned to an uploaded document."""

    PROPOSAL = "proposal"
    RFP = "rfp"
    SUPPORTING_EVIDENCE = "supporting_evidence"
    VENDOR_PROFILE = "vendor_profile"


class DocumentLifecycleStatus(StrEnum):
    """Processing lifecycle for an uploaded document."""

    REGISTERED = "registered"
    STORED = "stored"
    EXTRACTION_PENDING = "extraction_pending"
    EXTRACTION_RUNNING = "extraction_running"
    EXTRACTED = "extracted"
    CHUNKING_PENDING = "chunking_pending"
    CHUNKING_RUNNING = "chunking_running"
    CHUNKED = "chunked"
    INDEXING_PENDING = "indexing_pending"
    INDEXING_RUNNING = "indexing_running"
    INDEXED = "indexed"
    FAILED = "failed"


class DocumentMediaType(StrEnum):
    """Media types accepted by the upload service."""

    PDF = "application/pdf"
    TEXT = "text/plain"


class DocumentUploadMetadata(BaseModel):
    """Metadata supplied with one document upload."""

    purpose: DocumentPurpose

    vendor_name: str | None = Field(
        default=None,
        max_length=200,
    )
    assessment_id: str | None = Field(
        default=None,
        max_length=200,
    )
    source_name: str | None = Field(
        default=None,
        max_length=300,
    )

    is_public_source: bool = False

    @model_validator(mode="after")
    def validate_vendor_profile(
        self,
    ) -> "DocumentUploadMetadata":
        """Require a vendor name for vendor-profile uploads."""

        if self.purpose is DocumentPurpose.VENDOR_PROFILE and not self.vendor_name:
            raise ValueError("Vendor-profile documents require a vendor name.")

        return self


class StoredDocumentRecord(BaseModel):
    """Stored metadata and lifecycle for one uploaded document."""

    document_id: str = Field(min_length=1)

    original_file_name: str = Field(min_length=1)
    storage_file_name: str = Field(min_length=1)

    media_type: DocumentMediaType
    purpose: DocumentPurpose
    lifecycle_status: DocumentLifecycleStatus

    file_size_bytes: int = Field(ge=1)

    checksum_sha256: str = Field(
        min_length=64,
        max_length=64,
    )

    vendor_name: str | None = None
    assessment_id: str | None = None
    source_name: str | None = None
    is_public_source: bool = False

    page_count: int | None = Field(
        default=None,
        ge=1,
    )
    extracted_character_count: int = Field(
        default=0,
        ge=0,
    )
    chunk_count: int = Field(
        default=0,
        ge=0,
    )

    error_message: str | None = None

    created_at: datetime
    updated_at: datetime


class DocumentUploadResponse(BaseModel):
    """Response returned after storing an uploaded document."""

    document_id: str = Field(min_length=1)
    original_file_name: str = Field(min_length=1)

    media_type: DocumentMediaType
    purpose: DocumentPurpose
    lifecycle_status: DocumentLifecycleStatus

    file_size_bytes: int = Field(ge=1)

    checksum_sha256: str = Field(
        min_length=64,
        max_length=64,
    )

    created_at: datetime

class DocumentProcessResponse(BaseModel):
    """Response returned after accepting document processing."""

    document_id: str = Field(min_length=1)
    lifecycle_status: DocumentLifecycleStatus
    processing_accepted: bool
    message: str = Field(min_length=1)


class DocumentStatusResponse(BaseModel):
    """Public processing status for one uploaded document."""

    document_id: str = Field(min_length=1)
    original_file_name: str = Field(min_length=1)

    purpose: DocumentPurpose
    lifecycle_status: DocumentLifecycleStatus

    page_count: int | None = Field(
        default=None,
        ge=1,
    )
    extracted_character_count: int = Field(
        default=0,
        ge=0,
    )
    chunk_count: int = Field(
        default=0,
        ge=0,
    )

    error_message: str | None = None

    created_at: datetime
    updated_at: datetime
