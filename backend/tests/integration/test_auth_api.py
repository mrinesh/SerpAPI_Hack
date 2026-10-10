from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import get_settings
from app.db.base import utcnow
from app.db.models import AlertRow, AuthSessionRow, RunRow, UserRow
from app.db.session import SessionLocal
from app.main import create_app
from app.pipeline import orchestrator
from app.reference.demo_profiles import DEMO_PROFILES
from app.schemas.profile import InvestorProfileIn
from app.services import profiles
from app.services.auth import CSRF_COOKIE

PASSWORD = "correct horse battery staple"


@pytest.fixture
def accounts(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "auth_enabled", True)
    monkeypatch.setattr(get_settings(), "auth_cookie_secure", False)
    monkeypatch.setattr(orchestrator, "_launch", orchestrator.run_pipeline)
    return client


def register(client, name):
    response = client.post("/api/auth/register", json={"username": name, "password": PASSWORD})
    assert response.status_code == 201, response.text
    client.headers["X-CSRF-Token"] = client.cookies[CSRF_COOKIE]
    return response


def run(client):
    profile = client.post("/api/profiles", json=DEMO_PROFILES["residential"]).json()
    result = client.post(f"/api/profiles/{profile['id']}/runs").json()
    result = client.get(f"/api/runs/{result['id']}").json()
    assert result["status"] == "succeeded", result
    candidates = client.get(f"/api/runs/{result['id']}/listings").json()
    return profile["id"], result["id"], candidates[0]["id"]


def test_login_logout_expiry_hashes_rotation_and_csrf(accounts):
    client = accounts
    assert client.get("/api/profiles").status_code == 401
    registered = register(client, "ALICE")
    assert registered.json()["user"]["username"] == "alice"
    assert (
        "HttpOnly" in registered.headers["set-cookie"]
        and "SameSite=strict" in registered.headers["set-cookie"]
    )
    old_cookie = client.cookies["realty_session"]
    assert (
        client.post(
            "/api/profiles", json=DEMO_PROFILES["residential"], headers={"X-CSRF-Token": ""}
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/profiles",
            json=DEMO_PROFILES["residential"],
            headers={"Origin": "https://evil.example"},
        ).status_code
        == 403
    )
    login = client.post("/api/auth/login", json={"username": "alice", "password": PASSWORD})
    assert login.status_code == 200 and client.cookies["realty_session"] != old_cookie
    client.headers["X-CSRF-Token"] = client.cookies[CSRF_COOKIE]
    with SessionLocal() as db:
        user = db.scalar(select(UserRow))
        assert PASSWORD not in user.password_hash
        assert old_cookie not in str(list(db.scalars(select(AuthSessionRow.token_hash))))
    assert client.post("/api/auth/logout").status_code == 200
    client.cookies.set("realty_session", old_cookie)
    assert client.get("/api/profiles").status_code == 401
    client.cookies.clear()
    client.post("/api/auth/login", json={"username": "alice", "password": PASSWORD})
    with SessionLocal() as db:
        db.scalar(select(AuthSessionRow)).expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
    assert client.get("/api/profiles").status_code == 401
    assert client.get("/api/auth/state").json()["user"] is None


def test_users_cannot_read_mutate_or_export_each_others_data(accounts):
    alice = accounts
    register(alice, "alice")
    p1, r1, key = run(alice)
    alice.post("/api/saved", json={"listing_id": key, "note": "Alice private note"})
    saved_snapshot = alice.get("/api/saved").json()[0]
    holding = alice.post(
        "/api/portfolio",
        json={"name": "Alice home", "acquired_on": "2020-01-01", "purchase_price_inr": 1000000},
    ).json()
    with SessionLocal() as db:
        db.add(
            AlertRow(
                id="alice-alert",
                profile_id=p1,
                kind="new_match",
                listing_id=key,
                message="Alice alert",
            )
        )
        db.commit()
    with TestClient(create_app()) as bob:
        register(bob, "bob")
        assert bob.get("/api/profiles").json() == []
        assert bob.get("/api/saved").json() == [] and bob.get("/api/alerts").json() == []
        assert bob.get("/api/portfolio").json()["holdings"] == []
        for path in (
            f"/api/profiles/{p1}",
            f"/api/runs/{r1}",
            f"/api/runs/{r1}/listings",
            f"/api/runs/{r1}/development",
            f"/api/properties/{key}",
            f"/api/properties/{key}/report.pdf",
        ):
            assert bob.get(path).status_code == 404, path
        assert bob.delete(f"/api/profiles/{p1}").status_code == 404
        assert bob.post("/api/alerts/alice-alert/read").status_code == 404
        assert bob.delete("/api/portfolio/" + holding["id"]).status_code == 404
        assert bob.post("/api/saved", json={"listing_id": key}).status_code == 404
        p2, r2, key2 = run(bob)
        assert key2 == key
        assert alice.get("/api/saved").json()[0] == saved_snapshot
        detail = bob.get(f"/api/properties/{key}").json()
        assert detail["run_id"] == r2
        assert {point["run_id"] for point in detail["price_history"]} == {r2}
        assert bob.get(f"/api/properties/{key}", params={"run_id": r1}).status_code == 404
        bob.post("/api/saved", json={"listing_id": key, "note": "Bob note"})
        assert bob.get("/api/saved").json()[0]["note"] == "Bob note"
        bob.delete("/api/saved/" + key)
        assert alice.get("/api/saved").json()[0]["note"] == "Alice private note"
        before = alice.get("/api/runs/" + r1).json()
        checked = bob.post("/api/alerts/check").json()
        assert checked["checked_profiles"] == 1
        assert alice.get("/api/runs/" + r1).json() == before
        with SessionLocal() as db:
            assert len(list(db.scalars(select(RunRow).where(RunRow.profile_id == p1)))) == 1
        assert bob.delete("/api/profiles/" + p2).status_code == 204


def test_legacy_local_data_is_retained_and_not_claimed_by_first_signup(accounts, monkeypatch):
    with SessionLocal() as db:
        local = profiles.create_profile(
            db, InvestorProfileIn.model_validate(DEMO_PROFILES["residential"])
        )
    register(accounts, "alice")
    assert accounts.get("/api/profiles").json() == []
    assert accounts.get("/api/profiles/" + local.id).status_code == 404
    monkeypatch.setattr(get_settings(), "auth_enabled", False)
    assert accounts.get("/api/profiles").json()[0]["id"] == local.id


def test_credentials_throttle_and_disabled_registration(accounts):
    for _ in range(10):
        response = accounts.post(
            "/api/auth/login", json={"username": "nobody", "password": PASSWORD}
        )
        assert response.status_code == 401
    assert (
        accounts.post(
            "/api/auth/login", json={"username": "nobody", "password": PASSWORD}
        ).status_code
        == 429
    )


def test_demo_mode_still_works_and_does_not_expose_account_creation(client):
    assert client.get("/api/auth/state").json() == {"enabled": False, "user": None}
    assert (
        client.post(
            "/api/auth/register", json={"username": "alice", "password": PASSWORD}
        ).status_code
        == 403
    )
