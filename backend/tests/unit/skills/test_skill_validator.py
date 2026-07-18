import pytest

from app.core.exceptions import (
    SkillDependencyError,
    SkillRuntimeValidationError,
)
from app.skills.factory import (
    create_default_skill_registry,
)
from app.skills.registry import SkillRegistry
from app.skills.runtime import (
    validate_default_skill_runtime,
)
from app.skills.schemas import SkillDefinition
from app.skills.validator import SkillRuntimeValidator


def create_test_skill(
    *,
    name: str = "test-skill",
    owning_agent: str = "test-agent",
    capabilities: list[str] | None = None,
    required_tools: list[str] | None = None,
    optional_tools: list[str] | None = None,
    depends_on_skills: list[str] | None = None,
    evaluator_names: list[str] | None = None,
    version: str = "1.0.0",
    maximum_tool_calls: int = 2,
) -> SkillDefinition:
    return SkillDefinition(
        name=name,
        version=version,
        description="Test skill definition.",
        owning_agent=owning_agent,
        capabilities=capabilities
        or [
            f"{name}-capability",
        ],
        required_tools=required_tools or [],
        optional_tools=optional_tools or [],
        input_schema_name="TestInput",
        output_schema_name="TestOutput",
        depends_on_skills=depends_on_skills or [],
        evaluator_names=evaluator_names or [],
        maximum_tool_calls=maximum_tool_calls,
        human_review_required=True,
    )


def test_validate_default_skill_runtime() -> None:
    registry = validate_default_skill_runtime()

    assert registry.skill_count == 3


def test_validate_existing_registry() -> None:
    registry = create_default_skill_registry()

    validated_registry = validate_default_skill_runtime(
        registry,
    )

    assert validated_registry is registry


def test_reject_unknown_skill_dependency() -> None:
    registry = SkillRegistry()
    registry.register(
        create_test_skill(
            depends_on_skills=[
                "missing-skill",
            ],
        )
    )

    validator = SkillRuntimeValidator()

    with pytest.raises(
        SkillDependencyError,
        match="unknown dependencies",
    ):
        validator.validate_dependencies(
            registry,
        )


def test_reject_circular_skill_dependencies() -> None:
    registry = SkillRegistry()

    registry.register(
        create_test_skill(
            name="skill-a",
            capabilities=[
                "capability-a",
            ],
            depends_on_skills=[
                "skill-b",
            ],
        )
    )
    registry.register(
        create_test_skill(
            name="skill-b",
            capabilities=[
                "capability-b",
            ],
            depends_on_skills=[
                "skill-c",
            ],
        )
    )
    registry.register(
        create_test_skill(
            name="skill-c",
            capabilities=[
                "capability-c",
            ],
            depends_on_skills=[
                "skill-a",
            ],
        )
    )

    validator = SkillRuntimeValidator()

    with pytest.raises(
        SkillDependencyError,
        match="Circular skill dependency",
    ):
        validator.validate_circular_dependencies(
            registry,
        )


def test_accept_acyclic_skill_dependencies() -> None:
    registry = SkillRegistry()

    registry.register(
        create_test_skill(
            name="skill-a",
            capabilities=[
                "capability-a",
            ],
        )
    )
    registry.register(
        create_test_skill(
            name="skill-b",
            capabilities=[
                "capability-b",
            ],
            depends_on_skills=[
                "skill-a",
            ],
        )
    )

    validator = SkillRuntimeValidator()

    validator.validate_dependencies(registry)
    validator.validate_circular_dependencies(
        registry,
    )


def test_reject_unknown_owning_agent() -> None:
    definition = create_test_skill()

    validator = SkillRuntimeValidator()

    with pytest.raises(
        SkillRuntimeValidationError,
        match="unknown owning agent",
    ):
        validator.validate_agent_tools(
            definition=definition,
            allowed_tools_by_agent={},
        )


def test_reject_unauthorized_declared_tool() -> None:
    definition = create_test_skill(
        required_tools=[
            "search_evidence",
        ],
        optional_tools=[
            "delete_database",
        ],
    )

    validator = SkillRuntimeValidator()

    with pytest.raises(
        SkillRuntimeValidationError,
        match="outside the policy",
    ):
        validator.validate_agent_tools(
            definition=definition,
            allowed_tools_by_agent={
                "test-agent": ("search_evidence",),
            },
        )


def test_accept_authorized_declared_tools() -> None:
    definition = create_test_skill(
        required_tools=[
            "search_evidence",
        ],
        optional_tools=[
            "get_document_page",
        ],
    )

    validator = SkillRuntimeValidator()

    validator.validate_agent_tools(
        definition=definition,
        allowed_tools_by_agent={
            "test-agent": (
                "search_evidence",
                "get_document_page",
            ),
        },
    )


def test_reject_unknown_evaluator() -> None:
    definition = create_test_skill(
        evaluator_names=[
            "missing-evaluator",
        ],
    )

    validator = SkillRuntimeValidator()

    with pytest.raises(
        SkillRuntimeValidationError,
        match="unknown evaluators",
    ):
        validator.validate_evaluators(
            definition=definition,
            evaluator_names_by_agent={
                "test-agent": ("known-evaluator",),
            },
        )


def test_reject_instruction_version_mismatch() -> None:
    definition = create_test_skill(
        version="2.0.0",
    )

    validator = SkillRuntimeValidator()

    with pytest.raises(
        SkillRuntimeValidationError,
        match="instruction version",
    ):
        validator.validate_instruction_version(
            definition=definition,
            instruction_versions_by_agent={
                "test-agent": "1.0.0",
            },
        )


def test_reject_maximum_tool_call_mismatch() -> None:
    definition = create_test_skill(
        maximum_tool_calls=2,
    )

    validator = SkillRuntimeValidator()

    with pytest.raises(
        SkillRuntimeValidationError,
        match="configured for 5",
    ):
        validator.validate_maximum_tool_calls(
            definition=definition,
            maximum_tool_calls_by_agent={
                "test-agent": 5,
            },
        )
