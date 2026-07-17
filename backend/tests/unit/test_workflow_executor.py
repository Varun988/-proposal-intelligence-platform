import pytest
from app.workflows.executor import (
    LangGraphAssessmentWorkflowExecutor,
)

from app.agents.orchestrator.schemas import OrchestratorInput
from app.agents.proposal_analysis.schemas import (
    ProposalAnalysisInput,
)
from app.core.exceptions import AssessmentExecutionError
from app.workflows.state import (
    AssessmentWorkflowState,
    WorkflowStatus,
)


class FakeCompiledGraph:
    """Fake compiled LangGraph used by executor tests."""

    def __init__(
        self,
        result: object | None = None,
        should_fail: bool = False,
    ) -> None:
        self.result = result
        self.should_fail = should_fail
        self.received_inputs: list[object] = []

    async def ainvoke(
        self,
        input: object,
        config: object | None = None,
    ) -> object:
        """Return a configured graph result."""

        self.received_inputs.append(input)

        if self.should_fail:
            raise RuntimeError("Synthetic graph failure.")

        if self.result is not None:
            return self.result

        return input


def create_state() -> AssessmentWorkflowState:
    """Create a valid workflow state for executor tests."""

    return AssessmentWorkflowState(
        assessment_id="assessment-001",
        proposal_document_id="proposal-001",
        orchestrator_input=OrchestratorInput(
            assessment_id="assessment-001",
            proposal_document_id="proposal-001",
            vendor_research_required=False,
            report_required=False,
        ),
        proposal_analysis_input=ProposalAnalysisInput(
            assessment_id="assessment-001",
            proposal_document_id="proposal-001",
            analysis_objectives=[
                "delivery timeline",
            ],
        ),
        maximum_steps=12,
        maximum_retries=2,
        human_review_required=True,
    )


@pytest.mark.asyncio
async def test_executor_returns_validated_final_state() -> None:
    final_state = create_state().model_copy(
        update={
            "status": WorkflowStatus.COMPLETED,
            "current_step": 4,
            "human_review_required": True,
            "human_review_reason": ("Final decision remains human-owned."),
        },
        deep=True,
    )

    graph = FakeCompiledGraph(
        result=final_state.model_dump(
            mode="python",
        ),
    )

    executor = LangGraphAssessmentWorkflowExecutor(
        graph=graph,
    )

    result = await executor.execute(
        create_state(),
    )

    assert result.status is WorkflowStatus.COMPLETED
    assert result.current_step == 4
    assert result.human_review_required is True
    assert len(graph.received_inputs) == 1


@pytest.mark.asyncio
async def test_executor_passes_a_deep_copy_to_graph() -> None:
    state = create_state()
    graph = FakeCompiledGraph()

    executor = LangGraphAssessmentWorkflowExecutor(
        graph=graph,
    )

    await executor.execute(state)

    received_state = graph.received_inputs[0]

    assert isinstance(
        received_state,
        AssessmentWorkflowState,
    )
    assert received_state == state
    assert received_state is not state


@pytest.mark.asyncio
async def test_executor_wraps_graph_failure() -> None:
    executor = LangGraphAssessmentWorkflowExecutor(
        graph=FakeCompiledGraph(
            should_fail=True,
        ),
    )

    with pytest.raises(
        AssessmentExecutionError,
        match="LangGraph execution failed",
    ):
        await executor.execute(
            create_state(),
        )


@pytest.mark.asyncio
async def test_executor_rejects_invalid_result() -> None:
    executor = LangGraphAssessmentWorkflowExecutor(
        graph=FakeCompiledGraph(
            result={
                "invalid": "state",
            },
        ),
    )

    with pytest.raises(
        AssessmentExecutionError,
        match="returned an invalid state",
    ):
        await executor.execute(
            create_state(),
        )


@pytest.mark.asyncio
async def test_executor_rejects_mismatched_assessment_id() -> None:
    final_state = create_state().model_copy(
        update={
            "assessment_id": "wrong-assessment",
        },
        deep=True,
    )

    executor = LangGraphAssessmentWorkflowExecutor(
        graph=FakeCompiledGraph(
            result=final_state,
        ),
    )

    with pytest.raises(
        AssessmentExecutionError,
        match="mismatched assessment ID",
    ):
        await executor.execute(
            create_state(),
        )


@pytest.mark.asyncio
async def test_executor_rejects_mismatched_document_id() -> None:
    final_state = create_state().model_copy(
        update={
            "proposal_document_id": "wrong-proposal",
        },
        deep=True,
    )

    executor = LangGraphAssessmentWorkflowExecutor(
        graph=FakeCompiledGraph(
            result=final_state,
        ),
    )

    with pytest.raises(
        AssessmentExecutionError,
        match="mismatched proposal document ID",
    ):
        await executor.execute(
            create_state(),
        )
