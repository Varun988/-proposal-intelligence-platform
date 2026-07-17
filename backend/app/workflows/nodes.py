from typing import Protocol

from app.agents.orchestrator.schemas import (
    OrchestratorExecution,
    OrchestratorInput,
    SpecialistAgentName,
)
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
from app.agents.vendor_research.schemas import (
    VendorResearchExecution,
    VendorResearchInput,
)


class OrchestratorAgentProtocol(Protocol):
    """Minimum Orchestrator Agent interface required by workflow."""

    def create_plan(
        self,
        orchestrator_input: OrchestratorInput,
    ) -> OrchestratorExecution:
        """Create a bounded specialist-agent execution plan."""


class ProposalAnalysisAgentProtocol(Protocol):
    """Minimum Proposal Analysis Agent interface required by workflow."""

    async def analyze(
        self,
        analysis_input: ProposalAnalysisInput,
    ) -> ProposalAnalysisExecution:
        """Run proposal analysis."""


class VendorResearchAgentProtocol(Protocol):
    """Minimum Vendor Research Agent interface required by workflow."""

    async def research(
        self,
        research_input: VendorResearchInput,
    ) -> VendorResearchExecution:
        """Run approved-source vendor research."""


class AssessmentWorkflowNodes:
    """Nodes used by the controlled assessment workflow."""

    def __init__(
        self,
        orchestrator_agent: OrchestratorAgentProtocol,
        proposal_analysis_agent: ProposalAnalysisAgentProtocol,
        proposal_evaluation_runner: AgentEvaluationRunner,
        vendor_research_agent: (VendorResearchAgentProtocol | None) = None,
        vendor_evaluation_runner: (AgentEvaluationRunner | None) = None,
    ) -> None:
        self._orchestrator_agent = orchestrator_agent
        self._proposal_analysis_agent = proposal_analysis_agent
        self._proposal_evaluation_runner = proposal_evaluation_runner
        self._vendor_research_agent = vendor_research_agent
        self._vendor_evaluation_runner = vendor_evaluation_runner

    def initialize_workflow(
        self,
        state: AssessmentWorkflowState,
    ) -> dict[str, object]:
        """Initialize workflow state and route to orchestration."""

        if state.step_limit_reached:
            return self._create_step_limit_failure(state, "initialize_workflow")

        event = WorkflowEvent(
            event_type=WorkflowEventType.STATUS_CHANGED,
            status=WorkflowStatus.ORCHESTRATION_PENDING,
            message=("Assessment workflow initialized and orchestration planning is pending."),
            metadata={"previous_status": state.status.value},
        )

        return {
            "status": WorkflowStatus.ORCHESTRATION_PENDING,
            "next_route": WorkflowRoute.RUN_ORCHESTRATION,
            "current_step": state.current_step + 1,
            "events": [*state.events, event],
        }

    def create_orchestration_plan(
        self,
        state: AssessmentWorkflowState,
    ) -> dict[str, object]:
        """Create and validate the specialist-agent execution plan."""

        if state.step_limit_reached:
            return self._create_step_limit_failure(
                state,
                "create_orchestration_plan",
            )

        started_event = WorkflowEvent(
            event_type=WorkflowEventType.ORCHESTRATION_STARTED,
            status=WorkflowStatus.ORCHESTRATION_RUNNING,
            message="Orchestrator planning started.",
            agent_name="orchestrator",
        )

        try:
            execution = self._orchestrator_agent.create_plan(
                state.orchestrator_input,
            )
            self._validate_orchestration_execution(state, execution)
        except Exception as error:
            error_message = f"Orchestrator planning failed: {type(error).__name__}."
            failure_event = WorkflowEvent(
                event_type=WorkflowEventType.WORKFLOW_FAILED,
                status=WorkflowStatus.HUMAN_REVIEW_REQUIRED,
                message=error_message,
                agent_name="orchestrator",
                metadata={"error_type": type(error).__name__},
            )
            return {
                "status": WorkflowStatus.HUMAN_REVIEW_REQUIRED,
                "next_route": WorkflowRoute.REQUIRE_HUMAN_REVIEW,
                "human_review_required": True,
                "human_review_reason": error_message,
                "current_step": state.current_step + 1,
                "errors": [*state.errors, error_message],
                "agent_execution_records": [
                    *state.agent_execution_records,
                    AgentExecutionRecord(
                        agent_name="orchestrator",
                        succeeded=False,
                        tool_call_count=0,
                        execution_time_ms=0.0,
                        instruction_version="1.0.0",
                        error_message=error_message,
                    ),
                ],
                "events": [*state.events, started_event, failure_event],
            }

        completed_event = WorkflowEvent(
            event_type=WorkflowEventType.ORCHESTRATION_COMPLETED,
            status=WorkflowStatus.ORCHESTRATION_COMPLETED,
            message="Orchestrator created a validated specialist-agent plan.",
            agent_name="orchestrator",
            metadata={
                "task_count": execution.plan.task_count,
                "planner_version": execution.planner_version,
            },
        )

        return {
            "status": WorkflowStatus.ORCHESTRATION_COMPLETED,
            "next_route": WorkflowRoute.RUN_PROPOSAL_ANALYSIS,
            "orchestrator_execution": execution,
            "maximum_steps": execution.plan.maximum_steps,
            "current_step": state.current_step + 1,
            "agent_execution_records": [
                *state.agent_execution_records,
                AgentExecutionRecord(
                    agent_name="orchestrator",
                    succeeded=True,
                    tool_call_count=0,
                    execution_time_ms=execution.execution_time_ms,
                    instruction_version=execution.planner_version,
                ),
            ],
            "completed_agents": [*state.completed_agents, "orchestrator"],
            "events": [*state.events, started_event, completed_event],
        }

    async def run_proposal_analysis(
        self,
        state: AssessmentWorkflowState,
    ) -> dict[str, object]:
        """Execute the Proposal Analysis Agent."""

        if state.step_limit_reached:
            return self._create_step_limit_failure(state, "run_proposal_analysis")

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
            error_message = f"Proposal Analysis Agent execution failed: {type(error).__name__}."
            failure_event = WorkflowEvent(
                event_type=WorkflowEventType.WORKFLOW_FAILED,
                status=WorkflowStatus.HUMAN_REVIEW_REQUIRED,
                message=error_message,
                agent_name="proposal-analysis",
                metadata={"error_type": type(error).__name__},
            )
            return {
                "status": WorkflowStatus.HUMAN_REVIEW_REQUIRED,
                "next_route": WorkflowRoute.REQUIRE_HUMAN_REVIEW,
                "current_step": state.current_step + 1,
                "human_review_required": True,
                "human_review_reason": error_message,
                "errors": [*state.errors, error_message],
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
                "events": [*state.events, started_event, failure_event],
            }

        completed_event = WorkflowEvent(
            event_type=WorkflowEventType.AGENT_COMPLETED,
            status=WorkflowStatus.PROPOSAL_ANALYSIS_COMPLETED,
            message="Proposal Analysis Agent execution completed.",
            agent_name="proposal-analysis",
            metadata={"tool_call_count": execution.tool_call_count},
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
                    execution_time_ms=execution.total_execution_time_ms,
                    instruction_version=execution.instruction_version,
                ),
            ],
            "completed_agents": [*state.completed_agents, "proposal-analysis"],
            "events": [*state.events, started_event, completed_event],
        }

    def evaluate_proposal_analysis(
        self,
        state: AssessmentWorkflowState,
    ) -> dict[str, object]:
        """Evaluate the Proposal Analysis Agent execution."""

        if state.step_limit_reached:
            return self._create_step_limit_failure(
                state,
                "evaluate_proposal_analysis",
            )

        execution = state.proposal_analysis_execution
        if execution is None:
            return self._create_human_review_update(
                state,
                "Proposal analysis evaluation cannot run because the agent execution is unavailable.",
                WorkflowEventType.WORKFLOW_FAILED,
            )

        started_event = WorkflowEvent(
            event_type=WorkflowEventType.EVALUATION_STARTED,
            status=WorkflowStatus.EVALUATION_RUNNING,
            message="Proposal analysis evaluation started.",
            agent_name="proposal-analysis",
        )

        try:
            report = self._proposal_evaluation_runner.run(
                target=execution,
                assessment_id=state.assessment_id,
                agent_instruction_version=execution.instruction_version,
            )
        except Exception as error:
            reason = f"Proposal analysis evaluation failed: {type(error).__name__}."
            update = self._create_human_review_update(
                state,
                reason,
                WorkflowEventType.WORKFLOW_FAILED,
            )
            update["events"] = [
                *state.events,
                started_event,
                *update["events"][len(state.events) :],
            ]
            return update

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
                    blocking_gate_failure_count=report.blocking_gate_failure_count,
                ),
            ],
            "events": [*state.events, started_event, completed_event],
        }

    def request_human_review(
        self,
        state: AssessmentWorkflowState,
    ) -> dict[str, object]:
        """Route the workflow to human review."""

        reason = state.human_review_reason or self._build_evaluation_failure_reason(state)
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
            "events": [*state.events, event],
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
                "Proposal analysis passed its release gates and the workflow is ready for the next agent."
            ),
            agent_name="proposal-analysis",
        )
        return {
            "status": WorkflowStatus.READY_FOR_NEXT_AGENT,
            "next_route": None,
            "human_review_required": False,
            "human_review_reason": None,
            "current_step": state.current_step + 1,
            "events": [*state.events, event],
        }

    @staticmethod
    def route_after_orchestration(state: AssessmentWorkflowState) -> str:
        """Route a valid plan to analysis or failure to review."""

        if (
            state.orchestrator_execution is None
            or state.human_review_required
            or state.next_route is WorkflowRoute.REQUIRE_HUMAN_REVIEW
        ):
            return "human_review"
        return "proposal_analysis"

    @staticmethod
    def route_after_proposal_analysis(state: AssessmentWorkflowState) -> str:
        """Choose evaluation or human review after agent execution."""

        if (
            state.proposal_analysis_execution is None
            or state.human_review_required
            or state.next_route is WorkflowRoute.REQUIRE_HUMAN_REVIEW
        ):
            return "human_review"
        return "evaluation"

    @staticmethod
    def route_after_evaluation(
        state: AssessmentWorkflowState,
    ) -> str:
        """Route after Proposal Analysis evaluation."""

        if not state.proposal_analysis_passed:
            return "human_review"

        if state.vendor_research_planned:
            return "vendor_research"

        return "next_agent"

    @staticmethod
    def _validate_orchestration_execution(
        state: AssessmentWorkflowState,
        execution: OrchestratorExecution,
    ) -> None:
        """Validate identity and mandatory plan tasks."""

        if execution.plan.assessment_id != state.assessment_id:
            raise ValueError("Orchestration plan assessment ID does not match workflow state.")

        planned_agents = {task.agent_name for task in execution.plan.tasks}
        if SpecialistAgentName.PROPOSAL_ANALYSIS not in planned_agents:
            raise ValueError(
                "Orchestration plan does not contain the mandatory Proposal Analysis Agent task."
            )

    @staticmethod
    def _build_evaluation_failure_reason(state: AssessmentWorkflowState) -> str:
        report = state.proposal_analysis_evaluation
        if report is None:
            return "Human review is required because no valid proposal analysis evaluation report is available."
        return (
            "Human review is required because proposal analysis failed "
            f"{report.blocking_gate_failure_count} blocking evaluation gate(s)."
        )

    @staticmethod
    def _create_step_limit_failure(
        state: AssessmentWorkflowState,
        node_name: str,
    ) -> dict[str, object]:
        reason = f"Workflow step limit reached before executing '{node_name}'."
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
            "errors": [*state.errors, reason],
            "events": [*state.events, event],
        }

    @staticmethod
    def _create_human_review_update(
        state: AssessmentWorkflowState,
        reason: str,
        event_type: WorkflowEventType,
    ) -> dict[str, object]:
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
            "errors": [*state.errors, reason],
            "events": [*state.events, event],
        }

    async def run_vendor_research(
        self,
        state: AssessmentWorkflowState,
    ) -> dict[str, object]:
        """Execute the Vendor Research Agent."""

        if state.step_limit_reached:
            return self._create_step_limit_failure(
                state=state,
                node_name="run_vendor_research",
            )

        if self._vendor_research_agent is None:
            return self._create_human_review_update(
                state=state,
                reason=("Vendor Research is planned, but no Vendor Research Agent is configured."),
                event_type=WorkflowEventType.WORKFLOW_FAILED,
            )

        if state.vendor_research_input is None:
            return self._create_human_review_update(
                state=state,
                reason=("Vendor Research is planned, but no Vendor Research input is available."),
                event_type=WorkflowEventType.WORKFLOW_FAILED,
            )

        started_event = WorkflowEvent(
            event_type=WorkflowEventType.AGENT_STARTED,
            status=WorkflowStatus.VENDOR_RESEARCH_RUNNING,
            message="Vendor Research Agent execution started.",
            agent_name="vendor-research",
        )

        try:
            execution = await self._vendor_research_agent.research(
                state.vendor_research_input,
            )
        except Exception as error:
            error_message = f"Vendor Research Agent execution failed: {type(error).__name__}."

            failure_event = WorkflowEvent(
                event_type=WorkflowEventType.WORKFLOW_FAILED,
                status=WorkflowStatus.HUMAN_REVIEW_REQUIRED,
                message=error_message,
                agent_name="vendor-research",
                metadata={
                    "error_type": type(error).__name__,
                },
            )

            return {
                "status": WorkflowStatus.HUMAN_REVIEW_REQUIRED,
                "next_route": (WorkflowRoute.REQUIRE_HUMAN_REVIEW),
                "human_review_required": True,
                "human_review_reason": error_message,
                "current_step": state.current_step + 1,
                "errors": [
                    *state.errors,
                    error_message,
                ],
                "agent_execution_records": [
                    *state.agent_execution_records,
                    AgentExecutionRecord(
                        agent_name="vendor-research",
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
            status=WorkflowStatus.VENDOR_RESEARCH_COMPLETED,
            message="Vendor Research Agent execution completed.",
            agent_name="vendor-research",
            metadata={
                "tool_call_count": execution.tool_call_count,
                "evidence_count": len(execution.retrieved_evidence),
            },
        )

        return {
            "status": WorkflowStatus.VENDOR_EVALUATION_PENDING,
            "next_route": WorkflowRoute.RUN_VENDOR_EVALUATION,
            "vendor_research_execution": execution,
            "current_step": state.current_step + 1,
            "agent_execution_records": [
                *state.agent_execution_records,
                AgentExecutionRecord(
                    agent_name="vendor-research",
                    succeeded=True,
                    tool_call_count=execution.tool_call_count,
                    execution_time_ms=(execution.total_execution_time_ms),
                    instruction_version=(execution.instruction_version),
                ),
            ],
            "completed_agents": [
                *state.completed_agents,
                "vendor-research",
            ],
            "events": [
                *state.events,
                started_event,
                completed_event,
            ],
        }

    def evaluate_vendor_research(
        self,
        state: AssessmentWorkflowState,
    ) -> dict[str, object]:
        """Evaluate the Vendor Research Agent execution."""

        if state.step_limit_reached:
            return self._create_step_limit_failure(
                state=state,
                node_name="evaluate_vendor_research",
            )

        execution = state.vendor_research_execution

        if execution is None:
            return self._create_human_review_update(
                state=state,
                reason=(
                    "Vendor Research evaluation cannot run because "
                    "the agent execution is unavailable."
                ),
                event_type=WorkflowEventType.WORKFLOW_FAILED,
            )

        if self._vendor_evaluation_runner is None:
            return self._create_human_review_update(
                state=state,
                reason=(
                    "Vendor Research execution is available, but "
                    "no evaluation runner is configured."
                ),
                event_type=WorkflowEventType.WORKFLOW_FAILED,
            )

        started_event = WorkflowEvent(
            event_type=WorkflowEventType.EVALUATION_STARTED,
            status=WorkflowStatus.VENDOR_EVALUATION_RUNNING,
            message="Vendor Research evaluation started.",
            agent_name="vendor-research",
        )

        try:
            report = self._vendor_evaluation_runner.run(
                target=execution,
                assessment_id=state.assessment_id,
                agent_instruction_version=(execution.instruction_version),
            )
        except Exception as error:
            reason = f"Vendor Research evaluation failed: {type(error).__name__}."

            update = self._create_human_review_update(
                state=state,
                reason=reason,
                event_type=WorkflowEventType.WORKFLOW_FAILED,
            )

            update["events"] = [
                *state.events,
                started_event,
                *update["events"][len(state.events) :],
            ]

            return update

        completed_event = WorkflowEvent(
            event_type=WorkflowEventType.EVALUATION_COMPLETED,
            status=WorkflowStatus.VENDOR_EVALUATION_COMPLETED,
            message="Vendor Research evaluation completed.",
            agent_name="vendor-research",
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
            "status": WorkflowStatus.VENDOR_EVALUATION_COMPLETED,
            "next_route": next_route,
            "vendor_research_evaluation": report,
            "current_step": state.current_step + 1,
            "evaluation_records": [
                *state.evaluation_records,
                EvaluationRecord(
                    agent_name="vendor-research",
                    evaluation_id=report.evaluation_id,
                    overall_score=report.overall_score,
                    release_approved=report.release_approved,
                    blocking_gate_failure_count=(report.blocking_gate_failure_count),
                ),
            ],
            "events": [
                *state.events,
                started_event,
                completed_event,
            ],
        }

    @staticmethod
    def route_after_vendor_research(
        state: AssessmentWorkflowState,
    ) -> str:
        """Route after Vendor Research execution."""

        if (
            state.vendor_research_execution is None
            or state.human_review_required
            or state.next_route is WorkflowRoute.REQUIRE_HUMAN_REVIEW
        ):
            return "human_review"

        return "vendor_evaluation"

    @staticmethod
    def route_after_vendor_evaluation(
        state: AssessmentWorkflowState,
    ) -> str:
        """Route from Vendor Research release gates."""

        if state.vendor_research_passed:
            return "next_agent"

        return "human_review"
