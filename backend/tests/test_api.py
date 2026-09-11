from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_snapshot_has_sections():
    client = TestClient(app)
    response = client.get("/api/snapshot")
    assert response.status_code == 200
    body = response.json()
    assert "health_score" in body
    assert "concerns" in body
    assert "link" in body
    assert "nearby" in body
    assert "devices" in body
    assert "internet" in body
    assert "interfaces" in body
    assert "system" in body
    assert body["link"]["ssid"]
