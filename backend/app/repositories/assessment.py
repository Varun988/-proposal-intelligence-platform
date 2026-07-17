import asyncio
from datetime import datetime
from typing import Protocol

from pydantic import BaseModel, Field

from app.core.exceptions import (
    AssessmentConflictError,
    AssessmentNotFoundError,
)
from app.schemas.assessment import (
    AssessmentCreateRequest,
    AssessmentLifecycleStatus,
)
from app.workflows.state import (
    AssessmentWorkflowState,
    WorkflowStatus,
)


class AssessmentRecord(BaseModel):
    """Internal persistent representation of an assessment."""

    assessment_id: str = Field(min_length=1)
    request: AssessmentCreateRequest

    lifecycle_status: AssessmentLifecycleStatus = AssessmentLifecycleStatus.CREATED
    workflow_status: WorkflowStatus = WorkflowStatus.CREATED

    workflow_state: AssessmentWorkflowState | None = None

    execution_requested: bool = False
    execution_started_at: datetime | None = None
    execution_completed_at: datetime | None = None

    created_at: datetime
    updated_at: datetime


class AssessmentRepositoryProtocol(Protocol):
    """Persistence contract used by the assessment service."""

    async def create(
        self,
        record: AssessmentRecord,
    ) -> AssessmentRecord:
        """Persist a new assessment record."""

    async def get(
        self,
        assessment_id: str,
    ) -> AssessmentRecord:
        """Retrieve one assessment record."""

    async def update(
        self,
        record: AssessmentRecord,
    ) -> AssessmentRecord:
        """Replace an existing assessment record."""

    async def exists(
        self,
        assessment_id: str,
    ) -> bool:
        """Return whether an assessment exists."""

    async def claim_execution(
        self,
        assessment_id: str,
        updated_at: datetime,
    ) -> AssessmentRecord:
        """Atomically claim an assessment for execution."""


class InMemoryAssessmentRepository:
    """Concurrency-safe in-memory assessment repository."""

    def __init__(self) -> None:
        self._records: dict[str, AssessmentRecord] = {}
        self._lock = asyncio.Lock()

    async def create(
        self,
        record: AssessmentRecord,
    ) -> AssessmentRecord:
        """Persist a new assessment record."""

        async with self._lock:
            if record.assessment_id in self._records:
                raise AssessmentConflictError(f"Assessment already exists: {record.assessment_id}.")

            stored_record = record.model_copy(
                deep=True,
            )

            self._records[record.assessment_id] = stored_record

            return stored_record.model_copy(
                deep=True,
            )

    async def get(
        self,
        assessment_id: str,
    ) -> AssessmentRecord:
        """Retrieve one assessment record."""

        normalized_id = assessment_id.strip()

        if not normalized_id:
            raise AssessmentNotFoundError("Assessment ID cannot be empty.")

        async with self._lock:
            record = self._records.get(
                normalized_id,
            )

            if record is None:
                raise AssessmentNotFoundError(f"Assessment not found: {normalized_id}.")

            return record.model_copy(
                deep=True,
            )

    async def update(
        self,
        record: AssessmentRecord,
    ) -> AssessmentRecord:
        """Replace an existing assessment record."""

        async with self._lock:
            if record.assessment_id not in self._records:
                raise AssessmentNotFoundError(f"Assessment not found: {record.assessment_id}.")

            stored_record = record.model_copy(
                deep=True,
            )

            self._records[record.assessment_id] = stored_record

            return stored_record.model_copy(
                deep=True,
            )

    async def exists(
        self,
        assessment_id: str,
    ) -> bool:
        """Return whether an assessment exists."""

        normalized_id = assessment_id.strip()

        if not normalized_id:
            return False

        async with self._lock:
            return normalized_id in self._records

    async def clear(self) -> None:
        """Remove all records for isolated tests."""

        async with self._lock:
            self._records.clear()

    async def claim_execution(
        self,
        assessment_id: str,
        updated_at: datetime,
    ) -> AssessmentRecord:
        """Atomically claim an assessment for execution."""

        normalized_id = assessment_id.strip()

        if not normalized_id:
            raise AssessmentNotFoundError("Assessment ID cannot be empty.")

        async with self._lock:
            record = self._records.get(
                normalized_id,
            )

            if record is None:
                raise AssessmentNotFoundError(f"Assessment not found: {normalized_id}.")

            if record.execution_requested:
                raise AssessmentConflictError("Assessment execution has already been requested.")

            updated_record = record.model_copy(
                update={
                    "execution_requested": True,
                    "lifecycle_status": (AssessmentLifecycleStatus.QUEUED),
                    "updated_at": updated_at,
                },
                deep=True,
            )

            self._records[normalized_id] = updated_record

            return updated_record.model_copy(
                deep=True,
            )
