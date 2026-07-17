import pytest
from pydantic import ValidationError

from app.agents.orchestrator.schemas import (
    OrchestrationPlan,
    OrchestrationTask,
    OrchestratorInput,
    SpecialistAgentName,
)


def create_task(
    task_id: str,
    depends_on: list[str] | None = None,
) -> OrchestrationTask:
    """Create a synthetic orchestration task."""

    return OrchestrationTask(
        task_id=task_id,
        agent_name=SpecialistAgentName.PROPOSAL_ANALYSIS,
        objective="Analyze proposal evidence.",
        depends_on=depends_on or [],
    )


def test_orchestrator_input_has_mvp_defaults() -> None:
    orchestrator_input = OrchestratorInput(
        assessment_id="assessment-001",
        proposal_document_id="proposal-001",
    )

    assert orchestrator_input.vendor_research_required is True
    assert orchestrator_input.report_required is True
    assert orchestrator_input.human_review_required is True
    assert "proposal_analysis" in (orchestrator_input.requested_capabilities)


def test_plan_accepts_valid_dependencies() -> None:
    plan = OrchestrationPlan(
        assessment_id="assessment-001",
        tasks=[
            create_task(
                "proposal-analysis-task",
            ),
            create_task(
                "vendor-research-task",
                depends_on=[
                    "proposal-analysis-task",
                ],
            ),
        ],
    )

    assert plan.task_count == 2
    assert plan.required_task_count == 2


def test_plan_rejects_duplicate_task_ids() -> None:
    with pytest.raises(
        ValidationError,
        match="task IDs must be unique",
    ):
        OrchestrationPlan(
            assessment_id="assessment-001",
            tasks=[
                create_task("duplicate-task"),
                create_task("duplicate-task"),
            ],
        )


def test_plan_rejects_unknown_dependency() -> None:
    with pytest.raises(
        ValidationError,
        match="unknown dependencies",
    ):
        OrchestrationPlan(
            assessment_id="assessment-001",
            tasks=[
                create_task(
                    "proposal-analysis-task",
                    depends_on=[
                        "missing-task",
                    ],
                )
            ],
        )


def test_plan_rejects_self_dependency() -> None:
    with pytest.raises(
        ValidationError,
        match="cannot depend on itself",
    ):
        OrchestrationPlan(
            assessment_id="assessment-001",
            tasks=[
                create_task(
                    "proposal-analysis-task",
                    depends_on=[
                        "proposal-analysis-task",
                    ],
                )
            ],
        )
