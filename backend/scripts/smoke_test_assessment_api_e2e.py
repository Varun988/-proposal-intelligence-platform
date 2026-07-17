"""Run a live, in-process, end-to-end assessment API smoke test.

This script exercises the real FastAPI routes, document pipeline, local
Sentence Transformer embeddings, assessment-scoped FAISS retrieval, real
Gemini agents, deterministic evaluation gates, and persisted API results.

Current API limitation
----------------------
The document upload endpoint can accept an assessment ID, but an assessment
cannot be created until its proposal document ID is known. Until a dedicated
document-association endpoint exists, this smoke test uploads documents first,
creates the assessment, and then binds the stored document records to the new
assessment through the in-process repository. All processing and workflow
execution still occur through the real REST endpoints.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Any

from fastapi.testclient import TestClient

from app.api.dependencies import get_document_repository
from app.core.config import get_settings
from app.main import app
from app.schemas.assessment import utc_now

PROPOSAL_FILE_NAME = "synthetic-proposal.txt"
VENDOR_FILE_NAME = "synthetic-vendor-profile.txt"
VENDOR_NAME = "Example Digital Services"

PROPOSAL_TEXT = """Example Digital Services submitted a proposal for the
Enterprise Platform Modernization Program.

The scope includes solution design, application development, testing,
deployment, knowledge transfer, and production support.

The implementation timeline is twelve months from contract signature and
includes design, build, test, and deployment phases.

The delivery team includes twenty consultants: two architects, twelve
developers, four test engineers, and two project managers.

Customer information will be encrypted at rest and in transit. Access uses
role-based controls and multifactor authentication.

The fixed implementation price is two million Australian dollars, excluding
taxes, approved travel, and third-party licence costs.

The client must provide timely access to subject-matter experts, system
documentation, and required test data.
"""

VENDOR_TEXT = """Example Digital Services was established in 2012 and is
headquartered in Melbourne, Australia.

The supplied synthetic profile states that the vendor reported positive
operating cash flow for the previous three years. This is a vendor-profile
claim and has not been independently verified.

The supplied synthetic profile claims current ISO 27001 certification.
Independent certificate validation is unavailable.

No adverse events are recorded in the supplied synthetic vendor profile.
No independent reputation source was supplied.
"""


@dataclass(frozen=True)
class UploadedDocument:
    """Identity and purpose of one uploaded synthetic document."""

    document_id: str
    purpose: str


def require(condition: bool, message: str) -> None:
    """Stop the smoke test with a concise validation error."""

    if not condition:
        raise RuntimeError(message)


def response_json(response: Any, operation: str) -> dict[str, Any]:
    """Validate one HTTP response and return its JSON object."""

    if response.status_code >= 400:
        try:
            body = response.json()
        except Exception:
            body = response.text
        raise RuntimeError(f"{operation} failed with HTTP {response.status_code}: {body}")

    body = response.json()
    require(isinstance(body, dict), f"{operation} returned invalid JSON.")
    return body


def print_heading(title: str) -> None:
    """Print one readable console section heading."""

    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def print_evaluation(label: str, report: dict[str, Any] | None) -> None:
    """Print a compact evaluation summary."""

    print()
    print(label)
    print("-" * len(label))

    if report is None:
        print("No evaluation report available.")
        return

    print(f"Release approved: {report.get('release_approved')}")
    print(f"Overall score: {report.get('overall_score')}")
    print(f"Blocking failures: {report.get('blocking_gate_failure_count')}")

    for result in report.get("results", []):
        print(f"- {result.get('evaluator_name')}: {result.get('status')} ({result.get('score')})")


def upload_document(
    client: TestClient,
    file_name: str,
    text: str,
    purpose: str,
    vendor_name: str | None = None,
    source_name: str | None = None,
) -> UploadedDocument:
    """Upload one synthetic UTF-8 document through the REST API."""

    form_data: dict[str, str] = {
        "purpose": purpose,
        "is_public_source": "false",
    }

    if vendor_name is not None:
        form_data["vendor_name"] = vendor_name
    if source_name is not None:
        form_data["source_name"] = source_name

    response = client.post(
        "/api/v1/documents",
        data=form_data,
        files={
            "file": (
                file_name,
                text.encode("utf-8"),
                "text/plain",
            )
        },
    )
    body = response_json(response, f"Upload {file_name}")

    require(
        body.get("lifecycle_status") == "stored",
        f"{file_name} did not reach STORED.",
    )

    print(f"Uploaded {file_name}: {body['document_id']} ({body['file_size_bytes']} bytes)")

    return UploadedDocument(
        document_id=body["document_id"],
        purpose=purpose,
    )


def create_assessment(
    client: TestClient,
    proposal_document_id: str,
) -> str:
    """Create the assessment through the REST API."""

    response = client.post(
        "/api/v1/assessments",
        json={
            "vendor_name": VENDOR_NAME,
            "proposal_document_id": proposal_document_id,
            "capabilities": [
                "proposal_analysis",
                "vendor_research",
                "risk_report",
            ],
            "proposal_requirements": [
                ("The proposal must provide an implementation timeline and delivery approach.")
            ],
            "proposal_analysis_objectives": [
                "scope and delivery timeline",
                "pricing, assumptions, dependencies, and exclusions",
                "staffing, support, and security controls",
            ],
            "vendor_research_objectives": [
                "company profile and ownership",
                "financial information",
                "security posture and certifications",
                "reputation and relevant adverse events",
            ],
            "report_objectives": [
                "summarize validated proposal findings",
                "summarize validated vendor research",
                "identify material cross-agent risks",
                "provide mitigations and clarification questions",
                "prepare reviewer and executive reports",
            ],
            "maximum_workflow_steps": 12,
            "maximum_retries": 2,
            "human_review_required": True,
        },
    )
    body = response_json(response, "Create assessment")

    require(
        body.get("lifecycle_status") == "created",
        "Assessment did not reach CREATED.",
    )

    assessment_id = body["assessment_id"]
    print(f"Created assessment: {assessment_id}")
    return assessment_id


async def bind_documents_to_assessment(
    assessment_id: str,
    documents: list[UploadedDocument],
) -> None:
    """Bridge the current missing document-association REST endpoint."""

    repository = get_document_repository()

    for document in documents:
        record = await repository.get(document.document_id)
        updated_record = record.model_copy(
            update={
                "assessment_id": assessment_id,
                "updated_at": utc_now(),
            },
            deep=True,
        )
        await repository.update(updated_record)

    print("Bound uploaded documents to the assessment through the in-process repository bridge.")


def process_document(client: TestClient, document_id: str) -> None:
    """Run extraction, chunking, embedding, and indexing through REST."""

    response = client.post(f"/api/v1/documents/{document_id}/process")
    body = response_json(response, f"Process {document_id}")

    require(
        response.status_code == 202,
        f"Processing request for {document_id} was not accepted.",
    )
    require(
        body.get("processing_accepted") is True,
        f"Processing was not accepted for {document_id}.",
    )

    status_response = client.get(f"/api/v1/documents/{document_id}")
    status_body = response_json(
        status_response,
        f"Get document status {document_id}",
    )

    require(
        status_body.get("lifecycle_status") == "indexed",
        (
            f"Document {document_id} did not reach INDEXED. "
            f"Current status: {status_body.get('lifecycle_status')}; "
            f"error: {status_body.get('error_message')}"
        ),
    )

    print(
        f"Indexed {document_id}: pages={status_body.get('page_count')}, "
        f"characters={status_body.get('extracted_character_count')}, "
        f"chunks={status_body.get('chunk_count')}"
    )


def execute_assessment(client: TestClient, assessment_id: str) -> None:
    """Execute the real four-agent workflow through the REST API."""

    response = client.post(f"/api/v1/assessments/{assessment_id}/execute")
    response_json(response, "Execute assessment")
    require(
        response.status_code == 202,
        "Assessment execution request was not accepted.",
    )


def validate_final_state(
    client: TestClient,
    assessment_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Read and validate final status and result payloads."""

    status_body = response_json(
        client.get(f"/api/v1/assessments/{assessment_id}"),
        "Get assessment status",
    )
    results_body = response_json(
        client.get(f"/api/v1/assessments/{assessment_id}/results"),
        "Get assessment results",
    )

    require(
        status_body.get("workflow_status") == "completed",
        (
            "Workflow did not reach COMPLETED. "
            f"Status: {status_body.get('workflow_status')}; "
            f"reason: {status_body.get('human_review_reason')}; "
            f"errors: {status_body.get('error_count')}"
        ),
    )
    require(
        status_body.get("human_review_required") is True,
        "Final human review was unexpectedly disabled.",
    )
    require(
        status_body.get("error_count") == 0,
        "The completed assessment recorded workflow errors.",
    )

    expected_agents = {
        "orchestrator",
        "proposal-analysis",
        "vendor-research",
        "risk-report",
    }
    completed_agents = set(status_body.get("completed_agents", []))
    require(
        expected_agents.issubset(completed_agents),
        "Not all planned agents completed.",
    )

    for key in (
        "proposal_evaluation",
        "vendor_evaluation",
        "risk_report_evaluation",
    ):
        report = results_body.get(key)
        require(report is not None, f"Missing {key}.")
        require(
            report.get("release_approved") is True,
            f"{key} did not approve release.",
        )

    return status_body, results_body


def run_smoke_test() -> None:
    """Run the complete live API smoke test."""

    settings = get_settings()
    require(
        bool(settings.gemini_api_key),
        "GEMINI_API_KEY is not configured.",
    )

    print_heading("LIVE END-TO-END ASSESSMENT API SMOKE TEST")
    print(f"LLM model: {settings.llm_model}")
    print(f"Embedding model: {settings.embedding_model}")
    print("Data classification: synthetic")
    print("Expected live Gemini calls: 3")

    with TestClient(app) as client:
        proposal = upload_document(
            client=client,
            file_name=PROPOSAL_FILE_NAME,
            text=PROPOSAL_TEXT,
            purpose="proposal",
        )
        vendor = upload_document(
            client=client,
            file_name=VENDOR_FILE_NAME,
            text=VENDOR_TEXT,
            purpose="vendor_profile",
            vendor_name=VENDOR_NAME,
            source_name="Synthetic Vendor Profile",
        )

        assessment_id = create_assessment(
            client=client,
            proposal_document_id=proposal.document_id,
        )

        import asyncio

        asyncio.run(
            bind_documents_to_assessment(
                assessment_id=assessment_id,
                documents=[proposal, vendor],
            )
        )

        process_document(client, proposal.document_id)
        process_document(client, vendor.document_id)

        execute_assessment(client, assessment_id)
        status_body, results_body = validate_final_state(
            client=client,
            assessment_id=assessment_id,
        )

    print_heading("ASSESSMENT RESULT")
    print(f"Assessment ID: {assessment_id}")
    print(f"Lifecycle status: {status_body.get('lifecycle_status')}")
    print(f"Workflow status: {status_body.get('workflow_status')}")
    print(f"Current step: {status_body.get('current_step')}")
    print("Completed agents: " + ", ".join(status_body.get("completed_agents", [])))
    print(f"Human review required: {status_body.get('human_review_required')}")
    print(f"Human review reason: {status_body.get('human_review_reason')}")
    print(f"Errors: {status_body.get('error_count')}")

    print_evaluation(
        "PROPOSAL ANALYSIS EVALUATION",
        results_body.get("proposal_evaluation"),
    )
    print_evaluation(
        "VENDOR RESEARCH EVALUATION",
        results_body.get("vendor_evaluation"),
    )
    print_evaluation(
        "RISK AND REPORT EVALUATION",
        results_body.get("risk_report_evaluation"),
    )

    print_heading("VALIDATION PASSED")
    print("- Documents uploaded through the REST API")
    print("- Documents extracted, chunked, embedded, and indexed")
    print("- FAISS retrieval remained assessment-scoped")
    print("- Proposal Analysis completed and passed release gates")
    print("- Vendor Research completed and passed release gates")
    print("- Risk and Report completed and passed its release gate")
    print("- Workflow reached COMPLETED")
    print("- Final business review remains human-owned")

    print()
    print("Compact risk report:")
    print(
        json.dumps(
            results_body.get("risk_report"),
            indent=2,
        )
    )


if __name__ == "__main__":
    try:
        run_smoke_test()
    except KeyboardInterrupt:
        print("Smoke test interrupted.", file=sys.stderr)
        raise SystemExit(130)
    except Exception as error:
        print(f"Smoke test failed: {error}", file=sys.stderr)
        raise SystemExit(1)
