"""F-07: one property as one run judged it, assembled from stored results (ADR 0021)."""

import pytest

from app.pipeline import orchestrator
from app.reference.demo_profiles import DEMO_PROFILES


@pytest.fixture(autouse=True)
def inline(monkeypatch):
    monkeypatch.setattr(orchestrator, "_launch", orchestrator.run_pipeline)


def _demo_run(client, name: str) -> str:
    profile_id = client.post("/api/profiles", json=DEMO_PROFILES[name]).json()["id"]
    return client.post(f"/api/profiles/{profile_id}/runs").json()["id"]


@pytest.mark.parametrize("name", DEMO_PROFILES)
def test_ranked_detail_matches_the_run_and_its_frozen_area(client, name):
    run_id = _demo_run(client, name)
    [top, *_] = client.get(f"/api/runs/{run_id}/recommendations").json()
    [area] = client.get(f"/api/runs/{run_id}/areas").json()

    response = client.get(f"/api/properties/{top['listing']['id']}", params={"run_id": run_id})

    assert response.status_code == 200
    detail = response.json()
    assert detail["run_id"] == run_id
    assert detail["recommendation"] == top
    assert detail["metrics"] == top["metrics"]
    assert detail["verification"] == top["verification"]
    assert detail["area"] == area
    competitors = client.get(f"/api/runs/{run_id}/competitors").json()
    if name == "commercial":
        assert [detail["competitors"]] == competitors  # the run's frozen report (F-06)
        places = {place["source"]["url"] for place in competitors[0]["competitors"]}
        assert places <= {source["url"] for source in detail["sources"]}
    else:
        assert detail["competitors"] is None and competitors == []
    assert [p["run_id"] for p in detail["price_history"]] == [run_id]
    keys = [(s["engine"], s["url"], s["search_id"]) for s in detail["sources"]]
    assert keys and len(keys) == len(set(keys))
    assert {s["engine"] for s in detail["sources"]} >= {"google", "google_maps"}


def test_rejected_and_unchecked_candidates_have_no_recommendation(client):
    run_id = _demo_run(client, "residential")
    checks = {v["listing_id"]: v for v in client.get(f"/api/runs/{run_id}/verifications").json()}
    listings = client.get(f"/api/runs/{run_id}/listings").json()
    rejected = next(i for i, v in checks.items() if v["verdict"] == "reject")
    unchecked = next(item["id"] for item in listings if item["id"] not in checks)

    detail = client.get(f"/api/properties/{rejected}", params={"run_id": run_id}).json()
    assert detail["verification"] == checks[rejected]
    assert detail["recommendation"] is None and detail["metrics"] is None

    detail = client.get(f"/api/properties/{unchecked}", params={"run_id": run_id}).json()
    assert detail["verification"] is None and detail["recommendation"] is None


def test_without_run_id_the_latest_run_is_used(client):
    first = _demo_run(client, "residential")
    second = _demo_run(client, "residential")
    listing_id = client.get(f"/api/runs/{second}/recommendations").json()[0]["listing"]["id"]

    detail = client.get(f"/api/properties/{listing_id}").json()

    assert detail["run_id"] == second
    assert [p["run_id"] for p in detail["price_history"]] == [first, second]


def test_commercial_detail_keeps_the_too_good_to_be_true_flag(client):
    run_id = _demo_run(client, "commercial")
    office = next(
        r
        for r in client.get(f"/api/runs/{run_id}/recommendations").json()
        if r["listing"]["price_inr"]["value"] == 360_000
    )
    detail = client.get(f"/api/properties/{office['listing']['id']}", params={"run_id": run_id})
    flags = [flag["kind"] for flag in detail.json()["verification"]["flags"]]
    assert "too_good_to_be_true" in flags


def test_unknown_listing_and_foreign_run_are_404(client):
    residential = _demo_run(client, "residential")
    commercial = _demo_run(client, "commercial")
    listing_id = client.get(f"/api/runs/{residential}/listings").json()[0]["id"]

    assert client.get("/api/properties/nope").status_code == 404
    assert client.get(f"/api/properties/{listing_id}", params={"run_id": "nope"}).status_code == 404
    response = client.get(f"/api/properties/{listing_id}", params={"run_id": commercial})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
