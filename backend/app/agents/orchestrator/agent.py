from time import perf_counter

from app.agents.orchestrator.policies import (
    ORCHESTRATOR_AGENT_NAME,
    ORCHESTRATOR_MAXIMUM_RETRIES_PER_TASK,
    ORCHESTRATOR_MAXIMUM_STEPS,
    ORCHESTRATOR_MAXIMUM_TASKS,
    ORCHESTRATOR_PLANNER_VERSION,
)
from app.agents.orchestrator.schemas import (
    OrchestrationPlan,
    OrchestrationPriority,
    OrchestrationTask,
    OrchestratorExecution,
    OrchestratorInput,
    SpecialistAgentName,
)
from app.core.exceptions import AgentConfigurationError


class OrchestratorAgent:
    """Create a deterministic bounded specialist-agent plan."""

    @property
    def name(self) -> str:
        """Return the Orchestrator Agent name."""

        return ORCHESTRATOR_AGENT_NAME

    @property
    def planner_version(self) -> str:
        """Return the deterministic planner version."""

        return ORCHESTRATOR_PLANNER_VERSION

    def create_plan(
        self,
        orchestrator_input: OrchestratorInput,
    ) -> OrchestratorExecution:
        """Create a bounded plan for specialist-agent execution."""

        started_at = perf_counter()

        tasks = [
            self._create_proposal_analysis_task(),
        ]

        if orchestrator_input.vendor_research_required:
            tasks.append(
                self._create_vendor_research_task(),
            )

        if orchestrator_input.report_required:
            report_dependencies = [
                "proposal-analysis-task",
            ]

            if orchestrator_input.vendor_research_required:
                report_dependencies.append(
                    "vendor-research-task",
                )

            tasks.append(
                self._create_risk_report_task(
                    dependencies=report_dependencies,
                )
            )

        if len(tasks) > ORCHESTRATOR_MAXIMUM_TASKS:
            raise AgentConfigurationError(
                "Orchestration plan exceeds the maximum "
                f"task count of {ORCHESTRATOR_MAXIMUM_TASKS}."
            )

        plan = OrchestrationPlan(
            assessment_id=orchestrator_input.assessment_id,
            tasks=tasks,
            maximum_steps=ORCHESTRATOR_MAXIMUM_STEPS,
            human_review_required=(orchestrator_input.human_review_required),
            planning_notes=[
                (
                    "Proposal analysis must pass deterministic "
                    "evaluation before downstream tasks proceed."
                ),
                ("Specialist failures and blocking evaluation failures require human review."),
            ],
        )

        return OrchestratorExecution(
            plan=plan,
            planner_version=self.planner_version,
            execution_time_ms=self._elapsed_ms(
                started_at,
            ),
        )

    @staticmethod
    def _create_proposal_analysis_task() -> OrchestrationTask:
        """Create the mandatory proposal-analysis task."""

        return OrchestrationTask(
            task_id="proposal-analysis-task",
            agent_name=(SpecialistAgentName.PROPOSAL_ANALYSIS),
            objective=(
                "Analyze proposal and RFP evidence, identify "
                "missing or contradictory information, and "
                "produce evidence-grounded findings."
            ),
            priority=OrchestrationPriority.HIGH,
            required=True,
            maximum_retries=(ORCHESTRATOR_MAXIMUM_RETRIES_PER_TASK),
        )

    @staticmethod
    def _create_vendor_research_task() -> OrchestrationTask:
        """Create the optional vendor-research task."""

        return OrchestrationTask(
            task_id="vendor-research-task",
            agent_name=(SpecialistAgentName.VENDOR_RESEARCH),
            objective=(
                "Collect and organize approved vendor evidence with source and retrieval metadata."
            ),
            priority=OrchestrationPriority.MEDIUM,
            depends_on=[
                "proposal-analysis-task",
            ],
            required=True,
            maximum_retries=(ORCHESTRATOR_MAXIMUM_RETRIES_PER_TASK),
        )

    @staticmethod
    def _create_risk_report_task(
        dependencies: list[str],
    ) -> OrchestrationTask:
        """Create the risk and report synthesis task."""

        return OrchestrationTask(
            task_id="risk-report-task",
            agent_name=SpecialistAgentName.RISK_REPORT,
            objective=(
                "Synthesize validated specialist findings into "
                "risk, mitigation, clarification, and management "
                "report outputs."
            ),
            priority=OrchestrationPriority.HIGH,
            depends_on=dependencies,
            required=True,
            maximum_retries=(ORCHESTRATOR_MAXIMUM_RETRIES_PER_TASK),
        )

    @staticmethod
    def _elapsed_ms(
        started_at: float,
    ) -> float:
        """Return elapsed execution time in milliseconds."""

        return max(
            (perf_counter() - started_at) * 1_000,
            0.0,
        )
