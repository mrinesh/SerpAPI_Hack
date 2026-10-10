"""Conservative keyword screening of frozen, locality-matched news. No new searches."""

import re

from app.schemas.area import AreaIntel
from app.schemas.risk import RiskIndicator, RiskReport

RULES = {
    "flood": (
        r"\b(flood(?:ed|ing|s)?|waterlogging|inundat(?:ed|ion))\b",
        "Inspect flood maps, drainage and the unit's elevation with local authorities.",
    ),
    "legal": (
        r"\b(title dispute|illegal construction|encroachment|unauthori[sz]ed construction)\b",
        "Have a qualified local lawyer verify title, approvals and encumbrances for this unit.",
    ),
    "oversupply": (
        r"\b(oversupply|unsold inventory|excess housing supply)\b",
        "Check current unsold inventory and comparable rental vacancies.",
    ),
}


def assess_risk(area: AreaIntel | None) -> RiskReport:
    indicators = []
    for kind, (pattern, next_step) in RULES.items():
        matches = (
            []
            if area is None
            else [
                news
                for news in area.news
                if re.search(pattern, f"{news.title} {news.snippet or ''}", re.I)
            ]
        )
        # A mention is a lead to investigate, never a confirmed property-specific hazard.
        indicators.append(
            RiskIndicator(
                kind=kind,
                status="reported_concern" if matches else "unknown",
                score=50 if matches else None,
                evidence=[news.title for news in matches[:5]],
                sources=[news.source for news in matches[:5]],
                next_step=next_step,
            )
        )
    observed = [item.score for item in indicators if item.score is not None]
    return RiskReport(
        indicators=indicators,
        reported_concern_score=sum(observed) / len(observed) if observed else None,
        coverage_pct=round(len(observed) / 3 * 100, 1),
        note="50/100 flags a news mention for investigation, not hazard severity or probability. "
        "No matching report means unknown, not safe. Locality news does not verify a unit's "
        "flood exposure, legal title or supply risk. Rankings are unchanged.",
    )
