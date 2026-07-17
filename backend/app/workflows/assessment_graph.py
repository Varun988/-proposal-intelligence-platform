from typing import Any

from langgraph.graph import END, START, StateGraph

from app.evaluation.runner import AgentEvaluationRunner
from app.workflows.nodes import (
    AssessmentWorkflowNodes,
    OrchestratorAgentProtocol,
    ProposalAnalysisAgentProtocol,
)
from app.workflows.state import AssessmentWorkflowState


def create_assessment_graph(
    orchestrator_agent: OrchestratorAgentProtocol,
    proposal_analysis_agent: ProposalAnalysisAgentProtocol,
    evaluation_runner: AgentEvaluationRunner,
) -> Any:
    """Create and compile the controlled assessment workflow."""

    nodes = AssessmentWorkflowNodes(
        orchestrator_agent=orchestrator_agent,
        proposal_analysis_agent=proposal_analysis_agent,
        evaluation_runner=evaluation_runner,
    )

    graph = StateGraph(AssessmentWorkflowState)

    graph.add_node("initialize_workflow", nodes.initialize_workflow)
    graph.add_node("create_orchestration_plan", nodes.create_orchestration_plan)
    graph.add_node("run_proposal_analysis", nodes.run_proposal_analysis)
    graph.add_node("evaluate_proposal_analysis", nodes.evaluate_proposal_analysis)
    graph.add_node("request_human_review", nodes.request_human_review)
    graph.add_node("mark_ready_for_next_agent", nodes.mark_ready_for_next_agent)

    graph.add_edge(START, "initialize_workflow")
    graph.add_edge("initialize_workflow", "create_orchestration_plan")

    graph.add_conditional_edges(
        "create_orchestration_plan",
        nodes.route_after_orchestration,
        {
            "proposal_analysis": "run_proposal_analysis",
            "human_review": "request_human_review",
        },
    )

    graph.add_conditional_edges(
        "run_proposal_analysis",
        nodes.route_after_proposal_analysis,
        {
            "evaluation": "evaluate_proposal_analysis",
            "human_review": "request_human_review",
        },
    )

    graph.add_conditional_edges(
        "evaluate_proposal_analysis",
        nodes.route_after_evaluation,
        {
            "next_agent": "mark_ready_for_next_agent",
            "human_review": "request_human_review",
        },
    )

    graph.add_edge("request_human_review", END)
    graph.add_edge("mark_ready_for_next_agent", END)

    return graph.compile()
