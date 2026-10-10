from io import BytesIO

from pypdf import PdfReader

from app.pipeline import orchestrator
from app.reference.demo_profiles import DEMO_PROFILES


def test_pdf_contains_frozen_values_sources_and_unknowns_without_searches(client, monkeypatch):
    monkeypatch.setattr(orchestrator, "_launch", orchestrator.run_pipeline)
    profile = client.post("/api/profiles", json=DEMO_PROFILES["residential"]).json()
    run = client.post(f"/api/profiles/{profile['id']}/runs").json()
    candidate = client.get(f"/api/runs/{run['id']}/listings").json()[0]
    before = client.get("/api/meta/budget").json()
    response = client.get(
        f"/api/properties/{candidate['id']}/report.pdf", params={"run_id": run["id"]}
    )
    assert response.status_code == 200 and response.headers["content-type"] == "application/pdf"
    pages = PdfReader(BytesIO(response.content)).pages
    text = "\n".join(page.extract_text() for page in pages)
    assert candidate["name"] in text and run["id"] in text
    assert "Sources" in text and "unknown" in text and "https://" in text
    assert "confidence" in text and "before costs" in text
    assert client.get("/api/meta/budget").json() == before


def test_pdf_unknown_property_returns_structured_404(client):
    assert client.get("/api/properties/missing/report.pdf").status_code == 404
