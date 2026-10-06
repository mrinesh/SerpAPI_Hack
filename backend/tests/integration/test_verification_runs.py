"""F-03 API/pipeline persistence, replay, rejects and failures over real SerpApi fixtures."""

import pytest
from sqlalchemy import select

from app.config import ProviderMode, get_settings
from app.core.errors import UpstreamError
from app.db.models import ListingRow, RunResultRow
from app.db.session import SessionLocal
from app.integrations.llm.deepseek import DeepSeekProvider
from app.integrations.llm.recorder import RecordingLLM
from app.pipeline import orchestrator
from tests.unit.test_profile_schema import RESIDENTIAL
from tests.unit.test_verification import FakeLLM


@pytest.fixture(autouse=True)
def inline(monkeypatch):
    monkeypatch.setattr(orchestrator, "_launch", orchestrator.run_pipeline)


def start(client, profile=RESIDENTIAL):
    profile_id = client.post("/api/profiles", json=profile).json()["id"]
    run_id = client.post(f"/api/profiles/{profile_id}/runs").json()["id"]
    return run_id, client.get(f"/api/runs/{run_id}").json()


def test_verifies_and_retains_rejected_candidates(client, monkeypatch):
    monkeypatch.setattr(orchestrator, "get_llm", lambda *_: FakeLLM())
    run_id, run = start(client)
    assert run["status"] == "succeeded", run
    listings = client.get(f"/api/runs/{run_id}/listings").json()
    verifications = client.get(f"/api/runs/{run_id}/verifications").json()
    limit = get_settings().verify_max_candidates
    assert len(verifications) == min(limit, len(listings))
    assert {v["listing_id"] for v in verifications} <= {listing["id"] for listing in listings}
    rejects = [v for v in verifications if v["verdict"] == "reject"]
    assert rejects and all(v["mismatches"] for v in rejects)
    checked = next(event for event in run["events"] if event["stage"] == "verify")
    assert checked["counts"]["checked"] == len(verifications)
    assert checked["counts"]["unchecked"] == len(listings) - len(verifications)
    assert checked["counts"]["rejected"] == len(rejects)
    with SessionLocal() as db:
        rows = db.scalars(select(RunResultRow).where(RunResultRow.run_id == run_id)).all()
        assert len(rows) == len(listings)
        rejected = {v["listing_id"] for v in rejects}
        ranks = sorted(row.rank for row in rows if row.rank is not None)
        # F-04 ranks every checked candidate that was not rejected; the rest stay unranked.
        assert ranks == list(range(1, len(verifications) - len(rejects) + 1))
        assert all(row.rank is None for row in rows if row.listing_id in rejected)


def test_verification_stops_at_the_per_run_limit(client, monkeypatch):
    monkeypatch.setattr(orchestrator, "get_llm", lambda *_: FakeLLM())
    monkeypatch.setattr(get_settings(), "verify_max_candidates", 3)
    run_id, run = start(client)
    assert run["status"] == "succeeded", run
    listings = client.get(f"/api/runs/{run_id}/listings").json()
    assert len(client.get(f"/api/runs/{run_id}/verifications").json()) == 3
    event = next(event for event in run["events"] if event["stage"] == "verify")
    assert event["counts"] == {
        "candidates": len(listings),
        "checked": 3,
        "rejected": event["counts"]["rejected"],
        "flagged": event["counts"]["flagged"],
        "unchecked": len(listings) - 3,
    }
    assert "limit 3 per run" in event["message"]


def test_second_candidate_failure_preserves_first_check_and_all_discovery(client, monkeypatch):
    class FailingLLM(FakeLLM):
        def generate_structured(self, **kwargs):
            if kwargs["task"] == "verify_listing" and any(
                call["task"] == "verify_listing" for call in self.calls
            ):
                raise UpstreamError("Provider temporarily unavailable")
            return super().generate_structured(**kwargs)

    monkeypatch.setattr(orchestrator, "get_llm", lambda *_: FailingLLM())
    run_id, run = start(client)
    assert run["status"] == "failed"
    assert run["error"] == "Provider temporarily unavailable"
    assert len(client.get(f"/api/runs/{run_id}/verifications").json()) == 1
    assert len(client.get(f"/api/runs/{run_id}/listings").json()) > 1
    event = next(event for event in run["events"] if event["stage"] == "verify")
    assert event["status"] == "failed" and event["counts"]["checked"] == 1


def test_recorded_run_replays_without_inner_provider(client, monkeypatch, tmp_path):
    provider = FakeLLM()
    monkeypatch.setattr(
        orchestrator,
        "get_llm",
        lambda settings, db: RecordingLLM(provider, ProviderMode.RECORD, tmp_path, db),
    )
    first_id, first = start(client)
    assert first["status"] == "succeeded"
    assert list((tmp_path / "llm" / "verify_listing").glob("*.json"))

    def forbidden(**_kwargs):
        raise AssertionError("Replay contacted the provider")

    monkeypatch.setattr(provider, "generate_structured", forbidden)
    monkeypatch.setattr(
        orchestrator,
        "get_llm",
        lambda settings, db: RecordingLLM(provider, ProviderMode.REPLAY, tmp_path, db),
    )
    second_id, second = start(client)
    assert second["status"] == "succeeded", second
    assert (
        client.get(f"/api/runs/{first_id}/verifications").json()
        == client.get(f"/api/runs/{second_id}/verifications").json()
    )


def test_run_snapshot_does_not_change_with_shared_listing(client, monkeypatch):
    monkeypatch.setattr(orchestrator, "get_llm", lambda *_: FakeLLM())
    run_id, _ = start(client)
    original = client.get(f"/api/runs/{run_id}/listings").json()
    with SessionLocal() as db:
        row = db.get(ListingRow, original[0]["id"])
        row.data = dict(row.data, name="Changed by a later run")
        db.commit()
    assert client.get(f"/api/runs/{run_id}/listings").json() == original


def test_missing_llm_fixture_fails_clearly_and_keeps_discovery(client, monkeypatch, tmp_path):
    # An empty fixture dir: the committed demo recordings would otherwise answer this profile.
    monkeypatch.setattr(
        orchestrator,
        "get_llm",
        lambda settings, db: RecordingLLM(
            DeepSeekProvider(settings), ProviderMode.REPLAY, tmp_path, db
        ),
    )
    run_id, run = start(client)
    assert run["status"] == "failed"
    assert "No recorded LLM response" in run["error"]
    assert client.get(f"/api/runs/{run_id}/listings").json()
    assert client.get(f"/api/runs/{run_id}/verifications").json() == []


def test_verifications_for_unknown_run_return_404(client):
    assert client.get("/api/runs/missing/verifications").status_code == 404


def test_recommendations_are_ranked_and_the_top_five_explained(client, monkeypatch):
    monkeypatch.setattr(orchestrator, "get_llm", lambda *_: FakeLLM())
    run_id, run = start(client)
    assert run["status"] == "succeeded", run
    recommendations = client.get(f"/api/runs/{run_id}/recommendations").json()
    assert [r["rank"] for r in recommendations] == list(range(1, len(recommendations) + 1))
    assert all(r["verification"]["verdict"] != "reject" for r in recommendations)
    scores = [r["score"] for r in recommendations]
    assert scores == sorted(scores, reverse=True)
    explained = [r["explained"] for r in recommendations]
    assert explained == [True] * min(5, len(explained)) + [False] * (len(explained) - 5)
    assert all(r["reason"].startswith(f"#{r['rank']} of ") for r in recommendations[5:])
    assert recommendations[0]["score_breakdown"]["roi"] is None
    event = next(e for e in run["events"] if e["stage"] == "rank")
    assert event["counts"] == {"ranked": len(recommendations), "explained": 5}


def test_explanation_failure_keeps_scores_and_code_reasons(client, monkeypatch):
    class FailingExplainer(FakeLLM):
        def generate_structured(self, **kwargs):
            if kwargs["task"] == "explain_recommendation":
                raise UpstreamError("Provider temporarily unavailable")
            return super().generate_structured(**kwargs)

    monkeypatch.setattr(orchestrator, "get_llm", lambda *_: FailingExplainer())
    run_id, run = start(client)
    assert run["status"] == "failed"
    assert next(e for e in run["events"] if e["stage"] == "rank")["status"] == "failed"
    recommendations = client.get(f"/api/runs/{run_id}/recommendations").json()
    assert recommendations and not any(r["explained"] for r in recommendations)


def test_recommendations_for_unknown_run_return_404(client):
    assert client.get("/api/runs/missing/recommendations").status_code == 404


def test_enrichment_builds_the_area_and_fills_the_area_score(client, monkeypatch):
    monkeypatch.setattr(orchestrator, "get_llm", lambda *_: FakeLLM())
    run_id, run = start(client)
    assert run["status"] == "succeeded", run
    [area] = client.get(f"/api/runs/{run_id}/areas").json()
    assert area["locality_key"] == "bengaluru/whitefield" and area["center"]
    assert {a["category"] for a in area["amenities"]} == {"metro", "school", "hospital"}
    assert area["price_levels"]["apartment"]["value"] > 0  # fake LLM: the run-median fallback
    assert client.get("/api/areas/bengaluru/whitefield").json()["locality"] == "Whitefield"
    top = client.get(f"/api/runs/{run_id}/recommendations").json()[0]
    assert top["score_breakdown"]["area"] is not None and top["access"]["metro_name"]
    event = next(e for e in run["events"] if e["stage"] == "enrich")
    assert event["status"] == "succeeded" and event["counts"]["localities"] == 1


def test_missing_area_data_leaves_the_area_score_empty_but_the_run_succeeds(client, monkeypatch):
    from app.pipeline.enrichment import area as area_module

    monkeypatch.setattr(orchestrator, "get_llm", lambda *_: FakeLLM())
    monkeypatch.setattr(area_module, "_search", lambda *_: None)
    run_id, run = start(client)
    assert run["status"] == "succeeded", run
    recommendations = client.get(f"/api/runs/{run_id}/recommendations").json()
    assert recommendations
    assert all(r["score_breakdown"]["area"] is None for r in recommendations)
    assert all(r["access"] is None for r in recommendations)


def test_area_routes_return_404_when_unknown(client):
    assert client.get("/api/runs/missing/areas").status_code == 404
    assert client.get("/api/areas/bengaluru/nowhere").status_code == 404


def test_missing_rent_leaves_roi_empty_but_the_run_succeeds(client, monkeypatch):
    from app.pipeline.enrichment import area as area_module

    monkeypatch.setattr(orchestrator, "get_llm", lambda *_: FakeLLM())
    monkeypatch.setattr(area_module, "rent_level", lambda *_: None)
    run_id, run = start(client)
    assert run["status"] == "succeeded", run
    recommendations = client.get(f"/api/runs/{run_id}/recommendations").json()
    assert recommendations
    for r in recommendations:
        assert r["score_breakdown"]["roi"] is None
        assert r["metrics"]["rental_yield_pct"]["value"] is None
        assert r["metrics"]["meets_target_roi"] is None
