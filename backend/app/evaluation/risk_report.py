from app.agents.risk_report.policies import (
    RISK_REPORT_AGENT_NAME,
)
from app.evaluation.evaluators.risk_report import (
    RiskReportEvaluator,
)
from app.evaluation.runner import AgentEvaluationRunner
from app.evaluation.schemas import (
    EvaluationGate,
    EvaluationStatus,
)


def create_risk_report_evaluation_runner(
) -> AgentEvaluationRunner:
    """Create the default Risk and Report evaluator suite."""

    return AgentEvaluationRunner(
        agent_name=RISK_REPORT_AGENT_NAME,
        evaluators=[
            RiskReportEvaluator(),
        ],
        gates=[
            EvaluationGate(
                evaluator_name="risk-report-evaluator",
                minimum_score=1.0,
                required_status=EvaluationStatus.PASSED,
                blocking=True,
            )
        ],
    )
    