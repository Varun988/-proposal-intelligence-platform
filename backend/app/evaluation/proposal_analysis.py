from app.agents.proposal_analysis.policies import (
    PROPOSAL_ANALYSIS_AGENT_NAME,
)
from app.evaluation.evaluators.citation import (
    ProposalCitationEvaluator,
)
from app.evaluation.evaluators.trajectory import (
    ProposalTrajectoryEvaluator,
)
from app.evaluation.runner import AgentEvaluationRunner
from app.evaluation.schemas import (
    EvaluationGate,
    EvaluationStatus,
)


def create_proposal_analysis_evaluation_runner() -> AgentEvaluationRunner:
    """Create the default Proposal Analysis Agent evaluator suite."""

    return AgentEvaluationRunner(
        agent_name=PROPOSAL_ANALYSIS_AGENT_NAME,
        evaluators=[
            ProposalCitationEvaluator(),
            ProposalTrajectoryEvaluator(),
        ],
        gates=[
            EvaluationGate(
                evaluator_name=("proposal-citation-evaluator"),
                minimum_score=1.0,
                required_status=EvaluationStatus.PASSED,
                blocking=True,
            ),
            EvaluationGate(
                evaluator_name=("proposal-trajectory-evaluator"),
                minimum_score=1.0,
                required_status=EvaluationStatus.PASSED,
                blocking=True,
            ),
        ],
    )
