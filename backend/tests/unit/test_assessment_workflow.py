import pytest

from app.agents.orchestrator.agent import OrchestratorAgent
from app.agents.orchestrator.schemas import OrchestratorInput
from app.agents.proposal_analysis.schemas import (
    ProposalAnalysisInput,
)
from app.agents.vendor_research.schemas import (
    VendorResearchInput,
)
from app.evaluation.proposal_analysis import (
    create_proposal_analysis_evaluation_runner,
)
from app.evaluation.vendor_research import (
    create_vendor_research_evaluation_runner,
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
    FakeVendorResearchAgent,
)
from app.agents.risk_report.schemas import RiskReportInput
from app.evaluation.risk_report import create_risk_report_evaluation_runner
from tests.workflow_fakes import (
    FakeProposalAnalysisAgent,
    FakeRiskReportAgent,
    FakeVendorResearchAgent,
    create_fake_proposal_result,
)

def create_state(
    maximum_steps: int = 12,
    vendor_research_required: bool = True,
) -> AssessmentWorkflowState:
    """Create a valid synthetic assessment workflow state."""

    return AssessmentWorkflowState(
        assessment_id="assessment-001",
        proposal_document_id="proposal-001",
        orchestrator_input=OrchestratorInput(
            assessment_id="assessment-001",
            proposal_document_id="proposal-001",
            vendor_research_required=(vendor_research_required),
        ),
        proposal_analysis_input=ProposalAnalysisInput(
            assessment_id="assessment-001",
            proposal_document_id="proposal-001",
            analysis_objectives=[
                "delivery timeline",
            ],
        ),
        vendor_research_input=VendorResearchInput(
            assessment_id="assessment-001",
            vendor_name="Example Digital Services",
            proposal_document_id="proposal-001",
            research_objectives=[
                "company profile and ownership",
            ],
        ),
        risk_report_input=RiskReportInput(
            assessment_id="assessment-001",
            proposal_document_id="proposal-001",
            vendor_name="Example Digital Services",
            proposal_analysis=create_fake_proposal_result(),
        ),
        maximum_steps=maximum_steps,
    )


def create_graph(
    proposal_agent: FakeProposalAnalysisAgent | None = None,
    vendor_agent: FakeVendorResearchAgent | None = None,
    risk_agent: FakeRiskReportAgent | None = None,
):
    """Create the complete four-agent assessment graph."""

    return create_assessment_graph(
        orchestrator_agent=OrchestratorAgent(),
        proposal_analysis_agent=(
            proposal_agent
            or FakeProposalAnalysisAgent()
        ),
        proposal_evaluation_runner=(
            create_proposal_analysis_evaluation_runner()
        ),
        vendor_research_agent=(
            vendor_agent
            or FakeVendorResearchAgent()
        ),
        vendor_evaluation_runner=(
            create_vendor_research_evaluation_runner()
        ),
        risk_report_agent=(
            risk_agent
            or FakeRiskReportAgent()
        ),
        risk_report_evaluation_runner=(
            create_risk_report_evaluation_runner()
        ),
    )


@pytest.mark.asyncio
async def test_workflow_routes_valid_execution_forward() -> None:
    proposal_agent = FakeProposalAnalysisAgent()
    vendor_agent = FakeVendorResearchAgent()

    result = await create_graph(
        proposal_agent=proposal_agent,
        vendor_agent=vendor_agent,
    ).ainvoke(
        create_state(),
    )

    final_state = AssessmentWorkflowState.model_validate(
        result,
    )

    assert final_state.status is WorkflowStatus.COMPLETED
    assert final_state.human_review_required is True
    assert final_state.human_review_reason is not None
    assert "human" in final_state.human_review_reason.casefold()

    assert final_state.orchestrator_execution is not None
    assert final_state.proposal_analysis_execution is not None
    assert final_state.proposal_analysis_evaluation is not None
    assert final_state.vendor_research_execution is not None
    assert final_state.vendor_research_evaluation is not None

    assert final_state.proposal_analysis_evaluation.release_approved is True
    assert final_state.vendor_research_evaluation.release_approved is True
    assert final_state.risk_report_execution is not None
    assert final_state.risk_report_evaluation is not None
    assert final_state.risk_report_passed is True
    assert "risk-report" in final_state.completed_agents
    assert "orchestrator" in final_state.completed_agents
    assert "proposal-analysis" in final_state.completed_agents
    assert "vendor-research" in final_state.completed_agents

    assert len(proposal_agent.received_inputs) == 1
    assert len(vendor_agent.received_inputs) == 1


@pytest.mark.asyncio
async def test_workflow_executes_vendor_research() -> None:
    vendor_agent = FakeVendorResearchAgent()

    result = await create_graph(
        vendor_agent=vendor_agent,
    ).ainvoke(
        create_state(),
    )

    final_state = AssessmentWorkflowState.model_validate(
        result,
    )

    assert final_state.vendor_research_execution is not None
    assert final_state.vendor_research_evaluation is not None

    assert final_state.vendor_research_evaluation.release_approved is True

    assert "vendor-research" in final_state.completed_agents
    assert len(vendor_agent.received_inputs) == 1

    assert final_state.status is WorkflowStatus.COMPLETED


@pytest.mark.asyncio
async def test_workflow_skips_unplanned_vendor_research() -> None:
    vendor_agent = FakeVendorResearchAgent()

    result = await create_graph(
        vendor_agent=vendor_agent,
    ).ainvoke(
        create_state(
            vendor_research_required=False,
        ),
    )

    final_state = AssessmentWorkflowState.model_validate(
        result,
    )

    assert final_state.status is WorkflowStatus.COMPLETED
    assert final_state.vendor_research_execution is None
    assert final_state.vendor_research_evaluation is None
    assert "vendor-research" not in final_state.completed_agents
    assert vendor_agent.received_inputs == []
    assert final_state.risk_report_execution is not None
    assert final_state.risk_report_evaluation is not None
    assert "risk-report" in final_state.completed_agents


@pytest.mark.asyncio
async def test_workflow_routes_proposal_failure_to_human_review() -> None:
    result = await create_graph(
        proposal_agent=FakeProposalAnalysisAgent(
            should_fail=True,
        ),
    ).ainvoke(
        create_state(),
    )

    final_state = AssessmentWorkflowState.model_validate(
        result,
    )

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
    assert final_state.vendor_research_execution is None


@pytest.mark.asyncio
async def test_workflow_routes_proposal_gate_failure_to_review() -> None:
    result = await create_graph(
        proposal_agent=FakeProposalAnalysisAgent(
            disable_human_review=True,
        ),
    ).ainvoke(
        create_state(),
    )

    final_state = AssessmentWorkflowState.model_validate(
        result,
    )

    assert final_state.status is WorkflowStatus.HUMAN_REVIEW_REQUIRED
    assert final_state.human_review_required is True
    assert final_state.proposal_analysis_evaluation is not None

    assert final_state.proposal_analysis_evaluation.release_approved is False

    assert final_state.vendor_research_execution is None


@pytest.mark.asyncio
async def test_workflow_routes_vendor_failure_to_review() -> None:
    result = await create_graph(
        vendor_agent=FakeVendorResearchAgent(
            should_fail=True,
        ),
    ).ainvoke(
        create_state(),
    )

    final_state = AssessmentWorkflowState.model_validate(
        result,
    )

    assert final_state.status is WorkflowStatus.HUMAN_REVIEW_REQUIRED
    assert final_state.human_review_required is True
    assert final_state.human_review_reason is not None
    assert final_state.errors

    vendor_record = next(
        record
        for record in final_state.agent_execution_records
        if record.agent_name == "vendor-research"
    )

    assert vendor_record.succeeded is False


@pytest.mark.asyncio
async def test_workflow_routes_vendor_gate_failure_to_review() -> None:
    result = await create_graph(
        vendor_agent=FakeVendorResearchAgent(
            disable_human_review=True,
        ),
    ).ainvoke(
        create_state(),
    )

    final_state = AssessmentWorkflowState.model_validate(
        result,
    )

    assert final_state.status is WorkflowStatus.HUMAN_REVIEW_REQUIRED
    assert final_state.human_review_required is True
    assert final_state.vendor_research_evaluation is not None

    assert final_state.vendor_research_evaluation.release_approved is False

    assert final_state.vendor_research_evaluation.blocking_gate_failure_count >= 1


@pytest.mark.asyncio
async def test_workflow_records_agent_and_evaluation_results() -> None:
    result = await create_graph().ainvoke(
        create_state(),
    )

    final_state = AssessmentWorkflowState.model_validate(
        result,
    )

    assert [
        record.agent_name
        for record in final_state.agent_execution_records
    ] == [
        "orchestrator",
        "proposal-analysis",
        "vendor-research",
        "risk-report",
    ]

    assert all(record.succeeded for record in final_state.agent_execution_records)

    assert [record.agent_name for record in final_state.evaluation_records] == [
        "proposal-analysis",
        "vendor-research",
        "risk-report",
    ]

    assert all(record.release_approved for record in final_state.evaluation_records)


@pytest.mark.asyncio
async def test_workflow_records_auditable_events() -> None:
    result = await create_graph().ainvoke(
        create_state(),
    )

    final_state = AssessmentWorkflowState.model_validate(
        result,
    )

    event_types = [event.event_type.value for event in final_state.events]

    assert "orchestration_started" in event_types
    assert "orchestration_completed" in event_types
    assert event_types.count("agent_started") == 3
    assert event_types.count("agent_completed") == 3
    assert event_types.count("evaluation_started") == 3
    assert event_types.count("evaluation_completed") == 3
    assert "workflow_completed" in event_types
    assert "status_changed" in event_types


@pytest.mark.asyncio
async def test_workflow_respects_step_limit() -> None:
    result = await create_graph().ainvoke(
        create_state(
            maximum_steps=1,
        ),
    )

    final_state = AssessmentWorkflowState.model_validate(
        result,
    )

    assert final_state.status is WorkflowStatus.HUMAN_REVIEW_REQUIRED
    assert final_state.human_review_required is True
    assert final_state.human_review_reason is not None

    assert "step limit" in (final_state.human_review_reason.casefold())



@pytest.mark.asyncio
async def test_workflow_executes_risk_report() -> None:
    risk_agent = FakeRiskReportAgent()
    result = await create_graph(risk_agent=risk_agent).ainvoke(create_state())
    final_state = AssessmentWorkflowState.model_validate(result)

    assert final_state.risk_report_execution is not None
    assert final_state.risk_report_evaluation is not None
    assert final_state.risk_report_passed is True
    assert "risk-report" in final_state.completed_agents
    assert len(risk_agent.received_inputs) == 1
    assert final_state.status is WorkflowStatus.COMPLETED
    assert final_state.human_review_required is True


@pytest.mark.asyncio
async def test_workflow_routes_risk_agent_failure_to_review() -> None:
    result = await create_graph(
        risk_agent=FakeRiskReportAgent(should_fail=True),
    ).ainvoke(create_state())
    final_state = AssessmentWorkflowState.model_validate(result)

    assert final_state.status is WorkflowStatus.HUMAN_REVIEW_REQUIRED
    assert final_state.human_review_required is True
    assert final_state.errors


@pytest.mark.asyncio
async def test_workflow_routes_risk_gate_failure_to_review() -> None:
    result = await create_graph(
        risk_agent=FakeRiskReportAgent(invalid_source_reference=True),
    ).ainvoke(create_state())
    final_state = AssessmentWorkflowState.model_validate(result)

    assert final_state.status is WorkflowStatus.HUMAN_REVIEW_REQUIRED
    assert final_state.risk_report_evaluation is not None
    assert final_state.risk_report_evaluation.release_approved is False


@pytest.mark.asyncio
async def test_completed_workflow_preserves_human_authority() -> None:
    result = await create_graph().ainvoke(create_state())
    final_state = AssessmentWorkflowState.model_validate(result)

    assert final_state.status is WorkflowStatus.COMPLETED
    assert final_state.human_review_required is True
    assert final_state.human_review_reason is not None
    assert "human" in final_state.human_review_reason.casefold()


def test_graph_compiles_successfully() -> None:
    graph = create_graph()

    assert graph is not None
