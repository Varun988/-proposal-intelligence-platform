from app.workflows.state import (
    AssessmentWorkflowState,
    WorkflowEvent,
    WorkflowEventType,
    WorkflowStatus,
)


class FakeAssessmentWorkflowExecutor:
    """Deterministic assessment workflow executor for API tests."""

    def __init__(
        self,
        final_status: WorkflowStatus = WorkflowStatus.COMPLETED,
        should_fail: bool = False,
    ) -> None:
        self.final_status = final_status
        self.should_fail = should_fail
        self.received_states: list[AssessmentWorkflowState] = []

    async def execute(
        self,
        state: AssessmentWorkflowState,
    ) -> AssessmentWorkflowState:
        """Return a deterministic final workflow state."""

        self.received_states.append(state.model_copy(deep=True))
        if self.should_fail:
            raise RuntimeError("Synthetic workflow execution failure.")

        human_review_reason = "Automated processing completed. Final review remains human-owned."
        event_type = WorkflowEventType.WORKFLOW_COMPLETED
        if self.final_status is WorkflowStatus.HUMAN_REVIEW_REQUIRED:
            human_review_reason = "Synthetic blocking release-gate failure."
            event_type = WorkflowEventType.HUMAN_REVIEW_REQUESTED

        event = WorkflowEvent(
            event_type=event_type,
            status=self.final_status,
            message="Synthetic assessment workflow execution completed.",
        )
        return state.model_copy(
            update={
                "status": self.final_status,
                "current_step": 10,
                "human_review_required": True,
                "human_review_reason": human_review_reason,
                "completed_agents": [
                    "orchestrator",
                    "proposal-analysis",
                    "vendor-research",
                    "risk-report",
                ],
                "events": state.events + [event],
            },
            deep=True,
        )
