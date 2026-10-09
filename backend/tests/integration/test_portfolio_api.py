import pytest

from app.pipeline import orchestrator
from app.reference.demo_profiles import DEMO_PROFILES


@pytest.fixture
def candidates(client, monkeypatch):
    monkeypatch.setattr(orchestrator, "_launch", orchestrator.run_pipeline)
    profile = client.post("/api/profiles", json=DEMO_PROFILES["residential"]).json()
    run = client.post(f"/api/profiles/{profile['id']}/runs").json()
    return client.get(f"/api/runs/{run['id']}/listings").json()


def test_save_update_notes_and_unsave_are_idempotent(client, candidates):
    key = candidates[0]["id"]
    assert client.get("/api/saved").json() == []
    first = client.post("/api/saved", json={"listing_id": key, "note": " call owner "})
    assert first.status_code == 201 and first.json()["note"] == "call owner"
    updated = client.post("/api/saved", json={"listing_id": key, "note": "revisit"}).json()
    assert updated["saved_at"] == first.json()["saved_at"]
    assert len(client.get("/api/saved").json()) == 1
    assert client.get("/api/saved").json()[0]["note"] == "revisit"
    assert client.delete(f"/api/saved/{key}").status_code == 204
    assert client.delete(f"/api/saved/{key}").status_code == 204
    assert client.get("/api/saved").json() == []


def test_saved_rejects_unknown_property_and_oversized_note(client):
    assert client.post("/api/saved", json={"listing_id": "missing"}).status_code == 404
    assert (
        client.post("/api/saved", json={"listing_id": "x", "note": "a" * 2001}).status_code == 422
    )


def test_compare_keeps_order_and_sourced_run_snapshots_without_searches(client, candidates):
    ids = [c["id"] for c in candidates[:4]]
    before = client.get("/api/meta/budget").json()
    for size in (2, 3, 4):
        response = client.get("/api/compare", params=[("ids", key) for key in ids[:size]])
        assert response.status_code == 200
        properties = response.json()["properties"]
        assert [p["listing"]["id"] for p in properties] == ids[:size]
        for p in properties:
            assert p == client.get(f"/api/properties/{p['listing']['id']}").json()
    assert client.get("/api/meta/budget").json() == before


@pytest.mark.parametrize("ids", [[], ["a"], ["a", "a"], ["a", "b", "c", "d", "e"]])
def test_compare_requires_two_to_four_distinct_properties(client, ids):
    assert client.get("/api/compare", params=[("ids", key) for key in ids]).status_code == 422


def test_compare_unknown_property_returns_404(client):
    assert client.get("/api/compare", params=[("ids", "a"), ("ids", "b")]).status_code == 404
