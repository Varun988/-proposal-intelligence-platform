from pathlib import Path

import pytest

from app.skills.definitions import (
    PROPOSAL_ANALYSIS_SKILL,
    RISK_REPORT_SKILL,
    VENDOR_RESEARCH_SKILL,
)
from app.skills.schemas import SkillDefinition

BACKEND_ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    ("relative_path", "definition"),
    [
        (
            Path(
                "app/agents/proposal_analysis/SKILL.md",
            ),
            PROPOSAL_ANALYSIS_SKILL,
        ),
        (
            Path(
                "app/agents/vendor_research/SKILL.md",
            ),
            VENDOR_RESEARCH_SKILL,
        ),
        (
            Path(
                "app/agents/risk_report/SKILL.md",
            ),
            RISK_REPORT_SKILL,
        ),
    ],
)
def test_skill_documentation_matches_definition(
    relative_path: Path,
    definition: SkillDefinition,
) -> None:
    document_path = BACKEND_ROOT / relative_path

    assert document_path.is_file()

    document = document_path.read_text(
        encoding="utf-8",
    )

    assert f"name: {definition.name}" in document
    assert f"version: {definition.version}" in document
    assert f"owning-agent: {definition.owning_agent}" in document
    assert f"status: {definition.status.value}" in document

    for capability in definition.capabilities:
        assert f"`{capability}`" in document

    for required_tool in definition.required_tools:
        assert f"`{required_tool}`" in document

    for optional_tool in definition.optional_tools:
        assert f"`{optional_tool}`" in document

    for dependency in definition.depends_on_skills:
        assert f"`{dependency}`" in document

    for evaluator_name in definition.evaluator_names:
        assert f"`{evaluator_name}`" in document


def test_skill_documents_state_runtime_authority() -> None:
    document_paths = [
        BACKEND_ROOT / "app/agents/proposal_analysis/SKILL.md",
        BACKEND_ROOT / "app/agents/vendor_research/SKILL.md",
        BACKEND_ROOT / "app/agents/risk_report/SKILL.md",
    ]

    for document_path in document_paths:
        document = document_path.read_text(
            encoding="utf-8",
        )

        assert "Runtime Source of Truth" in document
        assert "This document is descriptive." in document
