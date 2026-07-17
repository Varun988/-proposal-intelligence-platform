from typing import Any

from langgraph.graph import END, START, StateGraph

from app.evaluation.runner import AgentEvaluationRunner
from app.workflows.nodes import (
    AssessmentWorkflowNodes,
    OrchestratorAgentProtocol,
    ProposalAnalysisAgentProtocol,
    VendorResearchAgentProtocol,
)
from app.workflows.state import AssessmentWorkflowState


def create_assessment_graph(
    orchestrator_agent: OrchestratorAgentProtocol,
    proposal_analysis_agent: ProposalAnalysisAgentProtocol,
    proposal_evaluation_runner: AgentEvaluationRunner,
    vendor_research_agent: (VendorResearchAgentProtocol | None) = None,
    vendor_evaluation_runner: (AgentEvaluationRunner | None) = None,
) -> Any:
    """Create and compile the controlled assessment workflow."""

    nodes = AssessmentWorkflowNodes(
        orchestrator_agent=orchestrator_agent,
        proposal_analysis_agent=proposal_analysis_agent,
        proposal_evaluation_runner=(proposal_evaluation_runner),
        vendor_research_agent=vendor_research_agent,
        vendor_evaluation_runner=vendor_evaluation_runner,
    )

    graph = StateGraph(AssessmentWorkflowState)

    graph.add_node("initialize_workflow", nodes.initialize_workflow)
    graph.add_node("create_orchestration_plan", nodes.create_orchestration_plan)
    graph.add_node("run_proposal_analysis", nodes.run_proposal_analysis)
    graph.add_node("evaluate_proposal_analysis", nodes.evaluate_proposal_analysis)
    graph.add_node("request_human_review", nodes.request_human_review)
    graph.add_node("mark_ready_for_next_agent", nodes.mark_ready_for_next_agent)
    graph.add_node(
        "run_vendor_research",
        nodes.run_vendor_research,
    )
    graph.add_node(
        "evaluate_vendor_research",
        nodes.evaluate_vendor_research,
    )

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
            "vendor_research": "run_vendor_research",
            "next_agent": "mark_ready_for_next_agent",
            "human_review": "request_human_review",
        },
    )

    graph.add_conditional_edges(
        "run_vendor_research",
        nodes.route_after_vendor_research,
        {
            "vendor_evaluation": "evaluate_vendor_research",
            "human_review": "request_human_review",
        },
    )

    graph.add_conditional_edges(
        "evaluate_vendor_research",
        nodes.route_after_vendor_evaluation,
        {
            "next_agent": "mark_ready_for_next_agent",
            "human_review": "request_human_review",
        },
    )

    graph.add_edge("request_human_review", END)
    graph.add_edge("mark_ready_for_next_agent", END)

    return graph.compile()
