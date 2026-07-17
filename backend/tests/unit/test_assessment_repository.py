import pytest
from app.repositories.assessment import (
    AssessmentRecord,
    InMemoryAssessmentRepository,
)

from app.core.exceptions import (
    AssessmentConflictError,
    AssessmentNotFoundError,
)
from app.schemas.assessment import (
    AssessmentCreateRequest,
    AssessmentLifecycleStatus,
    utc_now,
)
from app.workflows.state import WorkflowStatus


def create_record(
    assessment_id: str = "assessment-001",
) -> AssessmentRecord:
    """Create an internal assessment record for tests."""

    timestamp = utc_now()

    return AssessmentRecord(
        assessment_id=assessment_id,
        request=AssessmentCreateRequest(
            vendor_name="Example Digital Services",
            proposal_document_id="proposal-001",
        ),
        lifecycle_status=(AssessmentLifecycleStatus.CREATED),
        workflow_status=WorkflowStatus.CREATED,
        created_at=timestamp,
        updated_at=timestamp,
    )


@pytest.mark.asyncio
async def test_repository_creates_and_retrieves_record() -> None:
    repository = InMemoryAssessmentRepository()

    created = await repository.create(
        create_record(),
    )

    retrieved = await repository.get(
        created.assessment_id,
    )

    assert retrieved == created
    assert retrieved is not created


@pytest.mark.asyncio
async def test_repository_returns_deep_copy() -> None:
    repository = InMemoryAssessmentRepository()

    await repository.create(
        create_record(),
    )

    retrieved = await repository.get(
        "assessment-001",
    )

    retrieved.request.vendor_name = "Changed Vendor"

    stored = await repository.get(
        "assessment-001",
    )

    assert stored.request.vendor_name == ("Example Digital Services")


@pytest.mark.asyncio
async def test_repository_rejects_duplicate_id() -> None:
    repository = InMemoryAssessmentRepository()
    record = create_record()

    await repository.create(record)

    with pytest.raises(
        AssessmentConflictError,
        match="already exists",
    ):
        await repository.create(record)


@pytest.mark.asyncio
async def test_repository_rejects_unknown_id() -> None:
    repository = InMemoryAssessmentRepository()

    with pytest.raises(
        AssessmentNotFoundError,
        match="not found",
    ):
        await repository.get(
            "assessment-missing",
        )


@pytest.mark.asyncio
async def test_repository_updates_existing_record() -> None:
    repository = InMemoryAssessmentRepository()

    record = await repository.create(
        create_record(),
    )

    updated = record.model_copy(
        update={
            "lifecycle_status": (AssessmentLifecycleStatus.RUNNING),
            "workflow_status": (WorkflowStatus.ORCHESTRATION_RUNNING),
            "updated_at": utc_now(),
        },
        deep=True,
    )

    saved = await repository.update(updated)

    assert saved.lifecycle_status is AssessmentLifecycleStatus.RUNNING
    assert saved.workflow_status is WorkflowStatus.ORCHESTRATION_RUNNING


@pytest.mark.asyncio
async def test_repository_rejects_update_for_unknown_id() -> None:
    repository = InMemoryAssessmentRepository()

    with pytest.raises(
        AssessmentNotFoundError,
        match="not found",
    ):
        await repository.update(
            create_record(
                assessment_id="assessment-missing",
            )
        )


@pytest.mark.asyncio
async def test_repository_checks_existence() -> None:
    repository = InMemoryAssessmentRepository()

    assert await repository.exists("assessment-001") is False

    await repository.create(
        create_record(),
    )

    assert await repository.exists("assessment-001") is True
