# Module Responsibilities

## API

`backend/app/api` contains HTTP transport logic only.

Allowed:

- request validation;
- response formatting;
- authentication context;
- invoking application services.

Not allowed:

- LLM prompts;
- RAG implementation;
- database queries;
- agent business logic.

## Agents

`backend/app/agents` contains bounded agent behavior.

Each agent should keep these concerns separate:

- instructions;
- tools;
- input and output schemas;
- execution logic.

Agents must not access provider SDKs, databases, or external services directly.

## Workflows

`backend/app/workflows` controls:

- LangGraph state;
- agent execution order;
- conditional routing;
- retry rules;
- step limits;
- human-review transitions.

## LLM

`backend/app/llm` provides a common model interface.

All agents must use this interface rather than importing Gemini or another provider directly.

## Documents

`backend/app/documents` extracts and normalizes document content.

It handles:

- PDF;
- Word;
- Excel;
- OCR;
- page references;
- table structures.

It does not perform risk analysis.

## RAG

`backend/app/rag` handles:

- chunking;
- embeddings;
- vector indexing;
- retrieval;
- evidence metadata;
- citation references.

## Services

`backend/app/services` contains reusable application and deterministic business logic.

Examples:

- assessment management;
- risk scoring;
- evidence validation;
- report assembly.

## Repositories

`backend/app/repositories` provides persistence abstractions.

Agents and API routes must not execute raw database queries.

## Integrations

`backend/app/integrations` contains adapters for external systems and information providers.

Examples:

- company registries;
- public information sources;
- future SAP Ariba integration;
- future SharePoint integration.

## Evaluation

`backend/app/evaluation` contains:

- deterministic evaluators;
- LLM evaluators;
- evaluation datasets;
- evaluation runners;
- release gates;
- regression comparisons.

## Schemas

`backend/app/schemas` defines shared Pydantic data contracts.

Modules communicate through these typed contracts instead of unstructured dictionaries.

## Core

`backend/app/core` contains:

- configuration;
- logging;
- exceptions;
- application constants;
- cross-cutting policies.

## Utils

`backend/app/utils` contains only small, generic utilities.

Business logic must not be placed in `utils`.