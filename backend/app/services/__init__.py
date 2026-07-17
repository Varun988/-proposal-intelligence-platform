"""Application service package.

Use direct imports from concrete service modules, for example::

    from app.services.assessment_service import AssessmentService
    from app.services.llm_service import LLMService

This initializer intentionally performs no eager imports to keep service-layer
dependencies acyclic.
"""
