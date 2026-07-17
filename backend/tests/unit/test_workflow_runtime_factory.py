import pytest

from app.agents.orchestrator.schemas import OrchestratorInput
from app.agents.proposal_analysis.schemas import ProposalAnalysisInput
from app.workflows.runtime_factory import DynamicAssessmentWorkflowExecutor
from app.workflows.state import AssessmentWorkflowState, WorkflowStatus


class FakeExecutor:
    """Executor returned by the fake runtime factory."""

    def __init__(self) -> None:
        self.received_states: list[AssessmentWorkflowState] = []

    async def execute(
        self,
        state: AssessmentWorkflowState,
    ) -> AssessmentWorkflowState:
        """Return a deterministic completed state."""

        self.received_states.append(state.model_copy(deep=True))
        return state.model_copy(
            update={
                "status": WorkflowStatus.COMPLETED,
                "human_review_required": True,
                "human_review_reason": ("Final business review remains human-owned."),
            },
            deep=True,
        )


class FakeRuntimeFactory:
    """Record the assessment used to create the runtime."""

    def __init__(self, executor: FakeExecutor) -> None:
        self.executor = executor
        self.received_assessment_ids: list[str] = []

    async def create_executor(self, assessment_id: str) -> FakeExecutor:
        """Return the configured fake executor."""

        self.received_assessment_ids.append(assessment_id)
        return self.executor


def create_state(
    assessment_id: str = "assessment-001",
) -> AssessmentWorkflowState:
    """Create a valid minimal workflow state."""

    return AssessmentWorkflowState(
        assessment_id=assessment_id,
        proposal_document_id="proposal-001",
        orchestrator_input=OrchestratorInput(
            assessment_id=assessment_id,
            proposal_document_id="proposal-001",
            vendor_research_required=False,
            report_required=False,
            human_review_required=True,
        ),
        proposal_analysis_input=ProposalAnalysisInput(
            assessment_id=assessment_id,
            proposal_document_id="proposal-001",
            analysis_objectives=["delivery timeline"],
        ),
        maximum_steps=12,
        maximum_retries=2,
        human_review_required=True,
    )


@pytest.mark.asyncio
async def test_dynamic_executor_builds_runtime_for_state_assessment() -> None:
    fake_executor = FakeExecutor()
    factory = FakeRuntimeFactory(fake_executor)
    dynamic_executor = DynamicAssessmentWorkflowExecutor(factory)

    result = await dynamic_executor.execute(create_state())

    assert factory.received_assessment_ids == ["assessment-001"]
    assert result.status is WorkflowStatus.COMPLETED
    assert result.human_review_required is True
    assert len(fake_executor.received_states) == 1


@pytest.mark.asyncio
async def test_dynamic_executor_passes_a_deep_copy() -> None:
    fake_executor = FakeExecutor()
    factory = FakeRuntimeFactory(fake_executor)
    dynamic_executor = DynamicAssessmentWorkflowExecutor(factory)
    state = create_state()

    await dynamic_executor.execute(state)

    received = fake_executor.received_states[0]
    assert received == state
    assert received is not state


@pytest.mark.asyncio
async def test_dynamic_executor_does_not_reuse_assessment_identity() -> None:
    fake_executor = FakeExecutor()
    factory = FakeRuntimeFactory(fake_executor)
    dynamic_executor = DynamicAssessmentWorkflowExecutor(factory)

    await dynamic_executor.execute(create_state("assessment-001"))
    await dynamic_executor.execute(create_state("assessment-002"))

    assert factory.received_assessment_ids == [
        "assessment-001",
        "assessment-002",
    ]
