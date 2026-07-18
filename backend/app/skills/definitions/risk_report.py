from app.agents.risk_report.instructions import (
    RISK_REPORT_INSTRUCTION_VERSION,
)
from app.agents.risk_report.policies import (
    RISK_REPORT_AGENT_NAME,
    RISK_REPORT_MAX_TOOL_CALLS,
)
from app.skills.schemas import SkillDefinition

RISK_REPORT_SKILL = SkillDefinition(
    name="risk-report",
    version=RISK_REPORT_INSTRUCTION_VERSION,
    description=(
        "Synthesize validated specialist findings into "
        "evidence-grounded risks and decision-support reports."
    ),
    owning_agent=RISK_REPORT_AGENT_NAME,
    capabilities=[
        "risk-synthesis",
        "mitigation-generation",
        "clarification-question-generation",
        "reviewer-report-generation",
        "executive-report-generation",
    ],
    required_tools=[],
    optional_tools=[
        "search_evidence",
        "get_document_page",
    ],
    input_schema_name="RiskReportInput",
    output_schema_name="RiskReportExecution",
    depends_on_skills=[
        "proposal-analysis",
    ],
    evaluator_names=[
        "risk-report-evaluator",
    ],
    maximum_tool_calls=RISK_REPORT_MAX_TOOL_CALLS,
    human_review_required=True,
)
