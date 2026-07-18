from app.skills.factory import (
    create_default_skill_registry,
)


def test_create_default_skill_registry() -> None:
    registry = create_default_skill_registry()

    assert registry.skill_count == 3
    assert registry.contains("proposal-analysis")
    assert registry.contains("vendor-research")
    assert registry.contains("risk-report")


def test_default_registry_indexes_all_capabilities() -> None:
    registry = create_default_skill_registry()

    expected_capability_count = sum(
        len(definition.capabilities) for definition in registry.all_definitions()
    )

    assert registry.capability_count == expected_capability_count


def test_default_registry_resolves_proposal_capability() -> None:
    registry = create_default_skill_registry()

    skill = registry.find_by_capability(
        "requirement-mapping",
    )

    assert skill.name == "proposal-analysis"


def test_default_registry_resolves_vendor_capability() -> None:
    registry = create_default_skill_registry()

    skill = registry.find_by_capability(
        "vendor-security-research",
    )

    assert skill.name == "vendor-research"


def test_default_registry_resolves_report_capability() -> None:
    registry = create_default_skill_registry()

    skill = registry.find_by_capability(
        "executive-report-generation",
    )

    assert skill.name == "risk-report"


def test_default_skills_are_returned_in_stable_order() -> None:
    registry = create_default_skill_registry()

    assert [definition.name for definition in registry.all_definitions()] == [
        "proposal-analysis",
        "risk-report",
        "vendor-research",
    ]
