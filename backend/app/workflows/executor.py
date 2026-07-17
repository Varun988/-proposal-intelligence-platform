from typing import Protocol

from app.core.exceptions import AssessmentExecutionError
from app.workflows.state import AssessmentWorkflowState


class CompiledAssessmentGraphProtocol(Protocol):
    """Minimum compiled LangGraph interface used by the executor."""

    async def ainvoke(
        self,
        input: object,
        config: object | None = None,
    ) -> object:
        """Execute the compiled assessment graph."""


class LangGraphAssessmentWorkflowExecutor:
    """Execute an assessment using a compiled LangGraph."""

    def __init__(
        self,
        graph: CompiledAssessmentGraphProtocol,
    ) -> None:
        self._graph = graph

    async def execute(
        self,
        state: AssessmentWorkflowState,
    ) -> AssessmentWorkflowState:
        """Execute the graph and validate its final state."""

        try:
            result = await self._graph.ainvoke(
                state.model_copy(deep=True),
            )
        except Exception as error:
            raise AssessmentExecutionError("The assessment LangGraph execution failed.") from error

        result_assessment_id = self._read_identity(
            result=result,
            field_name="assessment_id",
        )

        if (
            result_assessment_id is not None
            and result_assessment_id
            != state.assessment_id
        ):
            raise AssessmentExecutionError(
                "The assessment LangGraph returned a mismatched "
                "assessment ID."
            )

        result_proposal_document_id = self._read_identity(
            result=result,
            field_name="proposal_document_id",
        )

        if (
            result_proposal_document_id is not None
            and result_proposal_document_id
            != state.proposal_document_id
        ):
            raise AssessmentExecutionError(
                "The assessment LangGraph returned a mismatched "
                "proposal document ID."
            )

        try:
            final_state = (
                AssessmentWorkflowState.model_validate(
                    result,
                )
            )
        except Exception as error:
            raise AssessmentExecutionError(
                "The assessment LangGraph returned an invalid state."
            ) from error

        if final_state.assessment_id != state.assessment_id:
            raise AssessmentExecutionError(
                "The assessment LangGraph returned a mismatched "
                "assessment ID."
            )

        if (
            final_state.proposal_document_id
            != state.proposal_document_id
        ):
            raise AssessmentExecutionError(
                "The assessment LangGraph returned a mismatched "
                "proposal document ID."
            )
        return final_state

    @staticmethod
    def _read_identity(
        result: object,
        field_name: str,
    ) -> object | None:
        """Read a top-level identity before full state validation."""

        if isinstance(result, dict):
            return result.get(field_name)

        return getattr(
            result,
            field_name,
            None,
        )