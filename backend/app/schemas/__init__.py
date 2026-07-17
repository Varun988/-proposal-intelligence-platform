"""Shared schema package.

Use direct imports from concrete schema modules, for example::

    from app.schemas.assessment import AssessmentCreateRequest
    from app.schemas.llm import LLMRequest

This initializer intentionally performs no eager imports because assessment
schemas depend on agent and workflow result types.
"""
