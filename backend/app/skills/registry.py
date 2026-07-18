from app.core.exceptions import (
    SkillCapabilityNotFoundError,
    SkillConfigurationError,
    SkillNotFoundError,
)
from app.skills.schemas import (
    SkillDefinition,
    SkillStatus,
)


class SkillRegistry:
    """Register and discover governed application skills."""

    def __init__(self) -> None:
        self._skills: dict[
            str,
            SkillDefinition,
        ] = {}

        self._capability_index: dict[
            str,
            str,
        ] = {}

    def register(
        self,
        definition: SkillDefinition,
    ) -> None:
        """Register one skill and its capabilities."""

        skill_name = definition.name

        if skill_name in self._skills:
            raise SkillConfigurationError(f"Skill '{skill_name}' is already registered.")

        self._validate_capability_ownership(
            definition,
        )

        self._skills[skill_name] = definition

        for capability in definition.capabilities:
            self._capability_index[capability] = skill_name

    def get(
        self,
        skill_name: str,
    ) -> SkillDefinition:
        """Return a registered skill by name."""

        normalized_name = self._normalize_identifier(
            skill_name,
        )
        definition = self._skills.get(
            normalized_name,
        )

        if definition is None:
            raise SkillNotFoundError(f"Unknown skill: '{normalized_name}'.")

        return definition

    def find_by_capability(
        self,
        capability: str,
    ) -> SkillDefinition:
        """Return the active skill providing a capability."""

        normalized_capability = self._normalize_identifier(
            capability,
        )
        skill_name = self._capability_index.get(
            normalized_capability,
        )

        if skill_name is None:
            raise SkillCapabilityNotFoundError(
                f"No registered skill provides capability '{normalized_capability}'."
            )

        definition = self.get(skill_name)

        if definition.status is not SkillStatus.ACTIVE:
            raise SkillCapabilityNotFoundError(
                f"Skill '{definition.name}' provides capability "
                f"'{normalized_capability}', but the skill is "
                f"currently '{definition.status.value}'."
            )

        return definition

    def definitions_for_agent(
        self,
        agent_name: str,
    ) -> tuple[SkillDefinition, ...]:
        """Return skills owned by one agent."""

        normalized_agent_name = self._normalize_identifier(
            agent_name,
        )

        return tuple(
            definition
            for definition in self.all_definitions()
            if definition.owning_agent == normalized_agent_name
        )

    def all_definitions(
        self,
    ) -> tuple[SkillDefinition, ...]:
        """Return all skill definitions in stable order."""

        return tuple(self._skills[skill_name] for skill_name in sorted(self._skills))

    def active_definitions(
        self,
    ) -> tuple[SkillDefinition, ...]:
        """Return active skills in stable order."""

        return tuple(
            definition
            for definition in self.all_definitions()
            if definition.status is SkillStatus.ACTIVE
        )

    def contains(
        self,
        skill_name: str,
    ) -> bool:
        """Return whether a skill is registered."""

        normalized_name = self._normalize_identifier(
            skill_name,
        )

        return normalized_name in self._skills

    @property
    def skill_count(self) -> int:
        """Return the number of registered skills."""

        return len(self._skills)

    @property
    def capability_count(self) -> int:
        """Return the number of indexed capabilities."""

        return len(self._capability_index)

    def _validate_capability_ownership(
        self,
        definition: SkillDefinition,
    ) -> None:
        """Prevent ambiguous capability ownership."""

        for capability in definition.capabilities:
            current_owner = self._capability_index.get(
                capability,
            )

            if current_owner is not None:
                raise SkillConfigurationError(
                    f"Capability '{capability}' is already provided by skill '{current_owner}'."
                )

    @staticmethod
    def _normalize_identifier(
        value: str,
    ) -> str:
        """Normalize an identifier used for registry lookup."""

        normalized_value = value.strip().casefold().replace("_", "-").replace(" ", "-")

        while "--" in normalized_value:
            normalized_value = normalized_value.replace(
                "--",
                "-",
            )

        if not normalized_value:
            raise SkillConfigurationError("Skill registry identifiers cannot be empty.")

        return normalized_value
