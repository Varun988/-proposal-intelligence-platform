from app.agents.orchestrator.agent import OrchestratorAgent
from app.agents.orchestrator.schemas import (
    OrchestratorInput,
    SpecialistAgentName,
)


def test_orchestrator_creates_complete_mvp_plan() -> None:
    agent = OrchestratorAgent()

    execution = agent.create_plan(
        OrchestratorInput(
            assessment_id="assessment-001",
            proposal_document_id="proposal-001",
            rfp_document_id="rfp-001",
        )
    )

    plan = execution.plan

    assert plan.assessment_id == "assessment-001"
    assert plan.task_count == 3
    assert execution.planner_version == "1.0.0"
    assert execution.execution_time_ms >= 0

    assert [task.agent_name for task in plan.tasks] == [
        SpecialistAgentName.PROPOSAL_ANALYSIS,
        SpecialistAgentName.VENDOR_RESEARCH,
        SpecialistAgentName.RISK_REPORT,
    ]


def test_orchestrator_creates_dependency_order() -> None:
    agent = OrchestratorAgent()

    plan = agent.create_plan(
        OrchestratorInput(
            assessment_id="assessment-001",
            proposal_document_id="proposal-001",
        )
    ).plan

    vendor_task = next(
        task for task in plan.tasks if task.agent_name is SpecialistAgentName.VENDOR_RESEARCH
    )

    risk_task = next(
        task for task in plan.tasks if task.agent_name is SpecialistAgentName.RISK_REPORT
    )

    assert vendor_task.depends_on == [
        "proposal-analysis-task",
    ]

    assert risk_task.depends_on == [
        "proposal-analysis-task",
        "vendor-research-task",
    ]


def test_orchestrator_can_skip_vendor_research() -> None:
    agent = OrchestratorAgent()

    plan = agent.create_plan(
        OrchestratorInput(
            assessment_id="assessment-001",
            proposal_document_id="proposal-001",
            vendor_research_required=False,
        )
    ).plan

    assert plan.task_count == 2

    assert [task.agent_name for task in plan.tasks] == [
        SpecialistAgentName.PROPOSAL_ANALYSIS,
        SpecialistAgentName.RISK_REPORT,
    ]

    risk_task = plan.tasks[1]

    assert risk_task.depends_on == [
        "proposal-analysis-task",
    ]


def test_orchestrator_can_create_analysis_only_plan() -> None:
    agent = OrchestratorAgent()

    plan = agent.create_plan(
        OrchestratorInput(
            assessment_id="assessment-001",
            proposal_document_id="proposal-001",
            vendor_research_required=False,
            report_required=False,
        )
    ).plan

    assert plan.task_count == 1
    assert plan.tasks[0].agent_name is SpecialistAgentName.PROPOSAL_ANALYSIS


def test_orchestrator_requires_human_review_by_default() -> None:
    agent = OrchestratorAgent()

    plan = agent.create_plan(
        OrchestratorInput(
            assessment_id="assessment-001",
            proposal_document_id="proposal-001",
        )
    ).plan

    assert plan.human_review_required is True


def test_orchestrator_exposes_identity() -> None:
    agent = OrchestratorAgent()

    assert agent.name == "orchestrator"
    assert agent.planner_version == "1.0.0"
