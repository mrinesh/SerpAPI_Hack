"""F-03 API/pipeline persistence, replay, rejects and failures over real SerpApi fixtures."""

import pytest
from sqlalchemy import select

from app.config import ProviderMode
from app.core.errors import UpstreamError
from app.db.models import ListingRow, RunResultRow
from app.db.session import SessionLocal
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
    assert {v["listing_id"] for v in verifications} == {listing["id"] for listing in listings}
    rejects = [v for v in verifications if v["verdict"] == "reject"]
    assert rejects and all(v["mismatches"] for v in rejects)
    checked = next(event for event in run["events"] if event["stage"] == "verify")
    assert checked["counts"]["checked"] == len(listings)
    assert checked["counts"]["rejected"] == len(rejects)
    with SessionLocal() as db:
        rows = db.scalars(select(RunResultRow).where(RunResultRow.run_id == run_id)).all()
        assert len(rows) == len(listings) and all(row.rank is None for row in rows)


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


def test_missing_llm_fixture_fails_clearly_and_keeps_discovery(client):
    run_id, run = start(client)
    assert run["status"] == "failed"
    assert "No recorded LLM response" in run["error"]
    assert client.get(f"/api/runs/{run_id}/listings").json()
    assert client.get(f"/api/runs/{run_id}/verifications").json() == []


def test_verifications_for_unknown_run_return_404(client):
    assert client.get("/api/runs/missing/verifications").status_code == 404
