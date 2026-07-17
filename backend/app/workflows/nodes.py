from collections.abc import Awaitable
from typing import Protocol

from app.agents.proposal_analysis.schemas import (
    ProposalAnalysisExecution,
    ProposalAnalysisInput,
)
from app.evaluation.runner import AgentEvaluationRunner
from app.workflows.state import (
    AgentExecutionRecord,
    AssessmentWorkflowState,
    EvaluationRecord,
    WorkflowEvent,
    WorkflowEventType,
    WorkflowRoute,
    WorkflowStatus,
)


class ProposalAnalysisAgentProtocol(Protocol):
    """Minimum Proposal Analysis Agent interface required by workflow."""

    async def analyze(
        self,
        analysis_input: ProposalAnalysisInput,
    ) -> ProposalAnalysisExecution:
        """Run proposal analysis."""


class AssessmentWorkflowNodes:
    """Nodes used by the controlled assessment workflow."""

    def __init__(
        self,
        proposal_analysis_agent: ProposalAnalysisAgentProtocol,
        evaluation_runner: AgentEvaluationRunner,
    ) -> None:
        self._proposal_analysis_agent = proposal_analysis_agent
        self._evaluation_runner = evaluation_runner

    def initialize_workflow(
        self,
        state: AssessmentWorkflowState,
    ) -> dict[str, object]:
        """Initialize workflow state and route to proposal analysis."""

        if state.step_limit_reached:
            return self._create_step_limit_failure(
                state=state,
                node_name="initialize_workflow",
            )

        event = WorkflowEvent(
            event_type=WorkflowEventType.STATUS_CHANGED,
            status=WorkflowStatus.PROPOSAL_ANALYSIS_PENDING,
            message=(
                "Assessment workflow initialized and proposal "
                "analysis is pending."
            ),
            metadata={
                "previous_status": state.status.value,
            },
        )

        return {
            "status": WorkflowStatus.PROPOSAL_ANALYSIS_PENDING,
            "next_route": WorkflowRoute.RUN_PROPOSAL_ANALYSIS,
            "current_step": state.current_step + 1,
            "events": [
                *state.events,
                event,
            ],
        }

    async def run_proposal_analysis(
        self,
        state: AssessmentWorkflowState,
    ) -> dict[str, object]:
        """Execute the Proposal Analysis Agent."""

        if state.step_limit_reached:
            return self._create_step_limit_failure(
                state=state,
                node_name="run_proposal_analysis",
            )

        started_event = WorkflowEvent(
            event_type=WorkflowEventType.AGENT_STARTED,
            status=WorkflowStatus.PROPOSAL_ANALYSIS_RUNNING,
            message="Proposal Analysis Agent execution started.",
            agent_name="proposal-analysis",
        )

        try:
            execution = await self._proposal_analysis_agent.analyze(
                state.proposal_analysis_input,
            )
        except Exception as error:
            error_message = (
                "Proposal Analysis Agent execution failed: "
                f"{type(error).__name__}."
            )

            failure_event = WorkflowEvent(
                event_type=WorkflowEventType.WORKFLOW_FAILED,
                status=WorkflowStatus.HUMAN_REVIEW_REQUIRED,
                message=error_message,
                agent_name="proposal-analysis",
                metadata={
                    "error_type": type(error).__name__,
                },
            )

            return {
                "status": WorkflowStatus.HUMAN_REVIEW_REQUIRED,
                "next_route": WorkflowRoute.REQUIRE_HUMAN_REVIEW,
                "current_step": state.current_step + 1,
                "human_review_required": True,
                "human_review_reason": error_message,
                "errors": [
                    *state.errors,
                    error_message,
                ],
                "agent_execution_records": [
                    *state.agent_execution_records,
                    AgentExecutionRecord(
                        agent_name="proposal-analysis",
                        succeeded=False,
                        tool_call_count=0,
                        execution_time_ms=0.0,
                        instruction_version="unknown",
                        error_message=error_message,
                    ),
                ],
                "events": [
                    *state.events,
                    started_event,
                    failure_event,
                ],
            }

        completed_event = WorkflowEvent(
            event_type=WorkflowEventType.AGENT_COMPLETED,
            status=WorkflowStatus.PROPOSAL_ANALYSIS_COMPLETED,
            message=(
                "Proposal Analysis Agent execution completed."
            ),
            agent_name="proposal-analysis",
            metadata={
                "tool_call_count": execution.tool_call_count,
            },
        )

        return {
            "status": WorkflowStatus.EVALUATION_PENDING,
            "next_route": WorkflowRoute.RUN_EVALUATION,
            "proposal_analysis_execution": execution,
            "current_step": state.current_step + 1,
            "agent_execution_records": [
                *state.agent_execution_records,
                AgentExecutionRecord(
                    agent_name="proposal-analysis",
                    succeeded=True,
                    tool_call_count=execution.tool_call_count,
                    execution_time_ms=(
                        execution.total_execution_time_ms
                    ),
                    instruction_version=(
                        execution.instruction_version
                    ),
                ),
            ],
            "completed_agents": [
                *state.completed_agents,
                "proposal-analysis",
            ],
            "events": [
                *state.events,
                started_event,
                completed_event,
            ],
        }

    def evaluate_proposal_analysis(
        self,
        state: AssessmentWorkflowState,
    ) -> dict[str, object]:
        """Evaluate the Proposal Analysis Agent execution."""

        if state.step_limit_reached:
            return self._create_step_limit_failure(
                state=state,
                node_name="evaluate_proposal_analysis",
            )

        execution = state.proposal_analysis_execution

        if execution is None:
            error_message = (
                "Proposal analysis evaluation cannot run because "
                "the agent execution is unavailable."
            )

            return self._create_human_review_update(
                state=state,
                reason=error_message,
                event_type=WorkflowEventType.WORKFLOW_FAILED,
            )

        started_event = WorkflowEvent(
            event_type=WorkflowEventType.EVALUATION_STARTED,
            status=WorkflowStatus.EVALUATION_RUNNING,
            message="Proposal analysis evaluation started.",
            agent_name="proposal-analysis",
        )

        try:
            report = self._evaluation_runner.run(
                target=execution,
                assessment_id=state.assessment_id,
                agent_instruction_version=(
                    execution.instruction_version
                ),
            )
        except Exception as error:
            error_message = (
                "Proposal analysis evaluation failed: "
                f"{type(error).__name__}."
            )

            failure_update = self._create_human_review_update(
                state=state,
                reason=error_message,
                event_type=WorkflowEventType.WORKFLOW_FAILED,
            )

            failure_update["events"] = [
                *state.events,
                started_event,
                *failure_update["events"][len(state.events):],
            ]

            return failure_update

        completed_event = WorkflowEvent(
            event_type=WorkflowEventType.EVALUATION_COMPLETED,
            status=WorkflowStatus.EVALUATION_COMPLETED,
            message="Proposal analysis evaluation completed.",
            agent_name="proposal-analysis",
            metadata={
                "evaluation_id": report.evaluation_id,
                "overall_score": report.overall_score,
                "release_approved": report.release_approved,
            },
        )

        next_route = (
            WorkflowRoute.CONTINUE_TO_NEXT_AGENT
            if report.release_approved
            else WorkflowRoute.REQUIRE_HUMAN_REVIEW
        )

        return {
            "status": WorkflowStatus.EVALUATION_COMPLETED,
            "next_route": next_route,
            "proposal_analysis_evaluation": report,
            "current_step": state.current_step + 1,
            "evaluation_records": [
                *state.evaluation_records,
                EvaluationRecord(
                    agent_name="proposal-analysis",
                    evaluation_id=report.evaluation_id,
                    overall_score=report.overall_score,
                    release_approved=report.release_approved,
                    blocking_gate_failure_count=(
                        report.blocking_gate_failure_count
                    ),
                ),
            ],
            "events": [
                *state.events,
                started_event,
                completed_event,
            ],
        }

    def request_human_review(
        self,
        state: AssessmentWorkflowState,
    ) -> dict[str, object]:
        """Route the workflow to human review."""

        reason = (
            state.human_review_reason
            or self._build_evaluation_failure_reason(state)
        )

        event = WorkflowEvent(
            event_type=WorkflowEventType.HUMAN_REVIEW_REQUESTED,
            status=WorkflowStatus.HUMAN_REVIEW_REQUIRED,
            message=reason,
            agent_name="proposal-analysis",
        )

        return {
            "status": WorkflowStatus.HUMAN_REVIEW_REQUIRED,
            "next_route": None,
            "human_review_required": True,
            "human_review_reason": reason,
            "current_step": state.current_step + 1,
            "events": [
                *state.events,
                event,
            ],
        }

    def mark_ready_for_next_agent(
        self,
        state: AssessmentWorkflowState,
    ) -> dict[str, object]:
        """Mark successful proposal analysis for the next agent."""

        event = WorkflowEvent(
            event_type=WorkflowEventType.STATUS_CHANGED,
            status=WorkflowStatus.READY_FOR_NEXT_AGENT,
            message=(
                "Proposal analysis passed its release gates and "
                "the workflow is ready for the next agent."
            ),
            agent_name="proposal-analysis",
        )

        return {
            "status": WorkflowStatus.READY_FOR_NEXT_AGENT,
            "next_route": None,
            "human_review_required": False,
            "human_review_reason": None,
            "current_step": state.current_step + 1,
            "events": [
                *state.events,
                event,
            ],
        }

    @staticmethod
    def route_after_proposal_analysis(
        state: AssessmentWorkflowState,
    ) -> str:
        """Choose evaluation or human review after agent execution."""

        if (
            state.proposal_analysis_execution is None
            or state.human_review_required
            or state.next_route
            is WorkflowRoute.REQUIRE_HUMAN_REVIEW
        ):
            return "human_review"

        return "evaluation"

    @staticmethod
    def route_after_evaluation(
        state: AssessmentWorkflowState,
    ) -> str:
        """Choose the next route from evaluation release gates."""

        if state.proposal_analysis_passed:
            return "next_agent"

        return "human_review"

    @staticmethod
    def _build_evaluation_failure_reason(
        state: AssessmentWorkflowState,
    ) -> str:
        """Create a safe human-review reason from evaluation state."""

        report = state.proposal_analysis_evaluation

        if report is None:
            return (
                "Human review is required because no valid proposal "
                "analysis evaluation report is available."
            )

        return (
            "Human review is required because proposal analysis "
            f"failed {report.blocking_gate_failure_count} "
            "blocking evaluation gate(s)."
        )

    @staticmethod
    def _create_step_limit_failure(
        state: AssessmentWorkflowState,
        node_name: str,
    ) -> dict[str, object]:
        """Create a human-review update after reaching step limits."""

        reason = (
            "Workflow step limit reached before executing "
            f"'{node_name}'."
        )

        event = WorkflowEvent(
            event_type=WorkflowEventType.WORKFLOW_FAILED,
            status=WorkflowStatus.HUMAN_REVIEW_REQUIRED,
            message=reason,
            metadata={
                "node_name": node_name,
                "current_step": state.current_step,
                "maximum_steps": state.maximum_steps,
            },
        )

        return {
            "status": WorkflowStatus.HUMAN_REVIEW_REQUIRED,
            "next_route": WorkflowRoute.REQUIRE_HUMAN_REVIEW,
            "human_review_required": True,
            "human_review_reason": reason,
            "errors": [
                *state.errors,
                reason,
            ],
            "events": [
                *state.events,
                event,
            ],
        }

    @staticmethod
    def _create_human_review_update(
        state: AssessmentWorkflowState,
        reason: str,
        event_type: WorkflowEventType,
    ) -> dict[str, object]:
        """Create a normalized human-review state update."""

        event = WorkflowEvent(
            event_type=event_type,
            status=WorkflowStatus.HUMAN_REVIEW_REQUIRED,
            message=reason,
            agent_name="proposal-analysis",
        )

        return {
            "status": WorkflowStatus.HUMAN_REVIEW_REQUIRED,
            "next_route": WorkflowRoute.REQUIRE_HUMAN_REVIEW,
            "human_review_required": True,
            "human_review_reason": reason,
            "current_step": state.current_step + 1,
            "errors": [
                *state.errors,
                reason,
            ],
            "events": [
                *state.events,
                event,
            ],
        }