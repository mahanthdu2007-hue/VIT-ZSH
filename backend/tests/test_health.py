from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_reports_backends() -> None:
    with TestClient(app) as started:  # runs startup, which loads System 1
        response = started.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["system1"] == "keyword"
    assert body["llm"] in {"groq", "gemini", "none"}
    assert isinstance(body["demo_mode"], bool)


def test_health_allows_frontend_origin() -> None:
    response = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
