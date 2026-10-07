"""Real replay, frozen API snapshots and actual deduplicated app search intents."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.db.models import RunDevelopmentRow, RunRow, SearchIntentRow
from app.db.session import SessionLocal
from app.pipeline import orchestrator
from app.pipeline.enrichment.search_history import app_history
from app.reference.demo_profiles import DEMO_PROFILES
from app.schemas.profile import InvestorProfileIn
from app.services.profiles import create_profile


@pytest.mark.parametrize("name", DEMO_PROFILES)
def test_actual_demo_history_sources_read_only_snapshot_and_no_forced_priority(
    client, monkeypatch, name
):
    monkeypatch.setattr(orchestrator, "_launch", orchestrator.run_pipeline)
    profile = DEMO_PROFILES[name]
    profile_id = client.post("/api/profiles", json=profile).json()["id"]
    run_id = client.post(f"/api/profiles/{profile_id}/runs").json()["id"]
    run = client.get(f"/api/runs/{run_id}").json()
    assert run["status"] == "succeeded", run["error"]
    reports = client.get(f"/api/runs/{run_id}/development").json()
    assert len(reports) == 1
    report = reports[0]
    assert report["signal"] == "no_sustained_growth" and report["rank"] is None
    assert not report["warnings"] and report["ai_review"] != "unavailable"
    assert len(report["public_interest"]) == 2
    for signal in report["public_interest"]:
        assert len(signal["history"]) == 104 and signal["usable"]
        assert signal["source"]["search_id"] and signal["retrieved_at"]
        assert signal["geo"] == "IN-KA" and signal["annual_change_pct"] is not None
    rental = next(s for s in report["public_interest"] if s["kind"] == "rental_interest")
    assert rental["signal"] == "falling" and rental["quarter_change_pct"] < -15
    assert not report["app_interest"]["usable"] and not report["app_interest"]["history"]
    for item in report["hypotheses"]:
        assert item["evidence"]["sources"][0]["url"]
        assert "not demonstrated causation" in item["explanation"]
    event = next(e for e in run["events"] if e["stage"] == "enrich")
    assert event["counts"]["development"] == 1 and event["counts"]["development_warnings"] == 0
    assert run["searches_used"] == 0
    assert (
        client.put(
            f"/api/profiles/{profile_id}", json=dict(profile, localities=["indiranagar"])
        ).status_code
        == 200
    )
    with SessionLocal() as db:
        assert db.scalar(select(SearchIntentRow.locality_key)) == report["locality_key"]
        assert db.scalar(select(func.count()).select_from(RunDevelopmentRow)) == 1
    assert client.get(f"/api/runs/{run_id}/development").json() == reports
    assert client.get(f"/api/runs/{run_id}").json()["cache_hits"] == run["cache_hits"]
    assert client.delete(f"/api/profiles/{profile_id}").status_code == 204
    assert client.get(f"/api/runs/{run_id}/development").status_code == 404
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(SearchIntentRow)) == 0
        assert db.scalar(select(func.count()).select_from(RunDevelopmentRow)) == 0


def test_pending_and_missing_report_contract_and_recorded_intent(client, monkeypatch):
    monkeypatch.setattr(orchestrator, "_launch", lambda _: None)
    assert client.get("/api/runs/missing/development").status_code == 404
    profile_id = client.post("/api/profiles", json=DEMO_PROFILES["residential"]).json()["id"]
    run_id = client.post(f"/api/profiles/{profile_id}/runs").json()["id"]
    assert client.get(f"/api/runs/{run_id}/development").json() == []
    with SessionLocal() as db:
        assert db.scalar(select(SearchIntentRow)).profile_id == profile_id
    assert "/api/runs/{run_id}/development" in client.get("/openapi.json").json()["paths"]


def test_app_aggregation_deduplicates_reruns_excludes_partial_weeks_and_handles_gaps(db):
    now = datetime(2026, 10, 7, tzinfo=UTC)
    current = datetime(2026, 10, 5, tzinfo=UTC)  # Monday
    beginning = current - timedelta(weeks=66)
    profiles = [
        create_profile(db, InvestorProfileIn.model_validate(DEMO_PROFILES["residential"]))
        for _ in range(6)
    ]

    def intent(profile, when, locality="bengaluru/whitefield"):
        row = RunRow(profile_id=profile.id, status="pending", events=[])
        db.add(row)
        db.flush()
        db.add(
            SearchIntentRow(
                run_id=row.id, profile_id=profile.id, locality_key=locality, created_at=when
            )
        )

    intent(profiles[0], beginning + timedelta(days=4))  # initial partial week
    for week in range(1, 66):
        for profile in profiles[: 2 if week < 53 else 6]:
            intent(profile, beginning + timedelta(weeks=week, days=1))
        intent(profiles[0], beginning + timedelta(weeks=week, days=2))  # rerun
    intent(profiles[0], current + timedelta(days=1))  # current partial week
    db.commit()
    result = app_history(db, "bengaluru/whitefield", now=now)
    assert len(result.history) == 65 and result.sample_size == 6
    assert result.history[-1].value == 6 and result.history[0].value == 2
    assert result.quarter_change_pct == 200 and result.annual_change_pct == 200
    assert result.usable and result.signal == "rising"
    # A locality without searches has observed zero weeks only since actual collection began.
    empty = app_history(db, "bengaluru/indiranagar", now=now)
    assert len(empty.history) == 65 and all(p.value == 0 for p in empty.history)
    assert not empty.usable and empty.quarter_change_pct is None
    assert "profile_id" not in result.model_dump_json()
