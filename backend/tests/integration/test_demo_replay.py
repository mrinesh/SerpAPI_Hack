"""I-07 acceptance: the demo profiles run end to end from committed fixtures with no keys."""

import pytest

from app.config import get_settings
from app.pipeline import orchestrator
from app.reference.demo_profiles import DEMO_PROFILES


@pytest.fixture(autouse=True)
def inline(monkeypatch):
    monkeypatch.setattr(orchestrator, "_launch", orchestrator.run_pipeline)


@pytest.mark.parametrize("name", DEMO_PROFILES)
def test_demo_profile_replays_without_keys(client, name):
    profile_id = client.post("/api/profiles", json=DEMO_PROFILES[name]).json()["id"]
    run_id = client.post(f"/api/profiles/{profile_id}/runs").json()["id"]
    run = client.get(f"/api/runs/{run_id}").json()
    # A failure here after a prompt or schema change means: re-run scripts/record_verification.py.
    assert run["status"] == "succeeded", run["error"]
    listings = client.get(f"/api/runs/{run_id}/listings").json()
    verifications = client.get(f"/api/runs/{run_id}/verifications").json()
    assert listings
    assert len(verifications) == min(get_settings().verify_max_candidates, len(listings))
    assert {v["listing_id"] for v in verifications} <= {listing["id"] for listing in listings}
    counts = next(event for event in run["events"] if event["stage"] == "verify")["counts"]
    assert counts["checked"] == len(verifications)
    assert counts["rejected"] == sum(v["verdict"] == "reject" for v in verifications)


def test_commercial_demo_flags_the_rent_quoted_as_a_sale(client):
    """S-01's "₹3.6 Lac … ₹75 /sqft … 4,800 sqft" office, against the recorded area level."""
    profile_id = client.post("/api/profiles", json=DEMO_PROFILES["commercial"]).json()["id"]
    run_id = client.post(f"/api/profiles/{profile_id}/runs").json()["id"]
    listings = {item["id"]: item for item in client.get(f"/api/runs/{run_id}/listings").json()}
    flagged = {
        listings[v["listing_id"]]["price_inr"]["value"]: v
        for v in client.get(f"/api/runs/{run_id}/verifications").json()
        if any(flag["kind"] == "too_good_to_be_true" for flag in v["flags"])
    }
    assert list(flagged) == [360_000]
    assert flagged[360_000]["verdict"] == "weak"
    assert "₹17,501/sq ft" in flagged[360_000]["mismatches"][-1]


@pytest.mark.parametrize("name", DEMO_PROFILES)
def test_demo_recommendations_replay_with_recorded_explanations(client, name):
    profile_id = client.post("/api/profiles", json=DEMO_PROFILES[name]).json()["id"]
    run_id = client.post(f"/api/profiles/{profile_id}/runs").json()["id"]
    recommendations = client.get(f"/api/runs/{run_id}/recommendations").json()
    assert [r["rank"] for r in recommendations] == list(range(1, len(recommendations) + 1))
    assert all(r["verification"]["verdict"] != "reject" for r in recommendations)
    # Recorded explanations all pass the number guard; the rest keep code reasons.
    top = min(5, len(recommendations))
    assert [r["explained"] for r in recommendations[:top]] == [True] * top
    assert not any(r["explained"] for r in recommendations[top:])
    if name == "commercial":
        # The rent quoted as a sale (₹3.6 L, flagged) ranks last, below every genuine office.
        assert recommendations[-1]["listing"]["price_inr"]["value"] == 360_000


@pytest.mark.parametrize(("name", "growth"), [("residential", 29.0), ("commercial", 26.9)])
def test_demo_areas_replay_with_centre_amenities_growth_and_summary(client, name, growth):
    profile_id = client.post("/api/profiles", json=DEMO_PROFILES[name]).json()["id"]
    run_id = client.post(f"/api/profiles/{profile_id}/runs").json()["id"]
    [area] = client.get(f"/api/runs/{run_id}/areas").json()
    assert area["center"] and {a["category"] for a in area["amenities"]} == {
        "metro",
        "school",
        "hospital",
    }
    # Recorded quotes: "appreciated by approximately 29% in the last one year" (Whitefield),
    # "+26.9% in 1 year" (Koramangala).
    assert area["price_growth_pct"]["value"] == growth
    assert area["summary_by_ai"] and "metro" in area["infrastructure_summary"].lower()
    recommendations = client.get(f"/api/runs/{run_id}/recommendations").json()
    assert all(r["score_breakdown"]["area"] is not None for r in recommendations)


@pytest.mark.parametrize(("name", "rent"), [("residential", 32.5), ("commercial", 84.4)])
def test_demo_metrics_replay_with_recorded_rent(client, name, rent):
    profile_id = client.post("/api/profiles", json=DEMO_PROFILES[name]).json()["id"]
    run_id = client.post(f"/api/profiles/{profile_id}/runs").json()["id"]
    [area] = client.get(f"/api/runs/{run_id}/areas").json()
    assert next(iter(area["rent_levels"].values()))["value"] == rent
    recommendations = client.get(f"/api/runs/{run_id}/recommendations").json()
    for r in recommendations:
        metrics = r["metrics"]
        priced = r["listing"]["price_inr"]["value"] is not None
        flagged = any(f["kind"] == "too_good_to_be_true" for f in r["verification"]["flags"])
        has_rate = priced and (
            r["listing"]["price_per_sqft"]["value"] or r["listing"]["size_sqft"]["value"]
        )
        assert (metrics["rental_yield_pct"]["value"] is not None) == bool(has_rate and not flagged)
        assert (r["score_breakdown"]["roi"] is None) == (metrics["meets_target_roi"] is None)
    # Recorded: Sowparnika Columns, ₹8,185/sq ft against ₹32.5/sq ft/month -> 4.76%, meets the
    # suggested 3%. Its rank depends on the recorded relevance checks; only its metrics are pinned.
    if name == "residential":
        [sowparnika] = [r for r in recommendations if r["listing"]["name"] == "Sowparnika Columns"]
        assert sowparnika["rank"] <= 3
        assert sowparnika["metrics"]["rental_yield_pct"]["value"] == 4.76
        assert sowparnika["metrics"]["meets_target_roi"] is True


@pytest.mark.parametrize("name", DEMO_PROFILES)
def test_demo_targets_are_the_wizards_suggestions(client, name):
    profile = DEMO_PROFILES[name]
    keys = ("segment", "property_types", "localities", "goal", "risk_appetite")
    response = client.post(
        "/api/profiles/target-suggestion", json={key: profile[key] for key in keys}
    )
    assert response.status_code == 200
    suggestion = response.json()
    assert suggestion["target_roi_pct"] == profile["target_roi_pct"]
    assert suggestion["parts"][0]["typical"]["sources"], "the suggestion must be sourced"


def test_suggestion_without_recorded_data_is_empty_not_an_error(client):
    body = {
        "segment": "residential",
        "property_types": ["apartment"],
        "localities": ["hebbal"],
        "goal": "rental_income",
        "risk_appetite": "balanced",
    }
    suggestion = client.post("/api/profiles/target-suggestion", json=body).json()
    assert suggestion["target_roi_pct"] is None and suggestion["parts"] == []


def test_suggestion_rejects_unknown_localities(client):
    body = {
        "segment": "residential",
        "property_types": ["apartment"],
        "localities": ["atlantis"],
        "goal": "rental_income",
        "risk_appetite": "balanced",
    }
    assert client.post("/api/profiles/target-suggestion", json=body).status_code == 422
