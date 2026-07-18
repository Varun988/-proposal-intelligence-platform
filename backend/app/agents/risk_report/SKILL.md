---
name: risk-report
version: 1.0.0
owning-agent: risk-report
status: active
human-review-required: true
---

# Risk and Report Skill

## Purpose

Synthesize validated specialist findings into evidence-grounded risks,
mitigations, clarification questions, reviewer reports, and executive
decision-support reports.

This skill consumes validated specialist outputs. It does not make the
official vendor decision.

## Capabilities

- `risk-synthesis`
- `mitigation-generation`
- `clarification-question-generation`
- `reviewer-report-generation`
- `executive-report-generation`

## Required Tools

This skill currently has no required direct tools.

Its primary inputs are validated specialist-agent results supplied in
`RiskReportInput`.

## Optional Tools

- `search_evidence`
- `get_document_page`

These tools are permitted by policy for future controlled use. The
current `RiskReportAgent` implementation does not directly receive a
`ToolRegistry`.

## Input Contract

- Model: `RiskReportInput`
- Module: `app.agents.risk_report.schemas`

The input includes:

- assessment identity;
- proposal-document identity;
- vendor identity;
- validated Proposal Analysis output;
- optional validated Vendor Research output;
- deterministic risk scores;
- report objectives.

## Output Contract

- Model: `RiskReportExecution`
- Result model: `RiskReportResult`
- Module: `app.agents.risk_report.schemas`

The output includes:

- synthesized risks;
- source finding references;
- evidence references;
- mitigations;
- clarification questions;
- reviewer report;
- executive report;
- analysis limitations;
- LLM provider and model metadata;
- instruction version;
- execution time.

## Skill Dependencies

Required dependency:

- `proposal-analysis`

The Proposal Analysis result must be available before Risk and Report
execution.

Vendor Research is an optional workflow predecessor. It is not declared
as a mandatory skill dependency because the current workflow supports
report generation without Vendor Research.

## Tool Limit

Maximum permitted tool calls:

```text
5
```
The runtime value is controlled by:

```text
RISK_REPORT_MAX_TOOL_CALLS
```

The current implementation may execute zero direct tool calls.

## Governance

The skill must:

- use only validated specialist outputs and approved evidence;
- preserve source-agent, source-finding, and source-evidence links;
- preserve deterministic scores supplied by trusted services;
- separate facts, analysis, uncertainty, mitigations, and proposed
  conditions;
- include the required decision-support disclaimer;
- require human review.

The skill must not:

- invent risks, scores, citations, incidents, certifications, financial
  figures, or obligations;
- calculate or modify the official deterministic risk score;
- approve, reject, recommend, or officially classify a vendor;
- bypass evaluation gates;
- remove the human-review requirement;
- provide specialist advice as a substitute for authorized review.

## Evaluation

The skill is governed by:

- `risk-report-evaluator`

The evaluator has a blocking release gate in the default evaluation
configuration.

## Runtime Source of Truth

Runtime configuration is defined by:

- `app.skills.definitions.risk_report`
- `app.agents.risk_report.instructions`
- `app.agents.risk_report.policies`
- `app.agents.risk_report.schemas`
- `app.evaluation.risk_report`

This document is descriptive. Runtime security and authorization are
enforced by Python policies, schemas, registries, and evaluators.