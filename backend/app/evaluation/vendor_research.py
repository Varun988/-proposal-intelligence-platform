from app.agents.vendor_research.policies import (
    VENDOR_RESEARCH_AGENT_NAME,
)
from app.evaluation.evaluators.vendor_citation import (
    VendorResearchCitationEvaluator,
)
from app.evaluation.evaluators.vendor_trajectory import (
    VendorResearchTrajectoryEvaluator,
)
from app.evaluation.runner import AgentEvaluationRunner
from app.evaluation.schemas import (
    EvaluationGate,
    EvaluationStatus,
)


def create_vendor_research_evaluation_runner() -> AgentEvaluationRunner:
    """Create the default Vendor Research evaluator suite."""

    return AgentEvaluationRunner(
        agent_name=VENDOR_RESEARCH_AGENT_NAME,
        evaluators=[
            VendorResearchCitationEvaluator(),
            VendorResearchTrajectoryEvaluator(),
        ],
        gates=[
            EvaluationGate(
                evaluator_name=("vendor-research-citation-evaluator"),
                minimum_score=1.0,
                required_status=EvaluationStatus.PASSED,
                blocking=True,
            ),
            EvaluationGate(
                evaluator_name=("vendor-research-trajectory-evaluator"),
                minimum_score=1.0,
                required_status=EvaluationStatus.PASSED,
                blocking=True,
            ),
        ],
    )
