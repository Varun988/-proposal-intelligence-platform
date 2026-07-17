import pytest
from pydantic import ValidationError
from app.agents.orchestrator.schemas import OrchestratorInput

from app.agents.proposal_analysis.schemas import (
    ProposalAnalysisInput,
)
from app.workflows.state import (
    AgentExecutionRecord,
    AssessmentWorkflowState,
    EvaluationRecord,
    WorkflowEvent,
    WorkflowEventType,
    WorkflowRoute,
    WorkflowStatus,
)


def create_state(
    current_step: int = 0,
    maximum_steps: int = 12,
    retry_count: int = 0,
    maximum_retries: int = 2,
) -> AssessmentWorkflowState:
    """Create a valid synthetic assessment workflow state."""

    return AssessmentWorkflowState(
        assessment_id="assessment-001",
        proposal_document_id="proposal-001",
        rfp_document_id="rfp-001",
        orchestrator_input=OrchestratorInput(
            assessment_id="assessment-001",
            proposal_document_id="proposal-001",
            rfp_document_id="rfp-001",
        ),
        proposal_analysis_input=ProposalAnalysisInput(
            assessment_id="assessment-001",
            proposal_document_id="proposal-001",
            rfp_document_id="rfp-001",
            analysis_objectives=[
                "delivery timeline",
            ],
        ),
        current_step=current_step,
        maximum_steps=maximum_steps,
        retry_count=retry_count,
        maximum_retries=maximum_retries,
    )


def test_workflow_state_has_safe_defaults() -> None:
    state = create_state()

    assert state.status is WorkflowStatus.CREATED
    assert state.next_route is None
    assert state.current_step == 0
    assert state.maximum_steps == 12
    assert state.retry_count == 0
    assert state.maximum_retries == 2
    assert state.human_review_required is False

    assert state.agent_execution_records == []
    assert state.evaluation_records == []
    assert state.events == []
    assert state.completed_agents == []
    assert state.errors == []


def test_workflow_state_detects_step_limit() -> None:
    state = create_state(
        current_step=12,
        maximum_steps=12,
    )

    assert state.step_limit_reached is True


def test_workflow_state_allows_remaining_steps() -> None:
    state = create_state(
        current_step=11,
        maximum_steps=12,
    )

    assert state.step_limit_reached is False


def test_workflow_state_detects_retry_limit() -> None:
    state = create_state(
        retry_count=2,
        maximum_retries=2,
    )

    assert state.retry_limit_reached is True


def test_workflow_state_records_events() -> None:
    state = create_state()

    state.events.append(
        WorkflowEvent(
            event_type=WorkflowEventType.STATUS_CHANGED,
            status=WorkflowStatus.INITIALIZING,
            message="Assessment workflow initialized.",
            metadata={
                "previous_status": "created",
            },
        )
    )

    assert len(state.events) == 1
    assert state.events[0].status is WorkflowStatus.INITIALIZING


def test_workflow_state_records_agent_execution() -> None:
    state = create_state()

    state.agent_execution_records.append(
        AgentExecutionRecord(
            agent_name="proposal-analysis",
            succeeded=True,
            tool_call_count=4,
            execution_time_ms=1250.0,
            instruction_version="1.0.0",
        )
    )

    assert len(state.agent_execution_records) == 1
    assert state.agent_execution_records[0].succeeded is True


def test_workflow_state_records_evaluation() -> None:
    state = create_state()

    state.evaluation_records.append(
        EvaluationRecord(
            agent_name="proposal-analysis",
            evaluation_id="evaluation-001",
            overall_score=1.0,
            release_approved=True,
            blocking_gate_failure_count=0,
        )
    )

    assert len(state.evaluation_records) == 1
    assert state.evaluation_records[0].release_approved is True


def test_workflow_state_supports_routing_decision() -> None:
    state = create_state()

    state.status = WorkflowStatus.PROPOSAL_ANALYSIS_PENDING
    state.next_route = WorkflowRoute.RUN_PROPOSAL_ANALYSIS

    assert state.next_route is WorkflowRoute.RUN_PROPOSAL_ANALYSIS


def test_workflow_state_rejects_assessment_id_mismatch() -> None:
    with pytest.raises(
        ValidationError,
        match="assessment ID must match",
    ):
        AssessmentWorkflowState(
            assessment_id="assessment-001",
            proposal_document_id="proposal-001",
            proposal_analysis_input=ProposalAnalysisInput(
                assessment_id="wrong-assessment",
                proposal_document_id="proposal-001",
            ),
        )


def test_workflow_state_rejects_document_id_mismatch() -> None:
    with pytest.raises(
        ValidationError,
        match="document ID must match",
    ):
        AssessmentWorkflowState(
            assessment_id="assessment-001",
            proposal_document_id="proposal-001",
            proposal_analysis_input=ProposalAnalysisInput(
                assessment_id="assessment-001",
                proposal_document_id="wrong-proposal",
            ),
        )


def test_workflow_state_rejects_rfp_id_mismatch() -> None:
    with pytest.raises(
        ValidationError,
        match="RFP document ID must match",
    ):
        AssessmentWorkflowState(
            assessment_id="assessment-001",
            proposal_document_id="proposal-001",
            rfp_document_id="rfp-001",
            proposal_analysis_input=ProposalAnalysisInput(
                assessment_id="assessment-001",
                proposal_document_id="proposal-001",
                rfp_document_id="wrong-rfp",
            ),
        )


def test_workflow_state_rejects_invalid_limits() -> None:
    with pytest.raises(ValidationError):
        create_state(
            current_step=0,
            maximum_steps=0,
        )
