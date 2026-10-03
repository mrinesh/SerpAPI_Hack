"""The API skeleton boots, and unbuilt endpoints fail with the agreed 501 shape."""


def test_health_reports_modes(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["serpapi_mode"] == "replay"
    assert body["llm_mode"] == "replay"


def test_unbuilt_endpoint_returns_501_with_checklist_id(client):
    response = client.get("/api/profiles")
    assert response.status_code == 501
    error = response.json()["error"]
    assert error["code"] == "not_implemented"
    assert error["details"]["feature_id"] == "F-01"


def test_openapi_schema_builds(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/profiles/{profile_id}/runs" in paths
    assert "/api/compare" in paths
