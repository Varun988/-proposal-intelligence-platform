import pytest

from app.agents.proposal_analysis.schemas import (
    ProposalAnalysisInput,
)
from app.evaluation.proposal_analysis import (
    create_proposal_analysis_evaluation_runner,
)
from app.workflows.assessment_graph import (
    create_assessment_graph,
)
from app.workflows.state import (
    AssessmentWorkflowState,
    WorkflowStatus,
)
from tests.workflow_fakes import (
    FakeProposalAnalysisAgent,
)


def create_state(
    maximum_steps: int = 12,
) -> AssessmentWorkflowState:
    """Create a valid synthetic assessment workflow state."""

    return AssessmentWorkflowState(
        assessment_id="assessment-001",
        proposal_document_id="proposal-001",
        proposal_analysis_input=ProposalAnalysisInput(
            assessment_id="assessment-001",
            proposal_document_id="proposal-001",
            analysis_objectives=[
                "delivery timeline",
            ],
        ),
        maximum_steps=maximum_steps,
    )


@pytest.mark.asyncio
async def test_workflow_routes_valid_execution_forward() -> None:
    agent = FakeProposalAnalysisAgent()

    graph = create_assessment_graph(
        proposal_analysis_agent=agent,
        evaluation_runner=(create_proposal_analysis_evaluation_runner()),
    )

    result = await graph.ainvoke(
        create_state(),
    )

    final_state = AssessmentWorkflowState.model_validate(
        result,
    )

    assert final_state.status is WorkflowStatus.READY_FOR_NEXT_AGENT
    assert final_state.human_review_required is False
    assert final_state.proposal_analysis_execution is not None
    assert final_state.proposal_analysis_evaluation is not None
    assert final_state.proposal_analysis_evaluation.release_approved is True
    assert "proposal-analysis" in final_state.completed_agents
    assert len(agent.received_inputs) == 1


@pytest.mark.asyncio
async def test_workflow_routes_agent_failure_to_human_review() -> None:
    agent = FakeProposalAnalysisAgent(
        should_fail=True,
    )

    graph = create_assessment_graph(
        proposal_analysis_agent=agent,
        evaluation_runner=(create_proposal_analysis_evaluation_runner()),
    )

    result = await graph.ainvoke(
        create_state(),
    )

    final_state = AssessmentWorkflowState.model_validate(
        result,
    )

    assert final_state.status is WorkflowStatus.HUMAN_REVIEW_REQUIRED
    assert final_state.human_review_required is True
    assert final_state.human_review_reason is not None
    assert final_state.errors
    assert final_state.agent_execution_records[0].succeeded is False


@pytest.mark.asyncio
async def test_workflow_routes_failed_evaluation_to_review() -> None:
    agent = FakeProposalAnalysisAgent(
        disable_human_review=True,
    )

    graph = create_assessment_graph(
        proposal_analysis_agent=agent,
        evaluation_runner=(create_proposal_analysis_evaluation_runner()),
    )

    result = await graph.ainvoke(
        create_state(),
    )

    final_state = AssessmentWorkflowState.model_validate(
        result,
    )

    assert final_state.status is WorkflowStatus.HUMAN_REVIEW_REQUIRED
    assert final_state.human_review_required is True
    assert final_state.proposal_analysis_evaluation is not None
    assert final_state.proposal_analysis_evaluation.release_approved is False
    assert final_state.proposal_analysis_evaluation.blocking_gate_failure_count >= 1


@pytest.mark.asyncio
async def test_workflow_records_auditable_events() -> None:
    graph = create_assessment_graph(
        proposal_analysis_agent=(FakeProposalAnalysisAgent()),
        evaluation_runner=(create_proposal_analysis_evaluation_runner()),
    )

    result = await graph.ainvoke(
        create_state(),
    )

    final_state = AssessmentWorkflowState.model_validate(
        result,
    )

    assert len(final_state.events) >= 6

    event_types = {event.event_type.value for event in final_state.events}

    assert "status_changed" in event_types
    assert "agent_started" in event_types
    assert "agent_completed" in event_types
    assert "evaluation_started" in event_types
    assert "evaluation_completed" in event_types


@pytest.mark.asyncio
async def test_workflow_records_agent_and_evaluation_results() -> None:
    graph = create_assessment_graph(
        proposal_analysis_agent=(FakeProposalAnalysisAgent()),
        evaluation_runner=(create_proposal_analysis_evaluation_runner()),
    )

    result = await graph.ainvoke(
        create_state(),
    )

    final_state = AssessmentWorkflowState.model_validate(
        result,
    )

    assert len(final_state.agent_execution_records) == 1
    assert final_state.agent_execution_records[0].agent_name == "proposal-analysis"
    assert final_state.agent_execution_records[0].succeeded is True

    assert len(final_state.evaluation_records) == 1
    assert final_state.evaluation_records[0].release_approved is True
    assert final_state.evaluation_records[0].blocking_gate_failure_count == 0


@pytest.mark.asyncio
async def test_workflow_respects_step_limit() -> None:
    graph = create_assessment_graph(
        proposal_analysis_agent=(FakeProposalAnalysisAgent()),
        evaluation_runner=(create_proposal_analysis_evaluation_runner()),
    )

    state = create_state(
        maximum_steps=1,
    )

    result = await graph.ainvoke(
        state,
    )

    final_state = AssessmentWorkflowState.model_validate(
        result,
    )

    assert final_state.status is WorkflowStatus.HUMAN_REVIEW_REQUIRED
    assert final_state.human_review_required is True
    assert final_state.human_review_reason is not None
    assert "step limit" in (final_state.human_review_reason.casefold())


def test_graph_compiles_successfully() -> None:
    graph = create_assessment_graph(
        proposal_analysis_agent=(FakeProposalAnalysisAgent()),
        evaluation_runner=(create_proposal_analysis_evaluation_runner()),
    )

    assert graph is not None
