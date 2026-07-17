from datetime import UTC

import pytest
from pydantic import ValidationError

from app.schemas.assessment import (
    AssessmentCapability,
    AssessmentCreateRequest,
    AssessmentLifecycleStatus,
    AssessmentStatusResponse,
    create_assessment_id,
    utc_now,
)
from app.workflows.state import WorkflowStatus


def test_create_request_has_safe_defaults() -> None:
    request = AssessmentCreateRequest(
        vendor_name="Example Digital Services",
        proposal_document_id="proposal-001",
    )

    assert request.capabilities == [
        AssessmentCapability.PROPOSAL_ANALYSIS,
        AssessmentCapability.VENDOR_RESEARCH,
        AssessmentCapability.RISK_REPORT,
    ]
    assert request.stale_vendor_evidence_after_days == 365
    assert request.maximum_workflow_steps == 12
    assert request.maximum_retries == 2
    assert request.human_review_required is True


def test_create_request_supports_proposal_only() -> None:
    request = AssessmentCreateRequest(
        vendor_name="Example Digital Services",
        proposal_document_id="proposal-001",
        capabilities=[
            AssessmentCapability.PROPOSAL_ANALYSIS,
        ],
    )

    assert request.capabilities == [
        AssessmentCapability.PROPOSAL_ANALYSIS,
    ]


def test_create_request_rejects_risk_without_proposal() -> None:
    with pytest.raises(
        ValidationError,
        match="Risk reporting requires proposal analysis",
    ):
        AssessmentCreateRequest(
            vendor_name="Example Digital Services",
            proposal_document_id="proposal-001",
            capabilities=[
                AssessmentCapability.RISK_REPORT,
            ],
        )


def test_create_request_rejects_vendor_research_without_proposal() -> None:
    with pytest.raises(
        ValidationError,
        match="Vendor research requires proposal analysis",
    ):
        AssessmentCreateRequest(
            vendor_name="Example Digital Services",
            proposal_document_id="proposal-001",
            capabilities=[
                AssessmentCapability.VENDOR_RESEARCH,
            ],
        )


def test_create_request_rejects_disabled_human_review() -> None:
    with pytest.raises(
        ValidationError,
        match="must require human review",
    ):
        AssessmentCreateRequest(
            vendor_name="Example Digital Services",
            proposal_document_id="proposal-001",
            human_review_required=False,
        )


def test_create_request_rejects_empty_capabilities() -> None:
    with pytest.raises(ValidationError):
        AssessmentCreateRequest(
            vendor_name="Example Digital Services",
            proposal_document_id="proposal-001",
            capabilities=[],
        )


def test_create_assessment_id_returns_unique_prefixed_ids() -> None:
    first_id = create_assessment_id()
    second_id = create_assessment_id()

    assert first_id.startswith("assessment-")
    assert second_id.startswith("assessment-")
    assert first_id != second_id


def test_utc_now_returns_timezone_aware_timestamp() -> None:
    timestamp = utc_now()

    assert timestamp.tzinfo is not None
    assert timestamp.utcoffset() == UTC.utcoffset(timestamp)


def test_status_response_accepts_workflow_summary() -> None:
    created_at = utc_now()
    updated_at = utc_now()

    response = AssessmentStatusResponse(
        assessment_id="assessment-001",
        lifecycle_status=(AssessmentLifecycleStatus.RUNNING),
        workflow_status=(WorkflowStatus.PROPOSAL_ANALYSIS_RUNNING),
        current_step=3,
        maximum_steps=12,
        completed_agents=[
            "orchestrator",
        ],
        human_review_required=True,
        error_count=0,
        created_at=created_at,
        updated_at=updated_at,
    )

    assert response.assessment_id == "assessment-001"
    assert response.current_step == 3
    assert response.completed_agents == [
        "orchestrator",
    ]
    assert response.error_count == 0
