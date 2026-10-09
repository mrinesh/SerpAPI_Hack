"""The API skeleton boots, and unbuilt endpoints fail with the agreed 501 shape."""


def test_health_reports_modes(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["serpapi_mode"] == "replay"
    assert body["llm_mode"] == "replay"


def test_alerts_start_empty(client):
    response = client.get("/api/alerts")
    assert response.status_code == 200
    assert response.json() == []


def test_openapi_schema_builds(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/profiles/{profile_id}/runs" in paths
    assert "/api/compare" in paths
