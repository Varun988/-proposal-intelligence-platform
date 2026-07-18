import pytest

from app.core.exceptions import (
    SkillCapabilityNotFoundError,
    SkillConfigurationError,
    SkillNotFoundError,
)
from app.skills.registry import SkillRegistry
from app.skills.schemas import (
    SkillDefinition,
    SkillStatus,
)


def create_skill(
    *,
    name: str = "proposal-analysis",
    owning_agent: str = "proposal-analysis",
    capabilities: list[str] | None = None,
    status: SkillStatus = SkillStatus.ACTIVE,
) -> SkillDefinition:
    return SkillDefinition(
        name=name,
        version="1.0.0",
        description="Test skill.",
        owning_agent=owning_agent,
        capabilities=capabilities
        or [
            "proposal-summary",
        ],
        input_schema_name="TestInput",
        output_schema_name="TestOutput",
        human_review_required=True,
        status=status,
    )


def test_register_skill() -> None:
    registry = SkillRegistry()
    definition = create_skill()

    registry.register(definition)

    assert registry.skill_count == 1
    assert registry.capability_count == 1
    assert (
        registry.get(
            "proposal-analysis",
        )
        == definition
    )


def test_get_normalizes_skill_name() -> None:
    registry = SkillRegistry()
    registry.register(create_skill())

    definition = registry.get(
        "Proposal Analysis",
    )

    assert definition.name == "proposal-analysis"


def test_reject_duplicate_skill_name() -> None:
    registry = SkillRegistry()
    registry.register(create_skill())

    with pytest.raises(
        SkillConfigurationError,
        match="already registered",
    ):
        registry.register(create_skill())


def test_reject_duplicate_capability_ownership() -> None:
    registry = SkillRegistry()

    registry.register(
        create_skill(
            name="proposal-analysis",
            capabilities=[
                "proposal-summary",
            ],
        )
    )

    second_skill = create_skill(
        name="proposal-review",
        owning_agent="proposal-review",
        capabilities=[
            "proposal-summary",
        ],
    )

    with pytest.raises(
        SkillConfigurationError,
        match="already provided",
    ):
        registry.register(second_skill)


def test_find_skill_by_capability() -> None:
    registry = SkillRegistry()
    registry.register(create_skill())

    definition = registry.find_by_capability(
        "Proposal Summary",
    )

    assert definition.name == "proposal-analysis"


def test_unknown_skill_raises_not_found() -> None:
    registry = SkillRegistry()

    with pytest.raises(
        SkillNotFoundError,
        match="Unknown skill",
    ):
        registry.get("unknown-skill")


def test_unknown_capability_raises_not_found() -> None:
    registry = SkillRegistry()

    with pytest.raises(
        SkillCapabilityNotFoundError,
        match="No registered skill",
    ):
        registry.find_by_capability(
            "unknown-capability",
        )


def test_disabled_skill_does_not_resolve_capability() -> None:
    registry = SkillRegistry()

    registry.register(
        create_skill(
            status=SkillStatus.DISABLED,
        )
    )

    with pytest.raises(
        SkillCapabilityNotFoundError,
        match="currently 'disabled'",
    ):
        registry.find_by_capability(
            "proposal-summary",
        )


def test_get_definitions_for_agent() -> None:
    registry = SkillRegistry()

    registry.register(
        create_skill(
            name="proposal-summary",
            capabilities=[
                "proposal-summary",
            ],
        )
    )
    registry.register(
        create_skill(
            name="requirement-mapping",
            capabilities=[
                "requirement-mapping",
            ],
        )
    )
    registry.register(
        create_skill(
            name="vendor-research",
            owning_agent="vendor-research",
            capabilities=[
                "vendor-profile-research",
            ],
        )
    )

    definitions = registry.definitions_for_agent(
        "Proposal Analysis",
    )

    assert [definition.name for definition in definitions] == [
        "proposal-summary",
        "requirement-mapping",
    ]


def test_all_definitions_are_returned_in_stable_order() -> None:
    registry = SkillRegistry()

    registry.register(
        create_skill(
            name="vendor-research",
            owning_agent="vendor-research",
            capabilities=[
                "vendor-profile-research",
            ],
        )
    )
    registry.register(
        create_skill(
            name="proposal-analysis",
            capabilities=[
                "proposal-summary",
            ],
        )
    )

    assert [definition.name for definition in registry.all_definitions()] == [
        "proposal-analysis",
        "vendor-research",
    ]
