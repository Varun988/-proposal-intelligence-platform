from enum import StrEnum

from pydantic import BaseModel, Field, field_validator, model_validator


class SkillStatus(StrEnum):
    """Lifecycle status of a registered skill."""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    DISABLED = "disabled"


class SkillDefinition(BaseModel):
    """Declarative definition of one governed application skill."""

    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    description: str = Field(min_length=1)
    owning_agent: str = Field(min_length=1)

    capabilities: list[str] = Field(min_length=1)

    required_tools: list[str] = Field(
        default_factory=list,
    )
    optional_tools: list[str] = Field(
        default_factory=list,
    )

    input_schema_name: str = Field(min_length=1)
    output_schema_name: str = Field(min_length=1)

    depends_on_skills: list[str] = Field(
        default_factory=list,
    )
    evaluator_names: list[str] = Field(
        default_factory=list,
    )

    maximum_tool_calls: int = Field(
        default=0,
        ge=0,
    )
    human_review_required: bool = True
    status: SkillStatus = SkillStatus.ACTIVE

    @field_validator(
        "name",
        "owning_agent",
        mode="after",
    )
    @classmethod
    def normalize_identifier(
        cls,
        value: str,
    ) -> str:
        """Normalize skill and agent identifiers to kebab case."""

        return cls._normalize_identifier(value)

    @field_validator(
        "capabilities",
        "depends_on_skills",
        "evaluator_names",
        mode="after",
    )
    @classmethod
    def normalize_identifier_collection(
        cls,
        values: list[str],
    ) -> list:
        """Normalize identifier collections while preserving order."""

        normalized_values = [cls._normalize_identifier(value) for value in values]

        if len(normalized_values) != len(set(normalized_values)):
            raise ValueError("Skill identifier collections must not contain duplicate values.")

        return normalized_values

    @field_validator(
        "required_tools",
        "optional_tools",
        mode="after",
    )
    @classmethod
    def normalize_tool_collection(
        cls,
        values: list[str],
    ) -> list:
        """Normalize executable tool names to lowercase snake case."""

        normalized_values: list[str] = []

        for value in values:
            normalized_value = value.strip().casefold().replace("-", "_").replace(" ", "_")

            while "__" in normalized_value:
                normalized_value = normalized_value.replace(
                    "__",
                    "_",
                )

            if not normalized_value:
                raise ValueError("Tool names cannot be empty.")

            normalized_values.append(
                normalized_value,
            )

        if len(normalized_values) != len(set(normalized_values)):
            raise ValueError("Skill tool collections must not contain duplicate values.")

        return normalized_values

    @model_validator(mode="after")
    def validate_definition(
        self,
    ) -> "SkillDefinition":
        """Validate tool boundaries and skill dependencies."""

        overlapping_tools = set(self.required_tools) & set(self.optional_tools)

        if overlapping_tools:
            overlapping_text = ", ".join(sorted(overlapping_tools))
            raise ValueError(f"Tools cannot be both required and optional: {overlapping_text}.")

        if self.name in self.depends_on_skills:
            raise ValueError("A skill cannot depend on itself.")

        if self.status is SkillStatus.ACTIVE and not self.human_review_required:
            raise ValueError("Active governed skills must require human review.")

        return self

    @staticmethod
    def _normalize_identifier(
        value: str,
    ) -> str:
        """Normalize a human-readable identifier to kebab case."""

        normalized_value = value.strip().casefold().replace("_", "-").replace(" ", "-")

        while "--" in normalized_value:
            normalized_value = normalized_value.replace(
                "--",
                "-",
            )

        if not normalized_value:
            raise ValueError("Skill identifiers cannot be empty.")

        return normalized_value
