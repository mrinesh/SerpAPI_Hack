from app.db.models import RunResultRow, RunRow
from app.db.session import SessionLocal
from app.pipeline import orchestrator
from app.pipeline.persist import save_candidates
from app.reference.demo_profiles import DEMO_PROFILES
from app.services import alerts
from tests.unit.test_alert_diff import listing


def test_first_check_creates_verified_matches_and_repeat_does_not_duplicate(client):
    profile = client.post("/api/profiles", json=DEMO_PROFILES["residential"]).json()
    first = client.post("/api/alerts/check")
    assert first.status_code == 200
    result = first.json()
    assert result["checked_profiles"] == 1 and result["errors"] == []
    assert result["alerts"] and {a["kind"] for a in result["alerts"]} == {"new_match"}
    assert {a["profile_id"] for a in result["alerts"]} == {profile["id"]}
    before = client.get("/api/alerts").json()
    assert client.post("/api/alerts/check").json()["alerts"] == []
    assert client.get("/api/alerts").json() == before
    key = before[0]["id"]
    marked = client.post(f"/api/alerts/{key}/read").json()
    assert marked["read_at"] is not None
    assert client.post(f"/api/alerts/{key}/read").json() == marked
    assert len(client.get("/api/alerts?unread_only=true").json()) == len(before) - 1
    assert client.post("/api/alerts/missing/read").status_code == 404
    assert client.get("/api/meta/budget").json()["used_this_month"] == 0


def test_failed_refresh_does_not_emit_alerts(client):
    data = {**DEMO_PROFILES["residential"], "localities": ["hebbal"]}
    client.post("/api/profiles", json=data)
    result = client.post("/api/alerts/check").json()
    assert result["checked_profiles"] == 0 and result["errors"]
    assert result["alerts"] == [] and client.get("/api/alerts").json() == []


def test_busy_check_returns_conflict_and_does_not_start_runs(client):
    alerts._check_lock.acquire()
    try:
        response = client.post("/api/alerts/check")
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "alert_check_busy"
    finally:
        alerts._check_lock.release()


def test_active_profiles_are_skipped(client, monkeypatch):
    monkeypatch.setattr(orchestrator, "_launch", lambda _: None)
    profile = client.post("/api/profiles", json=DEMO_PROFILES["residential"]).json()
    client.post(f"/api/profiles/{profile['id']}/runs")
    result = client.post("/api/alerts/check").json()
    assert result["skipped_profiles"] == 1 and result["checked_profiles"] == 0


def test_profile_failure_does_not_prevent_other_checks(client, monkeypatch):
    client.post("/api/profiles", json=DEMO_PROFILES["residential"])
    client.post("/api/profiles", json=DEMO_PROFILES["commercial"])
    original = alerts.start_run
    calls = []

    def fail_once(db, key, **kwargs):
        calls.append(key)
        if len(calls) == 1:
            raise RuntimeError("synthetic failure")
        return original(db, key, **kwargs)

    monkeypatch.setattr(alerts, "start_run", fail_once)
    with SessionLocal() as db:
        result = alerts.check_alerts(db)
    assert result.checked_profiles == 1 and len(result.errors) == 1
    assert result.alerts


def test_price_drop_is_persisted_for_changed_candidate_id(client, monkeypatch):
    profile = client.post("/api/profiles", json=DEMO_PROFILES["residential"]).json()

    def stored_run(db, item):
        run = RunRow(profile_id=profile["id"], status="succeeded", events=[])
        db.add(run)
        db.commit()
        save_candidates(db, run.id, [item])
        row = db.query(RunResultRow).filter_by(run_id=run.id, listing_id=item.id).one()
        row.recommendation = {**row.recommendation, "verification": {"verdict": "partial"}}
        db.commit()
        return run

    with SessionLocal() as db:
        stored_run(db, listing())
    monkeypatch.setattr(
        alerts, "start_run", lambda db, key, **kw: stored_run(db, listing("new", 5_000_000))
    )
    result = client.post("/api/alerts/check").json()
    assert result["errors"] == []
    [alert] = result["alerts"]
    assert alert["kind"] == "price_drop" and alert["listing_id"] == "new"
    assert client.get("/api/alerts").json() == [alert]
