RISK_REPORT_AGENT_NAME = "risk-report"

RISK_REPORT_INSTRUCTION_VERSION = "1.0.0"

RISK_REPORT_ALLOWED_SOURCE_AGENTS = (
    "proposal-analysis",
    "vendor-research",
)

RISK_REPORT_ALLOWED_TOOLS = (
    "get_document_page",
    "search_evidence",
)

RISK_REPORT_MAX_TOOL_CALLS = 5

RISK_REPORT_REQUIRED_SECTIONS = (
    "executive summary",
    "key strengths",
    "key risks",
    "unresolved decisions",
    "proposed conditions",
    "human actions",
)

RISK_REPORT_DECISION_DISCLAIMER = (
    "This report is decision-support material only. Final vendor "
    "approval, rejection, exception handling, and risk acceptance "
    "remain the responsibility of authorized human reviewers."
)
