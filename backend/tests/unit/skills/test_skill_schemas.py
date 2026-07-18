import pytest
from pydantic import ValidationError

from app.skills.schemas import (
    SkillDefinition,
    SkillStatus,
)


def create_skill_definition(
    **overrides: object,
) -> SkillDefinition:
    values = {
        "name": "proposal-analysis",
        "version": "1.0.0",
        "description": ("Analyze proposal evidence."),
        "owning_agent": "proposal-analysis",
        "capabilities": [
            "proposal-summary",
            "requirement-mapping",
        ],
        "required_tools": [
            "search-evidence",
        ],
        "optional_tools": [
            "get-document-page",
        ],
        "input_schema_name": ("ProposalAnalysisInput"),
        "output_schema_name": ("ProposalAnalysisExecution"),
        "depends_on_skills": [],
        "evaluator_names": [
            "proposal-citation-evaluator",
        ],
        "maximum_tool_calls": 15,
        "human_review_required": True,
        "status": SkillStatus.ACTIVE,
    }
    values.update(overrides)

    return SkillDefinition.model_validate(values)


def test_create_valid_skill_definition() -> None:
    definition = create_skill_definition()

    assert definition.name == "proposal-analysis"
    assert definition.owning_agent == "proposal-analysis"
    assert definition.maximum_tool_calls == 15
    assert definition.human_review_required is True


def test_normalize_skill_identifiers() -> None:
    definition = create_skill_definition(
        name=" Proposal_Analysis ",
        owning_agent="Proposal Analysis",
        capabilities=[
            "Proposal Summary",
            "Requirement_Mapping",
        ],
        required_tools=[
            "Search Evidence",
        ],
    )

    assert definition.name == "proposal-analysis"
    assert definition.owning_agent == "proposal-analysis"
    assert definition.capabilities == [
        "proposal-summary",
        "requirement-mapping",
    ]
    assert definition.required_tools == [
        "search_evidence",
    ]


def test_reject_duplicate_capabilities() -> None:
    with pytest.raises(
        ValidationError,
        match="duplicate values",
    ):
        create_skill_definition(
            capabilities=[
                "proposal-summary",
                "Proposal Summary",
            ],
        )


def test_reject_overlapping_tool_definitions() -> None:
    with pytest.raises(
        ValidationError,
        match="both required and optional",
    ):
        create_skill_definition(
            required_tools=[
                "search-evidence",
            ],
            optional_tools=[
                "Search Evidence",
            ],
        )


def test_reject_self_dependency() -> None:
    with pytest.raises(
        ValidationError,
        match="cannot depend on itself",
    ):
        create_skill_definition(
            depends_on_skills=[
                "proposal_analysis",
            ],
        )


def test_reject_active_skill_without_human_review() -> None:
    with pytest.raises(
        ValidationError,
        match="must require human review",
    ):
        create_skill_definition(
            status=SkillStatus.ACTIVE,
            human_review_required=False,
        )


def test_allow_disabled_skill_without_human_review() -> None:
    definition = create_skill_definition(
        status=SkillStatus.DISABLED,
        human_review_required=False,
    )

    assert definition.status is SkillStatus.DISABLED
    assert definition.human_review_required is False
