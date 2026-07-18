from collections.abc import Mapping

from app.core.exceptions import (
    SkillDependencyError,
    SkillRuntimeValidationError,
)
from app.skills.registry import SkillRegistry
from app.skills.schemas import SkillDefinition


class SkillRuntimeValidator:
    """Validate skill definitions against application configuration."""

    def validate(
        self,
        *,
        skill_registry: SkillRegistry,
        allowed_tools_by_agent: Mapping[
            str,
            tuple[str, ...],
        ],
        evaluator_names_by_agent: Mapping[
            str,
            tuple[str, ...],
        ],
        instruction_versions_by_agent: Mapping[
            str,
            str,
        ],
        maximum_tool_calls_by_agent: Mapping[
            str,
            int,
        ],
    ) -> None:
        """Run all skill configuration validations."""

        self.validate_dependencies(
            skill_registry,
        )
        self.validate_circular_dependencies(
            skill_registry,
        )

        for definition in skill_registry.all_definitions():
            self.validate_agent_tools(
                definition=definition,
                allowed_tools_by_agent=(allowed_tools_by_agent),
            )
            self.validate_evaluators(
                definition=definition,
                evaluator_names_by_agent=(evaluator_names_by_agent),
            )
            self.validate_instruction_version(
                definition=definition,
                instruction_versions_by_agent=(instruction_versions_by_agent),
            )
            self.validate_maximum_tool_calls(
                definition=definition,
                maximum_tool_calls_by_agent=(maximum_tool_calls_by_agent),
            )

    @staticmethod
    def validate_dependencies(
        skill_registry: SkillRegistry,
    ) -> None:
        """Ensure all declared skill dependencies exist."""

        available_skill_names = {definition.name for definition in skill_registry.all_definitions()}

        for definition in skill_registry.all_definitions():
            missing_dependencies = set(definition.depends_on_skills) - available_skill_names

            if not missing_dependencies:
                continue

            missing_text = ", ".join(sorted(missing_dependencies))

            raise SkillDependencyError(
                f"Skill '{definition.name}' references unknown dependencies: {missing_text}."
            )

    @staticmethod
    def validate_circular_dependencies(
        skill_registry: SkillRegistry,
    ) -> None:
        """Reject direct and indirect circular dependencies."""

        definitions_by_name = {
            definition.name: definition for definition in skill_registry.all_definitions()
        }

        visited: set[str] = set()
        active_path: set[str] = set()

        def visit(
            skill_name: str,
            dependency_path: list[str],
        ) -> None:
            if skill_name in active_path:
                cycle_start = dependency_path.index(
                    skill_name,
                )
                cycle = dependency_path[cycle_start:] + [skill_name]
                cycle_text = " -> ".join(cycle)

                raise SkillDependencyError(f"Circular skill dependency detected: {cycle_text}.")

            if skill_name in visited:
                return

            definition = definitions_by_name.get(
                skill_name,
            )

            if definition is None:
                return

            active_path.add(skill_name)
            dependency_path.append(skill_name)

            for dependency_name in definition.depends_on_skills:
                visit(
                    dependency_name,
                    dependency_path,
                )

            dependency_path.pop()
            active_path.remove(skill_name)
            visited.add(skill_name)

        for registered_skill_name in sorted(definitions_by_name):
            visit(
                registered_skill_name,
                [],
            )

    @staticmethod
    def validate_agent_tools(
        *,
        definition: SkillDefinition,
        allowed_tools_by_agent: Mapping[
            str,
            tuple[str, ...],
        ],
    ) -> None:
        """Validate declared tools against agent policy."""

        allowed_tools = allowed_tools_by_agent.get(
            definition.owning_agent,
        )

        if allowed_tools is None:
            raise SkillRuntimeValidationError(
                f"Skill '{definition.name}' references "
                f"unknown owning agent "
                f"'{definition.owning_agent}'."
            )

        permitted_tool_names = set(
            allowed_tools,
        )
        declared_tool_names = {
            *definition.required_tools,
            *definition.optional_tools,
        }
        unauthorized_tools = declared_tool_names - permitted_tool_names

        if not unauthorized_tools:
            return

        unauthorized_text = ", ".join(sorted(unauthorized_tools))

        raise SkillRuntimeValidationError(
            f"Skill '{definition.name}' declares tools "
            f"outside the policy for agent "
            f"'{definition.owning_agent}': "
            f"{unauthorized_text}."
        )

    @staticmethod
    def validate_evaluators(
        *,
        definition: SkillDefinition,
        evaluator_names_by_agent: Mapping[
            str,
            tuple[str, ...],
        ],
    ) -> None:
        """Validate declared evaluators for the owning agent."""

        actual_evaluator_names = evaluator_names_by_agent.get(
            definition.owning_agent,
        )

        if actual_evaluator_names is None:
            raise SkillRuntimeValidationError(
                f"No evaluator configuration exists for "
                f"skill '{definition.name}' and agent "
                f"'{definition.owning_agent}'."
            )

        missing_evaluators = set(definition.evaluator_names) - set(actual_evaluator_names)

        if not missing_evaluators:
            return

        missing_text = ", ".join(sorted(missing_evaluators))

        raise SkillRuntimeValidationError(
            f"Skill '{definition.name}' references unknown evaluators: {missing_text}."
        )

    @staticmethod
    def validate_instruction_version(
        *,
        definition: SkillDefinition,
        instruction_versions_by_agent: Mapping[
            str,
            str,
        ],
    ) -> None:
        """Validate skill and agent instruction versions."""

        configured_version = instruction_versions_by_agent.get(
            definition.owning_agent,
        )

        if configured_version is None:
            raise SkillRuntimeValidationError(
                f"No instruction version exists for "
                f"skill '{definition.name}' and agent "
                f"'{definition.owning_agent}'."
            )

        if definition.version == configured_version:
            return

        raise SkillRuntimeValidationError(
            f"Skill '{definition.name}' has version "
            f"'{definition.version}', but agent "
            f"'{definition.owning_agent}' uses instruction "
            f"version '{configured_version}'."
        )

    @staticmethod
    def validate_maximum_tool_calls(
        *,
        definition: SkillDefinition,
        maximum_tool_calls_by_agent: Mapping[
            str,
            int,
        ],
    ) -> None:
        """Validate the skill tool limit against agent policy."""

        configured_maximum = maximum_tool_calls_by_agent.get(
            definition.owning_agent,
        )

        if configured_maximum is None:
            raise SkillRuntimeValidationError(
                f"No tool-call limit exists for skill "
                f"'{definition.name}' and agent "
                f"'{definition.owning_agent}'."
            )

        if definition.maximum_tool_calls == configured_maximum:
            return

        raise SkillRuntimeValidationError(
            f"Skill '{definition.name}' declares a maximum "
            f"of {definition.maximum_tool_calls} tool calls, "
            f"but agent '{definition.owning_agent}' is "
            f"configured for {configured_maximum}."
        )
