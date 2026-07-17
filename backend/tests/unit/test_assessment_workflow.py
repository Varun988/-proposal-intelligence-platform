import pytest

from app.agents.orchestrator.agent import OrchestratorAgent
from app.agents.orchestrator.schemas import OrchestratorInput
from app.agents.proposal_analysis.schemas import ProposalAnalysisInput
from app.evaluation.proposal_analysis import (
    create_proposal_analysis_evaluation_runner,
)
from app.workflows.assessment_graph import create_assessment_graph
from app.workflows.state import AssessmentWorkflowState, WorkflowStatus
from tests.workflow_fakes import FakeProposalAnalysisAgent


def create_state(maximum_steps: int = 12) -> AssessmentWorkflowState:
    """Create a valid synthetic assessment workflow state."""

    return AssessmentWorkflowState(
        assessment_id="assessment-001",
        proposal_document_id="proposal-001",
        orchestrator_input=OrchestratorInput(
            assessment_id="assessment-001",
            proposal_document_id="proposal-001",
        ),
        proposal_analysis_input=ProposalAnalysisInput(
            assessment_id="assessment-001",
            proposal_document_id="proposal-001",
            analysis_objectives=["delivery timeline"],
        ),
        maximum_steps=maximum_steps,
    )


def create_graph(agent: FakeProposalAnalysisAgent):
    return create_assessment_graph(
        orchestrator_agent=OrchestratorAgent(),
        proposal_analysis_agent=agent,
        evaluation_runner=create_proposal_analysis_evaluation_runner(),
    )


@pytest.mark.asyncio
async def test_workflow_routes_valid_execution_forward() -> None:
    agent = FakeProposalAnalysisAgent()
    result = await create_graph(agent).ainvoke(create_state())
    final_state = AssessmentWorkflowState.model_validate(result)

    assert final_state.status is WorkflowStatus.READY_FOR_NEXT_AGENT
    assert final_state.human_review_required is False
    assert final_state.orchestrator_execution is not None
    assert final_state.proposal_analysis_execution is not None
    assert final_state.proposal_analysis_evaluation is not None
    assert final_state.proposal_analysis_evaluation.release_approved is True
    assert "orchestrator" in final_state.completed_agents
    assert "proposal-analysis" in final_state.completed_agents
    assert len(agent.received_inputs) == 1


@pytest.mark.asyncio
async def test_workflow_routes_agent_failure_to_human_review() -> None:
    result = await create_graph(FakeProposalAnalysisAgent(should_fail=True)).ainvoke(create_state())
    final_state = AssessmentWorkflowState.model_validate(result)

    assert final_state.status is WorkflowStatus.HUMAN_REVIEW_REQUIRED
    assert final_state.human_review_required is True
    assert final_state.human_review_reason is not None
    assert final_state.errors
    proposal_record = next(
        record
        for record in final_state.agent_execution_records
        if record.agent_name == "proposal-analysis"
    )
    assert proposal_record.succeeded is False


@pytest.mark.asyncio
async def test_workflow_routes_failed_evaluation_to_review() -> None:
    result = await create_graph(FakeProposalAnalysisAgent(disable_human_review=True)).ainvoke(
        create_state()
    )
    final_state = AssessmentWorkflowState.model_validate(result)

    assert final_state.status is WorkflowStatus.HUMAN_REVIEW_REQUIRED
    assert final_state.human_review_required is True
    assert final_state.proposal_analysis_evaluation is not None
    assert final_state.proposal_analysis_evaluation.release_approved is False


@pytest.mark.asyncio
async def test_workflow_records_agent_and_evaluation_results() -> None:
    result = await create_graph(FakeProposalAnalysisAgent()).ainvoke(create_state())
    final_state = AssessmentWorkflowState.model_validate(result)

    assert [record.agent_name for record in final_state.agent_execution_records] == [
        "orchestrator",
        "proposal-analysis",
    ]
    assert len(final_state.evaluation_records) == 1
    assert final_state.evaluation_records[0].release_approved is True


@pytest.mark.asyncio
async def test_workflow_records_orchestration_events() -> None:
    result = await create_graph(FakeProposalAnalysisAgent()).ainvoke(create_state())
    final_state = AssessmentWorkflowState.model_validate(result)
    event_types = {event.event_type.value for event in final_state.events}

    assert "orchestration_started" in event_types
    assert "orchestration_completed" in event_types
    assert "agent_started" in event_types
    assert "evaluation_completed" in event_types


@pytest.mark.asyncio
async def test_workflow_respects_step_limit() -> None:
    result = await create_graph(FakeProposalAnalysisAgent()).ainvoke(create_state(maximum_steps=1))
    final_state = AssessmentWorkflowState.model_validate(result)

    assert final_state.status is WorkflowStatus.HUMAN_REVIEW_REQUIRED
    assert final_state.human_review_required is True
    assert final_state.human_review_reason is not None
    assert "step limit" in final_state.human_review_reason.casefold()


def test_graph_compiles_successfully() -> None:
    assert create_graph(FakeProposalAnalysisAgent()) is not None
