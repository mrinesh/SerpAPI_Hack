"""Profile API: options, CRUD round trip, and the shared 422 / 404 error shapes."""

from datetime import datetime

from tests.unit.test_profile_schema import COMMERCIAL, RESIDENTIAL


def _fields(response) -> dict[str, str]:
    """{field: message} from our 422 body; loc is ["body", field, ...]."""
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    return {f["loc"][1]: f["msg"] for f in error["details"]["fields"]}


def test_profile_options_come_from_reference_data(client):
    options = client.get("/api/meta/profile-options").json()
    assert options["city"] == "Bengaluru"
    assert len(options["localities"]) == 15
    assert {"slug": "kr-puram", "name": "KR Puram"} in options["localities"]
    assert "Wikipedia" in options["locality_source"]
    assert options["max_localities"] == 5
    segments = {s["value"]: [t["label"] for t in s["property_types"]] for s in options["segments"]}
    assert segments == {
        "residential": [
            "Apartment / Flat",
            "Independent House / Villa",
            "Builder Floor",
            "Plot / Land",
        ],
        "commercial": ["Office Space", "Shop / Showroom", "Warehouse / Godown", "Commercial Land"],
    }
    assert {g["value"]: g["measure"] for g in options["goals"]} == {
        "rental_income": "rental_yield",
        "appreciation": "price_growth",
        "balanced": "total_return",
    }
    assert [r["value"] for r in options["risk_levels"]] == [
        "conservative",
        "balanced",
        "aggressive",
    ]


def test_profile_options_unknown_city_is_404(client):
    response = client.get("/api/meta/profile-options", params={"city": "Atlantis"})
    assert response.status_code == 404


def test_crud_round_trip(client):
    created = client.post("/api/profiles", json=RESIDENTIAL)
    assert created.status_code == 201
    profile = created.json()
    assert profile["roi_measure"] == "rental_yield"
    assert datetime.fromisoformat(profile["created_at"]).tzinfo is not None
    profile_id = profile["id"]

    assert client.get(f"/api/profiles/{profile_id}").json() == profile

    updated = client.put(
        f"/api/profiles/{profile_id}", json=RESIDENTIAL | {"goal": "balanced", "name": "Balanced"}
    )
    assert updated.status_code == 200
    assert updated.json()["roi_measure"] == "total_return"
    assert updated.json()["name"] == "Balanced"
    assert updated.json()["updated_at"] >= profile["updated_at"]

    assert client.delete(f"/api/profiles/{profile_id}").status_code == 204
    missing = client.get(f"/api/profiles/{profile_id}")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "not_found"


def test_list_is_most_recently_updated_first(client):
    first = client.post("/api/profiles", json=RESIDENTIAL).json()
    second = client.post("/api/profiles", json=COMMERCIAL).json()
    assert [p["id"] for p in client.get("/api/profiles").json()] == [second["id"], first["id"]]

    client.put(f"/api/profiles/{first['id']}", json=RESIDENTIAL | {"name": "Edited"})
    assert [p["id"] for p in client.get("/api/profiles").json()] == [first["id"], second["id"]]


def test_schema_errors_use_the_shared_422_shape(client):
    data = {k: v for k, v in COMMERCIAL.items() if k != "business_type"}
    response = client.post("/api/profiles", json=data)
    assert response.status_code == 422
    assert _fields(response) == {
        "business_type": "business type is required for commercial profiles"
    }


def test_unknown_locality_and_city_are_rejected(client):
    response = client.post(
        "/api/profiles", json=RESIDENTIAL | {"localities": ["whitefield", "atlantis"]}
    )
    assert response.status_code == 422
    assert _fields(response) == {"localities": "unknown localities for Bengaluru: atlantis"}

    response = client.post("/api/profiles", json=RESIDENTIAL | {"city": "Atlantis"})
    assert _fields(response) == {"city": "Atlantis is not a supported city"}


def test_update_and_delete_unknown_profile_are_404(client):
    assert client.put("/api/profiles/nope", json=RESIDENTIAL).status_code == 404
    assert client.delete("/api/profiles/nope").status_code == 404


def test_starting_a_run_for_an_unknown_profile_is_404(client):
    assert client.post("/api/profiles/nope/runs").status_code == 404
