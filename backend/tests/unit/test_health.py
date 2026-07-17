from fastapi.testclient import TestClient

from app.main import create_app


def test_health_check_returns_application_status() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "application": "Proposal Intelligence Platform",
        "version": "0.1.0",
        "environment": "development",
    }
