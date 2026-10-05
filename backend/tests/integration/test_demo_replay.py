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
