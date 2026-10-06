"""Investor profiles the committed fixtures cover end to end (S-01 searches, F-03 LLM recordings).

`scripts/record_verification.py` records with these and `tests/integration/test_demo_replay.py`
replays them with no keys, so changing a value here means re-recording.
"""

_RESIDENTIAL = {
    "name": "Whitefield demo",
    "segment": "residential",
    "property_types": ["apartment"],
    "localities": ["whitefield"],
    "budget_max_inr": 8_000_000,
    "goal": "rental_income",
    "target_roi_pct": 4,
    "risk_appetite": "balanced",
}

DEMO_PROFILES: dict[str, dict] = {
    "residential": _RESIDENTIAL,
    "commercial": _RESIDENTIAL
    | {
        "name": "Koramangala office demo",
        "segment": "commercial",
        "property_types": ["office"],
        "localities": ["koramangala"],
        "budget_max_inr": 30_000_000,
        "business_type": "IT services",
    },
}
