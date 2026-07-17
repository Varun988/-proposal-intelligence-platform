import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_assessment_repository,
    get_assessment_service,
)
from app.main import app


@pytest.fixture(autouse=True)
def reset_assessment_dependencies() -> None:
    """Reset cached in-memory dependencies between tests."""

    get_assessment_service.cache_clear()
    get_assessment_repository.cache_clear()

    yield

    get_assessment_service.cache_clear()
    get_assessment_repository.cache_clear()


@pytest.fixture
def client() -> TestClient:
    """Create an isolated FastAPI test client."""

    return TestClient(app)


def create_payload() -> dict[str, object]:
    """Create a valid assessment request payload."""

    return {
        "vendor_name": "Example Digital Services",
        "proposal_document_id": "proposal-001",
        "capabilities": [
            "proposal_analysis",
            "vendor_research",
            "risk_report",
        ],
        "proposal_requirements": [("The proposal must provide an implementation timeline.")],
        "proposal_analysis_objectives": [
            "delivery timeline",
            "pricing and exclusions",
        ],
        "vendor_research_objectives": [
            "company profile and ownership",
            "financial information",
        ],
        "report_objectives": [
            "identify material cross-agent risks",
        ],
        "human_review_required": True,
    }


def test_create_assessment_returns_created_record(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/assessments",
        json=create_payload(),
    )

    assert response.status_code == 201

    response_data = response.json()

    assert response_data["assessment_id"].startswith("assessment-")
    assert response_data["lifecycle_status"] == "created"
    assert response_data["workflow_status"] == "created"
    assert response_data["vendor_name"] == "Example Digital Services"
    assert response_data["proposal_document_id"] == "proposal-001"
    assert response_data["human_review_required"] is True
    assert "created_at" in response_data


def test_get_assessment_returns_created_status(
    client: TestClient,
) -> None:
    create_response = client.post(
        "/api/v1/assessments",
        json=create_payload(),
    )

    assessment_id = create_response.json()["assessment_id"]

    response = client.get(
        f"/api/v1/assessments/{assessment_id}",
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["assessment_id"] == assessment_id
    assert response_data["lifecycle_status"] == "created"
    assert response_data["workflow_status"] == "created"
    assert response_data["current_step"] == 0
    assert response_data["maximum_steps"] == 12
    assert response_data["completed_agents"] == []
    assert response_data["agent_executions"] == []
    assert response_data["evaluations"] == []
    assert response_data["human_review_required"] is True
    assert response_data["error_count"] == 0


def test_get_results_returns_empty_created_result(
    client: TestClient,
) -> None:
    create_response = client.post(
        "/api/v1/assessments",
        json=create_payload(),
    )

    assessment_id = create_response.json()["assessment_id"]

    response = client.get(
        f"/api/v1/assessments/{assessment_id}/results",
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["assessment_id"] == assessment_id
    assert response_data["lifecycle_status"] == "created"
    assert response_data["workflow_status"] == "created"

    assert response_data["proposal_analysis"] is None
    assert response_data["vendor_research"] is None
    assert response_data["risk_report"] is None

    assert response_data["proposal_evaluation"] is None
    assert response_data["vendor_evaluation"] is None
    assert response_data["risk_report_evaluation"] is None

    assert response_data["human_review_required"] is True


def test_get_unknown_assessment_returns_not_found(
    client: TestClient,
) -> None:
    response = client.get(
        "/api/v1/assessments/assessment-missing",
    )

    assert response.status_code == 404

    response_data = response.json()
    detail = response_data["detail"]

    assert detail["error_code"] == "assessment_not_found"
    assert detail["assessment_id"] == "assessment-missing"
    assert "not found" in detail["message"]


def test_get_unknown_results_returns_not_found(
    client: TestClient,
) -> None:
    response = client.get(
        ("/api/v1/assessments/assessment-missing/results"),
    )

    assert response.status_code == 404

    detail = response.json()["detail"]

    assert detail["error_code"] == "assessment_not_found"
    assert detail["assessment_id"] == "assessment-missing"


def test_create_rejects_risk_without_proposal(
    client: TestClient,
) -> None:
    payload = create_payload()
    payload["capabilities"] = [
        "risk_report",
    ]

    response = client.post(
        "/api/v1/assessments",
        json=payload,
    )

    assert response.status_code == 422


def test_create_rejects_vendor_without_proposal(
    client: TestClient,
) -> None:
    payload = create_payload()
    payload["capabilities"] = [
        "vendor_research",
    ]

    response = client.post(
        "/api/v1/assessments",
        json=payload,
    )

    assert response.status_code == 422


def test_create_rejects_disabled_human_review(
    client: TestClient,
) -> None:
    payload = create_payload()
    payload["human_review_required"] = False

    response = client.post(
        "/api/v1/assessments",
        json=payload,
    )

    assert response.status_code == 422


def test_create_rejects_empty_vendor_name(
    client: TestClient,
) -> None:
    payload = create_payload()
    payload["vendor_name"] = ""

    response = client.post(
        "/api/v1/assessments",
        json=payload,
    )

    assert response.status_code == 422
