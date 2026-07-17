import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_assessment_execution_service,
    get_assessment_repository,
    get_assessment_service,
    get_assessment_workflow_executor,
)
from app.main import app
from app.services.assessment_execution_service import AssessmentExecutionService
from tests.assessment_execution_fakes import FakeAssessmentWorkflowExecutor


@pytest.fixture(autouse=True)
def reset_dependencies():
    """Reset caches and dependency overrides."""

    get_assessment_execution_service.cache_clear()
    get_assessment_workflow_executor.cache_clear()
    get_assessment_service.cache_clear()
    get_assessment_repository.cache_clear()
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()
    get_assessment_execution_service.cache_clear()
    get_assessment_workflow_executor.cache_clear()
    get_assessment_service.cache_clear()
    get_assessment_repository.cache_clear()


@pytest.fixture
def fake_executor() -> FakeAssessmentWorkflowExecutor:
    """Create a fake workflow executor."""

    return FakeAssessmentWorkflowExecutor()


@pytest.fixture
def client(
    fake_executor: FakeAssessmentWorkflowExecutor,
) -> TestClient:
    """Create an API client using the fake executor."""

    repository = get_assessment_repository()
    execution_service = AssessmentExecutionService(
        repository=repository,
        workflow_executor=fake_executor,
    )
    app.dependency_overrides[get_assessment_execution_service] = lambda: execution_service
    return TestClient(app)


def create_assessment(client: TestClient) -> str:
    """Create an assessment and return its ID."""

    response = client.post(
        "/api/v1/assessments",
        json={
            "vendor_name": "Example Digital Services",
            "proposal_document_id": "proposal-001",
            "capabilities": [
                "proposal_analysis",
                "vendor_research",
                "risk_report",
            ],
            "human_review_required": True,
        },
    )
    assert response.status_code == 201
    return response.json()["assessment_id"]


def test_execute_assessment_returns_accepted(client: TestClient) -> None:
    assessment_id = create_assessment(client)
    response = client.post(f"/api/v1/assessments/{assessment_id}/execute")

    assert response.status_code == 202
    response_data = response.json()
    assert response_data["assessment_id"] == assessment_id
    assert response_data["execution_accepted"] is True
    assert response_data["lifecycle_status"] == "queued"


def test_background_execution_persists_completion(
    client: TestClient,
    fake_executor: FakeAssessmentWorkflowExecutor,
) -> None:
    assessment_id = create_assessment(client)
    response = client.post(f"/api/v1/assessments/{assessment_id}/execute")
    assert response.status_code == 202

    status_response = client.get(f"/api/v1/assessments/{assessment_id}")
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert status_data["lifecycle_status"] == "completed"
    assert status_data["workflow_status"] == "completed"
    assert status_data["human_review_required"] is True
    assert len(fake_executor.received_states) == 1


def test_execute_unknown_assessment_returns_not_found(
    client: TestClient,
) -> None:
    response = client.post("/api/v1/assessments/assessment-missing/execute")
    assert response.status_code == 404
    assert response.json()["detail"]["error_code"] == "assessment_not_found"


def test_duplicate_execution_returns_conflict(client: TestClient) -> None:
    assessment_id = create_assessment(client)
    first_response = client.post(f"/api/v1/assessments/{assessment_id}/execute")
    assert first_response.status_code == 202

    second_response = client.post(f"/api/v1/assessments/{assessment_id}/execute")
    assert second_response.status_code == 409
    assert second_response.json()["detail"]["error_code"] == "assessment_execution_conflict"
