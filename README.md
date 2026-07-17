# Proposal Intelligence & Vendor Risk Platform

> An AI-powered, evidence-grounded decision-support platform for accelerating enterprise proposal analysis, vendor due diligence, risk assessment, and multi-stage approval reporting.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Problem Statement](#problem-statement)
3. [Business Context](#business-context)
4. [Business Impact](#business-impact)
5. [Proposed Solution](#proposed-solution)
6. [Solution Objectives](#solution-objectives)
7. [Primary Users and Stakeholders](#primary-users-and-stakeholders)
8. [Key Use Cases](#key-use-cases)
9. [System Workflow](#system-workflow)
10. [Agent Architecture](#agent-architecture)
11. [Agent and LLM Evaluation](#agent-and-llm-evaluation)
12. [RAG and Knowledge Architecture](#rag-and-knowledge-architecture)
13. [Technology Stack](#technology-stack)
14. [Modular Project Architecture](#modular-project-architecture)
15. [Security and Responsible AI](#security-and-responsible-ai)
16. [Human-in-the-Loop Governance](#human-in-the-loop-governance)
17. [MVP Scope](#mvp-scope)
18. [Future Scope](#future-scope)
19. [Success Metrics](#success-metrics)
20. [Local Development Strategy](#local-development-strategy)
21. [Getting Started](#getting-started)
22. [Environment Variables](#environment-variables)
23. [Testing Strategy](#testing-strategy)
24. [Repository Guidelines](#repository-guidelines)
25. [Project Roadmap](#project-roadmap)
26. [Current Project Status](#current-project-status)
27. [Disclaimer](#disclaimer)

---

## Project Overview

Large enterprises frequently outsource implementation projects, managed services, consulting engagements, software delivery, and operational work to external service providers. Vendors submit detailed proposals containing commercial terms, project scope, delivery methodology, staffing plans, timelines, service levels, assumptions, exclusions, security responses, and contractual conditions.

Evaluating these proposals is not limited to reading the submitted documents. The client must also understand the vendor's financial stability, compliance position, security posture, delivery capability, historical performance, reputation, relevant adverse events, and alignment with internal procurement and risk policies.

The **Proposal Intelligence & Vendor Risk Platform** is designed to assist this process by combining:

- structured document extraction;
- retrieval-augmented generation, or RAG;
- controlled AI agents;
- deterministic business rules;
- evidence and citation validation;
- agent and LLM evaluation;
- human review and approval workflows;
- traceable, decision-ready report generation.

The platform is intended to act as a **decision-support system**. It does not autonomously approve or reject a vendor.

---

## Problem Statement

Enterprise proposal evaluation is commonly fragmented across procurement, finance, information security, legal, compliance, enterprise risk, and business teams.

The existing process often depends on manual activities such as:

- reading lengthy proposals, RFPs, statements of work, questionnaires, and pricing workbooks;
- locating relevant internal policies and comparison benchmarks;
- mapping vendor responses to mandatory RFP requirements;
- identifying missing, inconsistent, or non-compliant information;
- researching the vendor across multiple internal and external sources;
- reviewing financial health, security controls, regulatory exposure, and reputation;
- consolidating feedback from multiple specialist teams;
- preparing different reports for different approval stages;
- maintaining evidence, comments, exceptions, and approval history.

This creates several challenges:

1. **Long review cycles** — reviewers spend substantial time reading, comparing, and summarizing documents.
2. **Inconsistent evaluation quality** — different reviewers may apply different interpretations and levels of diligence.
3. **Fragmented evidence** — supporting information is distributed across documents, systems, emails, and external sources.
4. **Limited traceability** — management recommendations may not always be directly linked to source evidence.
5. **Delayed risk discovery** — important security, financial, compliance, or delivery concerns may be found late in the approval process.
6. **Duplicated effort** — several stakeholders may independently extract or summarize the same information.
7. **Reporting overhead** — each approval stage requires its own summary, risk view, and recommendation.
8. **Knowledge loss** — lessons from previous proposals and vendor assessments are not consistently reused.

---

## Business Context

A typical enterprise sourcing scenario may involve:

- a client organization issuing an RFP;
- multiple service providers submitting proposals;
- procurement checking commercial completeness;
- finance reviewing cost and vendor stability;
- security reviewing architecture, controls, certifications, and data handling;
- legal reviewing non-standard contract clauses;
- compliance reviewing regulatory and policy obligations;
- business owners evaluating delivery feasibility and strategic fit;
- senior management reviewing a consolidated recommendation before approval.

The system is designed to support this multi-stakeholder process while preserving accountability with designated human reviewers and approvers.

---

## Business Impact

### Expected benefits

#### Reduced proposal review time

Document extraction, requirement mapping, evidence retrieval, and report drafting can reduce the amount of repetitive manual work performed by reviewers.

#### Improved consistency

The same evaluation criteria, output schemas, risk taxonomy, evidence rules, and report structure can be applied across proposals.

#### Better evidence traceability

Material findings can be linked to the corresponding proposal page, RFP requirement, internal policy, or approved research source.

#### Earlier risk identification

Commercial, delivery, security, financial, compliance, and reputational concerns can be surfaced before later approval stages.

#### Higher reviewer productivity

Specialists can focus on judgment and exceptions instead of repeatedly searching for and summarizing information.

#### Faster management reporting

The system can generate stage-specific summaries from validated structured findings rather than recreating reports manually.

#### Reusable institutional knowledge

Previous proposal assessments, approved clauses, vendor performance records, and policy interpretations can become searchable organizational knowledge.

#### Stronger auditability

The platform can retain the model version, prompt version, retrieved evidence, generated findings, human changes, workflow events, and final approval history.

### Intended business outcome

The goal is not simply to generate reports faster. The intended outcome is to:

> Reduce proposal evaluation cycle time while maintaining or improving decision quality, evidence traceability, consistency, security, and human accountability.

---

## Proposed Solution

The proposed platform receives proposal-related documents and creates a structured, evidence-grounded assessment.

At a high level, it will:

1. accept an RFP, vendor proposal, pricing workbook, questionnaire, and supporting documents;
2. extract text, tables, document structure, and page references;
3. normalize relevant proposal information into structured schemas;
4. compare the proposal with RFP requirements;
5. retrieve applicable internal policies and historical knowledge;
6. gather vendor-related evidence from approved data sources;
7. identify risk findings and missing information;
8. validate whether findings are supported by evidence;
9. apply deterministic scoring and business rules;
10. generate reviewer-specific and management-ready reports;
11. allow users to accept, edit, reject, or escalate AI-generated findings;
12. preserve a complete audit and evaluation trail.

### Core design principle

The system follows this pattern:

```text
Deterministic workflow
        +
Specialized AI agents
        +
RAG and approved tools
        +
Deterministic rules and scoring
        +
Independent evaluation
        +
Human approval gates
```

This is intentionally different from an unrestricted autonomous-agent system.

---

## Solution Objectives

The platform aims to:

- automate repetitive proposal-review activities;
- extract structured facts from unstructured documents;
- create an RFP-to-proposal compliance matrix;
- identify missing, contradictory, or unclear information;
- retrieve relevant internal knowledge with permission-aware controls;
- support vendor research through approved sources;
- generate evidence-linked risk findings;
- produce stage-specific reports and executive summaries;
- evaluate the quality, safety, efficiency, and behavior of every agent;
- preserve human ownership of final business decisions;
- remain modular enough to replace LLM providers, data sources, and infrastructure components later.

---

## Primary Users and Stakeholders

### Procurement analysts

- initiate assessments;
- review proposal completeness;
- compare pricing and commercial terms;
- manage vendor clarification questions;
- coordinate the approval process.

### Business and delivery reviewers

- evaluate scope, methodology, staffing, assumptions, timelines, and dependencies;
- assess delivery feasibility and strategic fit.

### Information security reviewers

- evaluate security controls, data handling, hosting, certifications, incidents, and remediation requirements.

### Finance reviewers

- assess pricing, total cost of ownership, payment terms, financial stability, and financial exposure.

### Legal and compliance reviewers

- evaluate contractual deviations, regulatory obligations, privacy, data residency, liability, intellectual property, and exceptions.

### Management and executive approvers

- review consolidated risk, business value, unresolved decisions, mitigating conditions, and management recommendations.

### AI administrators and evaluators

- manage models, prompts, agent configuration, evaluation datasets, release thresholds, traces, and production-quality monitoring.

### Auditors

- inspect the evidence, model and prompt versions, system-generated findings, reviewer changes, and approval history.

---

## Key Use Cases

### 1. Proposal information extraction

Extract and normalize:

- vendor identity;
- scope and deliverables;
- timeline and milestones;
- staffing and resource model;
- pricing, currencies, and rate cards;
- SLAs and service credits;
- assumptions, dependencies, and exclusions;
- support and warranty commitments;
- payment terms;
- liability and termination clauses;
- intellectual property conditions.

### 2. RFP-to-proposal compliance mapping

For every requirement, determine whether the response is:

- compliant;
- partially compliant;
- non-compliant;
- unclear;
- not found.

Every result should include evidence references and confidence information.

### 3. Proposal completeness and contradiction detection

Identify:

- missing sections;
- conflicting dates;
- inconsistent pricing;
- unclear obligations;
- mismatches between scope, resources, timeline, and cost;
- contradictions across the main proposal and annexures.

### 4. Internal-policy retrieval

Retrieve applicable:

- procurement policies;
- security standards;
- risk thresholds;
- approved rate cards;
- clause libraries;
- previous vendor assessments;
- historical vendor-performance information.

### 5. Vendor research

Collect evidence about:

- financial health;
- compliance status;
- security posture;
- certifications;
- ownership and company records;
- previous internal performance;
- relevant adverse events;
- reputation.

The prototype must use only synthetic, public, or fully redacted information when free LLM APIs are involved.

### 6. Risk analysis

Generate evidence-based findings in categories such as:

- commercial;
- delivery;
- financial;
- security;
- compliance;
- legal;
- reputation;
- strategic fit.

### 7. Cross-proposal comparison

Compare multiple vendor proposals by:

- normalized total cost;
- mandatory-requirement compliance;
- delivery approach;
- risk profile;
- strengths and weaknesses;
- missing information;
- unresolved questions.

### 8. Report generation

Generate different outputs for:

- procurement review;
- security review;
- finance review;
- legal and compliance review;
- business-owner review;
- executive approval.

### 9. Reviewer feedback

Allow reviewers to mark a finding as:

- accepted;
- accepted with modification;
- incorrect;
- duplicate;
- insufficiently supported;
- wrong category;
- wrong severity;
- requiring further investigation.

### 10. Agent and LLM evaluation

Evaluate agent outputs, tool calls, trajectories, grounding, citations, instruction-following, safety, latency, and cost before release and during operation.

---

## System Workflow

```text
Proposal assessment created
          |
          v
Documents uploaded and classified
          |
          v
Text, tables, and page references extracted
          |
          v
Proposal and RFP indexed for retrieval
          |
          v
Proposal analysis and requirement mapping
          |
          +-----------------------------+
          |                             |
          v                             v
Internal knowledge retrieval      Vendor research
          |                             |
          +---------------+-------------+
                          |
                          v
                 Risk finding synthesis
                          |
                          v
             Evidence and citation validation
                          |
                          v
         Deterministic rules and score calculation
                          |
                          v
             Stage-specific report generation
                          |
                          v
                Human review and approval
                          |
                          v
              Auditable final assessment
```

---

## Agent Architecture

The MVP is planned with **four operational agents**.

### 1. Orchestrator Agent

Coordinates the analysis workflow.

Responsibilities:

- understand the requested assessment;
- determine which tasks are required;
- call the appropriate agents and tools;
- maintain workflow state;
- enforce maximum steps and retry limits;
- route exceptions to human review;
- prevent unauthorized actions;
- consolidate statuses without altering specialist evidence.

The Orchestrator Agent cannot approve or reject a vendor.

### 2. Proposal Analysis Agent

Analyzes proposal and RFP documents.

Responsibilities:

- extract important proposal information;
- map RFP requirements to vendor responses;
- identify missing and contradictory information;
- identify assumptions, exclusions, and dependencies;
- create structured findings with page-level evidence;
- highlight commercial and delivery concerns for further analysis.

### 3. Vendor Research Agent

Collects internal and approved external vendor evidence.

Responsibilities:

- retrieve vendor-performance history;
- collect public or approved company information;
- organize financial, security, compliance, and reputation evidence;
- distinguish confirmed facts from claims or unavailable information;
- preserve source, date, and retrieval metadata;
- detect stale or conflicting evidence.

### 4. Risk and Report Agent

Synthesizes validated findings and prepares decision-support reports.

Responsibilities:

- categorize findings;
- explain deterministic scores;
- generate risks, mitigations, and clarification questions;
- create reviewer-specific reports;
- generate an executive summary;
- clearly separate facts, analysis, uncertainty, and recommendation.

The LLM does not calculate the official score and does not make the final approval decision.

### Potential production expansion

After the MVP is evaluated, specialist responsibilities may be separated into:

- Delivery Risk Agent;
- Financial and Commercial Risk Agent;
- Security and Compliance Risk Agent;
- Evidence Validation and Report Agent.

An additional agent will be added only when it provides measurable improvements in quality, security, context isolation, tool permissions, maintainability, or parallel execution.

---

## Agent and LLM Evaluation

Evaluation is a first-class architectural component. It is not deferred until the end of development.

### Evaluation levels

#### LLM-call evaluation

Measures:

- structured-output validity;
- extraction correctness;
- instruction-following;
- groundedness;
- hallucination;
- consistency.

#### Individual-agent evaluation

Measures:

- task completion;
- correct tool selection;
- valid tool arguments;
- evidence quality;
- output-schema compliance;
- safe termination.

#### Trajectory evaluation

Examines the complete execution trace:

- actions taken;
- tool-call order;
- retrieved documents;
- state transitions;
- retries;
- loops;
- agent handoffs;
- final output.

#### End-to-end workflow evaluation

Measures:

- successful workflow completion;
- critical finding recall;
- grounded report generation;
- cross-agent consistency;
- duplicate findings;
- latency;
- number of calls;
- resource usage.

#### Safety and adversarial evaluation

Tests:

- prompt injection in uploaded documents;
- indirect prompt injection in retrieved sources;
- attempts to retrieve unauthorized information;
- confidential-data leakage;
- fabricated citations;
- manipulated tables;
- excessive loops or tool calls;
- attempts to bypass human approval.

### Evaluation methods

The project will combine:

1. **Deterministic evaluators** for schemas, exact values, citations, tool permissions, trajectories, calculations, latency, and limits.
2. **Reference-based evaluators** using human-approved expected outputs.
3. **LLM-based evaluators** for groundedness, completeness, evidence alignment, and report clarity.
4. **Human expert review** for high-impact or ambiguous cases and evaluator calibration.

### Evaluation datasets

The repository will eventually include versioned JSONL datasets for:

- component tests;
- end-to-end proposal cases;
- edge cases;
- adversarial cases;
- regression cases;
- anonymized reviewer feedback.

### Example quality gates

Initial targets will be finalized after a baseline is available, but the project intends to measure:

- critical-field extraction accuracy;
- structured-output success rate;
- critical-finding recall;
- groundedness;
- citation correctness;
- correct tool selection;
- unauthorized retrieval attempts;
- prompt-injection resistance;
- workflow completion rate;
- latency and model-call limits;
- human reviewer acceptance and correction rates.

---

## RAG and Knowledge Architecture

Retrieval-augmented generation will ground agent outputs in approved evidence.

### Suitable RAG sources

- RFPs;
- vendor proposals;
- procurement policies;
- security standards;
- approved contractual clauses;
- previous vendor assessments;
- vendor-performance reports;
- internal approval guidelines;
- public or approved vendor evidence.

### RAG is not used for

- exact arithmetic;
- official risk-score calculation;
- approval routing;
- deterministic policy rules;
- exact date or currency comparisons;
- sanctions matching that should use an authoritative API.

### Retrieval pipeline

```text
Question or agent task
        |
        v
Access and intent validation
        |
        v
Query construction or decomposition
        |
        v
Semantic and keyword retrieval
        |
        v
Metadata filtering
        |
        v
Relevant evidence selection
        |
        v
LLM answer or finding with citation IDs
```

### Prototype RAG stack

The zero-cost prototype will use:

- local text extraction;
- sentence-transformer embeddings;
- FAISS for vector retrieval;
- metadata stored with each chunk;
- page-level citation references.

The architecture will allow FAISS to be replaced later with Azure AI Search, PostgreSQL with pgvector, OpenSearch, or another approved enterprise service.

---

## Technology Stack

### Zero-cost prototype stack

#### Development environment

- GitHub repository;
- GitHub Codespaces using included personal-account allowance;
- browser-based Visual Studio Code;
- reusable development-container configuration.

#### Frontend

- Next.js;
- TypeScript;
- Microsoft Fluent UI or Tailwind CSS;
- TanStack Query;
- PDF.js-based document viewing.

#### Backend

- Python;
- FastAPI;
- Pydantic;
- Uvicorn;
- SQLAlchemy when persistence is introduced;
- Alembic when database migrations are required.

#### Agent orchestration

- LangGraph;
- explicit state and controlled transitions;
- bounded retries and maximum steps;
- human-review routes.

#### LLM provider

- Gemini Developer API free tier for the initial prototype;
- provider-independent LLM adapter;
- optional Groq fallback only if free developer access is available;
- model and provider selected through environment variables.

#### Document processing

- PyMuPDF;
- pdfplumber;
- python-docx;
- openpyxl;
- Tesseract OCR when needed.

#### RAG

- Sentence Transformers;
- FAISS;
- local metadata and citation mapping.

#### Persistence

- SQLite for the first version;
- local file storage for synthetic or redacted test documents.

#### Evaluation

- Pytest;
- custom Python evaluators;
- JSONL golden datasets;
- optional Gemini-based judge for qualitative dimensions.

#### Tracing and logging

- structured Python logging;
- LangGraph execution traces;
- local JSON trace files;
- OpenTelemetry later if required.

### Future enterprise stack

The modular architecture can later support:

- Microsoft Foundry models and Agent Service;
- Azure AI Document Intelligence;
- Azure AI Search;
- Azure Database for PostgreSQL;
- Azure Blob Storage;
- Azure Service Bus;
- Azure Logic Apps;
- Microsoft Entra ID;
- Microsoft Graph and SharePoint;
- SAP Ariba APIs;
- Azure API Management;
- Azure Key Vault;
- Application Insights and Azure Monitor;
- Azure Container Apps.

---

## Modular Project Architecture

The project is structured as a modular monorepo.

```text
proposal-intelligence-platform/
|
|-- backend/
|   |-- app/
|   |   |-- api/
|   |   |   `-- routes/
|   |   |
|   |   |-- agents/
|   |   |   |-- orchestrator/
|   |   |   |-- proposal_analysis/
|   |   |   |-- vendor_research/
|   |   |   `-- risk_report/
|   |   |
|   |   |-- workflows/
|   |   |-- llm/
|   |   |   `-- providers/
|   |   |-- documents/
|   |   |   `-- parsers/
|   |   |-- rag/
|   |   |-- services/
|   |   |-- repositories/
|   |   |-- integrations/
|   |   |-- evaluation/
|   |   |   |-- evaluators/
|   |   |   `-- datasets/
|   |   |-- schemas/
|   |   |-- core/
|   |   |-- utils/
|   |   `-- main.py
|   |
|   `-- tests/
|       |-- unit/
|       |-- integration/
|       `-- evaluation/
|
|-- frontend/
|-- data/
|   |-- samples/
|   |-- uploads/
|   `-- indexes/
|
|-- docs/
|   |-- architecture/
|   `-- decisions/
|
`-- scripts/
```

### Module responsibilities

#### `api/routes`

Handles HTTP transport only:

- request parsing;
- validation;
- authorization context;
- calling application services;
- response formatting.

Business logic and prompts must not be placed in API routes.

#### `agents`

Contains agent-specific behavior. Each agent will keep its instructions, tools, schemas, and execution logic separated.

#### `workflows`

Contains the controlled LangGraph workflow, state transitions, branch conditions, retry limits, and human-review paths.

#### `llm`

Defines a provider-independent LLM interface and provider implementations. Application modules must use the shared interface rather than calling a provider SDK directly.

#### `documents`

Handles extraction and normalization of PDF, Word, Excel, and scanned-document content. It does not perform risk analysis.

#### `rag`

Handles chunking, embeddings, indexing, retrieval, ranking, and citation metadata.

#### `services`

Contains reusable application and business operations such as assessment management, deterministic scoring, evidence validation, and report assembly.

#### `repositories`

Contains access to SQLite or future databases. Agents must not execute raw database queries.

#### `integrations`

Contains adapters for public data, future SAP Ariba integration, SharePoint, vendor systems, and approved research sources.

#### `evaluation`

Contains evaluators, evaluation datasets, runners, result schemas, quality gates, and regression comparisons.

#### `schemas`

Contains shared Pydantic contracts such as proposal summaries, evidence records, findings, workflow state, agent results, and evaluation results.

#### `core`

Contains configuration, logging, custom exceptions, application constants, and cross-cutting policies.

#### `utils`

Contains only small generic helpers. It must not become a location for unrelated business logic.

### Coding principles

- Each module should have one clear responsibility.
- API, agent, RAG, persistence, evaluation, and integration logic must remain separate.
- Shared communication must use typed schemas.
- Prompts should be versioned and isolated from transport logic.
- LLM providers should be replaceable through configuration.
- Scoring and critical rules should be deterministic.
- Agents receive only the tools and context required for their task.
- Files should remain focused and reasonably small.
- Reusable logic belongs in services, not copied across agents.
- Every module should have corresponding tests.

---

## Security and Responsible AI

### Data handling

The zero-cost prototype must use only:

- synthetic proposal documents;
- public procurement documents;
- fabricated vendor profiles;
- fully redacted test documents;
- sample policies created specifically for testing.

Confidential customer or enterprise documents must not be sent to a free LLM API.

### Secret management

- API keys must be stored in environment variables or Codespaces secrets.
- `.env` files must not be committed.
- Secrets must not appear in prompts, logs, traces, or application responses.
- `.env.example` may contain variable names but no real values.

### Prompt-injection defense

Uploaded and retrieved documents are untrusted input. The platform should:

- treat document instructions as data rather than system commands;
- isolate system instructions from retrieved content;
- restrict available tools;
- validate tool arguments;
- limit agent steps and retries;
- validate every structured output;
- record suspicious instructions;
- route uncertain high-impact cases to human review.

### Least privilege

Every agent will receive only the tools and data required for its responsibility.

Examples:

- the Proposal Analysis Agent does not need approval tools;
- the Vendor Research Agent does not need database administration access;
- the Report Agent does not modify official risk scores;
- the Orchestrator does not bypass workflow states.

### Auditability

Important executions should record:

- model provider and model name;
- model configuration;
- prompt and agent version;
- retrieved evidence IDs;
- tool calls;
- state transitions;
- generated findings;
- evaluator results;
- reviewer modifications;
- final workflow outcome.

---

## Human-in-the-Loop Governance

The platform supports human decision-making rather than replacing it.

Human reviewers remain responsible for:

- accepting or rejecting findings;
- resolving ambiguous evidence;
- approving exceptions;
- changing severity where justified;
- adding confidential reviewer comments;
- determining contractual or commercial action;
- making the final approval decision.

Controlled final statuses may include:

- recommended;
- recommended with conditions;
- further information required;
- escalation required;
- not recommended.

Only authorized human roles can finalize these statuses.

---

## MVP Scope

The first MVP will focus on proving the core workflow at zero planned cost.

### Included

- one RFP and one vendor proposal per assessment;
- PDF and text extraction;
- basic Word and Excel extraction where practical;
- structured proposal summary;
- RFP-to-proposal compliance mapping;
- missing-information detection;
- local RAG over proposal, RFP, and sample policies;
- four operational agents;
- commercial, delivery, security, and compliance findings;
- evidence-linked findings;
- deterministic scoring service;
- management report generation;
- reviewer feedback capture;
- agent and LLM evaluation;
- structured traces and logs;
- Codespaces-based development.

### Excluded from the first MVP

- real confidential enterprise documents;
- production SAP Ariba integration;
- production SharePoint integration;
- paid external financial or adverse-media providers;
- autonomous vendor approval;
- production-scale identity and access management;
- enterprise deployment and high availability;
- advanced legal opinion generation;
- automated outbound communication to vendors.

---

## Future Scope

Potential future capabilities include:

- multiple-bid comparison;
- production SAP Ariba integration;
- SharePoint and Microsoft Graph integration;
- vendor-master and ERP integration;
- licensed financial, regulatory, cyber-risk, and news providers;
- version comparison between original and revised proposals;
- policy-aware approval routing;
- negotiation-question generation;
- contract-deviation analysis;
- portfolio-level vendor concentration analysis;
- organization-wide risk dashboards;
- Microsoft Teams approval experience;
- multilingual proposal support;
- enterprise deployment on Azure;
- continuous production evaluation and model monitoring.

---

## Success Metrics

The project will track both business and technical indicators.

### Business-oriented metrics

- assessment cycle time;
- reviewer hours per proposal;
- report preparation time;
- percentage of requirements automatically mapped;
- percentage of AI findings accepted by reviewers;
- number of critical risks found earlier;
- report rework rate;
- reviewer satisfaction.

### Agent and LLM metrics

- task-completion rate;
- critical-field extraction accuracy;
- structured-output validity;
- critical-finding precision and recall;
- groundedness;
- citation correctness;
- unsupported-claim rate;
- correct tool-selection rate;
- forbidden-tool-call count;
- workflow completion rate;
- repeated-call and loop rate;
- latency;
- LLM calls per assessment;
- quota consumption;
- reviewer correction rate.

---

## Local Development Strategy

The project starts in GitHub Codespaces to avoid local-machine setup and planned infrastructure expenditure.

### Development approach

- use the smallest suitable Codespaces machine;
- configure a short idle timeout;
- stop the Codespace after each session;
- keep paid Codespaces usage disabled;
- use a private GitHub repository;
- avoid committing generated indexes, uploaded documents, databases, reports, traces, and secrets;
- use only synthetic, public, or redacted test documents;
- cache extraction results to avoid repeated LLM calls;
- enforce daily and per-assessment LLM-call limits.

### Important limitation

Codespaces is the development environment, not the permanent production host. Forwarded URLs are temporary, the environment stops after inactivity, and monthly compute and storage allowances apply.

---

## Getting Started

The detailed setup will evolve as the application is implemented.

### Prerequisites

- GitHub account;
- private repository;
- GitHub Codespaces access;
- Gemini Developer API key for free-tier prototype usage;
- synthetic or redacted sample documents.

### Clone or open in Codespaces

Open the repository in GitHub and select:

```text
Code -> Codespaces -> Create codespace on main
```

### Planned backend startup

After backend dependencies and application code are added, the intended development command will be similar to:

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Planned frontend startup

After the Next.js application is initialized:

```bash
cd frontend
npm install
npm run dev
```

The Codespace will expose the application through forwarded ports.

---

## Environment Variables

The following configuration is planned:

```dotenv
APP_ENV=development
APP_NAME=Proposal Intelligence Platform
LOG_LEVEL=INFO

LLM_PROVIDER=gemini
LLM_MODEL=<free-tier-model-id>
GEMINI_API_KEY=<configured-through-codespaces-secret>

MAX_AGENT_STEPS=12
MAX_AGENT_RETRIES=2
MAX_LLM_CALLS_PER_ASSESSMENT=20

DATABASE_URL=sqlite:///./proposal_intelligence.db
UPLOAD_DIRECTORY=../data/uploads
INDEX_DIRECTORY=../data/indexes
```

Real values must be stored in Codespaces secrets or an uncommitted `.env` file.

---

## Testing Strategy

### Unit tests

Test individual functions and modules, including:

- document parsers;
- chunking;
- schema validation;
- deterministic scoring;
- evidence utilities;
- provider adapters.

### Integration tests

Test interactions between:

- document processing and RAG;
- RAG and agents;
- agents and workflow state;
- services and repositories;
- backend routes and services.

### Evaluation tests

Test:

- proposal extraction;
- RFP mapping;
- finding quality;
- grounding;
- citation accuracy;
- tool selection;
- agent trajectory;
- prompt-injection resistance;
- end-to-end workflow completion.

### Frontend tests

Planned tools include:

- component tests;
- API interaction tests;
- Playwright for critical user flows.

### Regression policy

Changes to a model, prompt, agent, tool, retrieval configuration, schema, or report template must run the relevant evaluation suite before release.

---

## Repository Guidelines

### Branch strategy

During the initial solo-development stage:

- `main` remains stable;
- feature branches use names such as `feature/document-extraction`;
- fixes use names such as `fix/citation-validation`;
- evaluation changes use names such as `eval/proposal-agent-baseline`.

### Commit convention

Examples:

```text
chore: create modular project structure
feat: add proposal PDF parser
feat: add Gemini LLM provider adapter
feat: implement proposal analysis agent
fix: preserve page references during chunking
test: add proposal extraction evaluation cases
docs: update architecture overview
```

### Pull-request expectations

A pull request should describe:

- the problem being solved;
- modules changed;
- tests and evaluations run;
- known limitations;
- security or data-handling impact;
- screenshots for user-interface changes.

### Never commit

- API keys;
- `.env` files;
- confidential proposals;
- real customer information;
- generated vector indexes;
- local SQLite databases;
- unrestricted trace logs;
- generated reports containing sensitive data.

---

## Project Roadmap

### Phase 1 — Foundation

- create repository and Codespace;
- establish modular directory structure;
- configure development container;
- add backend health check;
- add formatting, linting, and tests;
- initialize frontend.

### Phase 2 — LLM abstraction

- define common LLM interface;
- implement Gemini provider;
- support structured outputs;
- add retry and quota controls;
- add provider-level tests.

### Phase 3 — Document intelligence

- implement PDF extraction;
- preserve page and section metadata;
- process Word and Excel files;
- add OCR fallback;
- create extraction evaluation cases.

### Phase 4 — Local RAG

- chunk extracted content;
- generate local embeddings;
- create FAISS index;
- retrieve evidence with metadata;
- evaluate retrieval quality.

### Phase 5 — Agent workflow

- implement workflow state;
- implement Orchestrator Agent;
- implement Proposal Analysis Agent;
- implement Vendor Research Agent;
- implement Risk and Report Agent;
- add bounded retries and human-review paths.

### Phase 6 — Evaluation framework

- create golden datasets;
- implement deterministic evaluators;
- add groundedness and citation evaluation;
- evaluate tool selection and trajectories;
- create regression reports.

### Phase 7 — User experience

- assessment dashboard;
- document upload;
- proposal summary;
- RFP compliance matrix;
- evidence viewer;
- findings and reviewer feedback;
- report preview.

### Phase 8 — Demonstration and hardening

- create synthetic demonstration cases;
- run end-to-end evaluations;
- improve security controls;
- document architecture decisions;
- prepare project demonstration and deployment options.

---

## Current Project Status

```text
Status: Foundation setup in progress
Environment: GitHub Codespaces
Planned cost: Zero, within free usage quotas
Operational agents planned for MVP: 4
Production agent target: Expand only after evaluation
Current data policy: Synthetic, public, or fully redacted data only
```

### Immediate next steps

1. Create the modular repository structure.
2. Add `.gitignore` rules for secrets and generated data.
3. Add a lightweight development-container configuration.
4. Configure backend linting, formatting, and unit testing.
5. Build the first FastAPI health endpoint.
6. Implement the provider-independent LLM interface.

---

## Disclaimer

This platform is a decision-support and research-assistance system. AI-generated content may be incomplete, incorrect, stale, or misunderstood. The platform must not be treated as a substitute for professional procurement, legal, financial, security, compliance, or risk advice.

Final vendor decisions, approvals, exceptions, contract interpretations, and risk acceptance remain the responsibility of authorized human stakeholders.

---

## Project Vision

> Build a modular, evidence-grounded, traceable, and evaluable AI platform that helps enterprises review proposals faster without sacrificing responsible governance or human accountability.
