from app.pipeline import orchestrator
from app.reference.demo_profiles import DEMO_PROFILES


def test_commercial_review_analysis_replays_with_cited_real_evidence(client, monkeypatch):
    monkeypatch.setattr(orchestrator, "_launch", orchestrator.run_pipeline)
    profile = client.post("/api/profiles", json=DEMO_PROFILES["commercial"]).json()
    run = client.post(f"/api/profiles/{profile['id']}/runs").json()
    assert client.get(f"/api/runs/{run['id']}").json()["status"] == "succeeded"
    [report] = client.get(f"/api/runs/{run['id']}/competitors").json()
    assert report["review_status"] == "ok" and report["review_warnings"] == []
    assert report["review_places_sampled"] == 1 and len(report["reviews"]) == 8
    assert report["gaps"]
    for gap in report["gaps"]:
        assert len(gap["sources"]) >= 2 and gap["confidence"] == 0.55
        assert all(source["engine"] == "google_maps_reviews" for source in gap["sources"])
    top = client.get(f"/api/runs/{run['id']}/recommendations").json()[0]
    detail = client.get(f"/api/properties/{top['listing']['id']}?run_id={run['id']}").json()
    assert detail["competitors"] == report
    assert any(source["engine"] == "google_maps_reviews" for source in detail["sources"])
    assert client.get("/api/meta/budget").json()["used_this_month"] == 0
