"""Discovery runs end to end, in replay mode against the recorded S-01 fixtures (no credits)."""

import pytest

from app.pipeline import orchestrator
from tests.unit.test_profile_schema import COMMERCIAL, RESIDENTIAL


@pytest.fixture(autouse=True)
def run_inline(monkeypatch):
    """Run the pipeline inside the request instead of on a background thread."""
    monkeypatch.setattr(orchestrator, "_launch", orchestrator.run_pipeline)


def run_for(client, profile: dict) -> tuple[dict, list[dict]]:
    profile_id = client.post("/api/profiles", json=profile).json()["id"]
    started = client.post(f"/api/profiles/{profile_id}/runs")
    assert started.status_code == 202
    run_id = started.json()["id"]
    run = client.get(f"/api/runs/{run_id}").json()
    listings = client.get(f"/api/runs/{run_id}/listings").json()
    return run, listings


def stages(run: dict) -> dict[str, str]:
    return {e["stage"]: e["status"] for e in run["events"]}


def test_residential_run_finds_priced_entries_and_projects(client):
    # Whitefield, apartment, up to 80 L: exactly the recorded spike searches #5 and #16.
    run, listings = run_for(client, RESIDENTIAL | {"budget_max_inr": 8_000_000})
    assert run["status"] == "succeeded", run
    assert stages(run) == {
        "plan": "succeeded",
        "fetch": "succeeded",
        "clean": "succeeded",
        "verify": "pending",
        "enrich": "pending",
        "rank": "pending",
    }
    assert (run["searches_used"], run["cache_hits"]) == (0, 2)  # replay never spends

    entries = [item for item in listings if item["kind"] == "snippet_entry"]
    projects = [item for item in listings if item["kind"] == "project"]
    assert entries and projects
    assert all(e["price_inr"]["value"] > 0 for e in entries)
    assert all(e["portal"] in {"99acres", "magicbricks", "nobroker"} for e in entries)
    assert all(e["sources"][0]["search_id"] for e in listings)
    names = {e["name"] for e in entries}
    assert "Sowparnika Columns" in names
    sowparnika = next(e for e in entries if e["name"] == "Sowparnika Columns")
    assert sowparnika["price_inr"]["value"] == 6_000_000
    assert sowparnika["url"].startswith("https://www.99acres.com/")
    gopalan = next(p for p in projects if p["name"] == "Gopalan Atlantis")
    assert gopalan["location"]["value"] == {
        "lat": pytest.approx(12.9747, abs=1e-3),
        "lng": pytest.approx(77.7440, abs=1e-3),
    }
    assert gopalan["url"].startswith("https://www.google.com/maps/search/?api=1")
    prices = [e["price_inr"]["value"] for e in entries]
    assert prices == sorted(prices)  # cheapest first


def test_commercial_run_skips_maps(client):
    profile = COMMERCIAL | {
        "property_types": ["office"],
        "localities": ["koramangala"],
        "budget_max_inr": 30_000_000,
    }
    run, listings = run_for(client, profile)
    assert run["status"] == "succeeded"
    assert run["cache_hits"] == 1
    assert listings and {item["kind"] for item in listings} == {"snippet_entry"}


def test_unrecorded_searches_are_reported_and_recorded_ones_still_used(client):
    # Hebbal's Google search was recorded (#22); Hebbal Maps and Electronic City under 1 crore
    # were not.
    run, listings = run_for(
        client,
        RESIDENTIAL | {"localities": ["hebbal", "electronic-city"], "budget_max_inr": 10_000_000},
    )
    assert run["status"] == "succeeded"
    fetch = next(e for e in run["events"] if e["stage"] == "fetch")
    assert "No recorded google_maps response" in fetch["message"]
    assert listings and all(item["locality"]["value"] == "hebbal" for item in listings)


def test_run_with_nothing_recorded_fails_with_a_clear_message(client):
    run, listings = run_for(
        client, RESIDENTIAL | {"property_types": ["house_villa"], "localities": ["malleswaram"]}
    )
    assert run["status"] == "failed"
    assert "No recorded google response" in run["error"]
    assert stages(run)["fetch"] == "failed" and listings == []


def test_repeat_runs_reuse_listing_ids(client):
    first, first_listings = run_for(client, RESIDENTIAL)
    second, second_listings = run_for(client, RESIDENTIAL)
    assert {item["id"] for item in first_listings} == {item["id"] for item in second_listings}
    assert first["id"] != second["id"]


def test_deleting_a_profile_removes_its_runs(client):
    profile_id = client.post("/api/profiles", json=RESIDENTIAL).json()["id"]
    run_id = client.post(f"/api/profiles/{profile_id}/runs").json()["id"]
    assert client.delete(f"/api/profiles/{profile_id}").status_code == 204
    assert client.get(f"/api/runs/{run_id}").status_code == 404
