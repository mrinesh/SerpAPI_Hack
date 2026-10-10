"""Bounded phrase parser: typed draft plus exact evidence, never an automatic saved profile."""

import re
from decimal import Decimal

from app.core.errors import InvalidInput
from app.reference import load_market
from app.schemas.language import LanguageProfileIn, LanguageProfileResult, ProfileDraft
from app.schemas.profile import (
    MAX_LOCALITIES,
    SEGMENT_PROPERTY_TYPES,
    InvestmentGoal,
    PropertyType,
    RiskAppetite,
    Segment,
)

TYPES = {
    "apartment": r"apartments?|flats?",
    "house_villa": r"villas?|independent houses?",
    "builder_floor": r"builder floors?",
    "plot": r"plots?|residential land",
    "office": r"offices?(?: space)?",
    "shop_showroom": r"shops?|showrooms?",
    "warehouse": r"warehouses?|godowns?",
    "commercial_land": r"commercial land",
}
MONEY = (
    r"(?:INR\s*|Rs\.?\s*|₹\s*)?(\d[\d,]*(?:\.\d+)?)\s*(crores?|cr|lakhs?|lacs?|lakh|lac|rupees?)"
)
NEGATION = re.compile(
    r"\b(?:not|avoid|exclude|no|without|don't want|do not want)\s+(?:an?\s+)?$", re.I
)


def parse_profile(data: LanguageProfileIn) -> LanguageProfileResult:
    market = load_market(data.city)
    if market is None:
        raise InvalidInput(["body", "city"], "Unsupported city")
    text = data.text.strip()
    if not text:
        raise InvalidInput(["body", "text"], "Describe your search criteria")
    draft = ProfileDraft()
    evidence = {}
    unresolved = []

    def matches(pattern):
        found = list(re.finditer(r"\b(?:" + pattern + r")\b", text, re.I))
        return [m for m in found if not NEGATION.search(text[max(0, m.start() - 25) : m.start()])]

    for kind, pattern in TYPES.items():
        found = matches(pattern)
        if found:
            draft.property_types.append(PropertyType(kind))
            evidence["property_type:" + kind] = found[0].group()
    segments = {
        s
        for s, types in SEGMENT_PROPERTY_TYPES.items()
        if any(t in types for t in draft.property_types)
    }
    if len(segments) == 1:
        draft.segment = segments.pop()
    elif len(segments) > 1:
        draft.property_types = []
        unresolved.append("Mixed residential/commercial types: choose one segment in the form.")
    for place in market.localities:
        found = matches("|".join(re.escape(name) for name in (place.name, *place.aliases)))
        if found:
            draft.localities.append(place.slug)
            evidence["locality:" + place.slug] = found[0].group()
    if len(draft.localities) > MAX_LOCALITIES:
        draft.localities = []
        unresolved.append(f"Choose at most {MAX_LOCALITIES} localities.")

    def amount(number, unit):
        scale = (
            10000000
            if unit.lower().startswith("cr")
            else 100000
            if unit.lower().startswith(("la", "lac"))
            else 1
        )
        value = Decimal(number.replace(",", "")) * scale
        return int(value) if 0 <= value <= 1e12 else None

    budget = re.search(
        r"\b(?:under|below|up to|max(?:imum)? budget(?: of)?|budget(?: of)?)\s*" + MONEY, text, re.I
    )
    price_range = re.search(
        r"\b(?:between|budget(?: of)?|from)\s*" + MONEY + r"\s*(?:to|and|-)\s*" + MONEY, text, re.I
    )
    if price_range:
        low = amount(price_range[1], price_range[2])
        high = amount(price_range[3], price_range[4])
        if low is not None and high is not None and 0 <= low <= high and high > 0:
            draft.budget_min_inr, draft.budget_max_inr = low, high
            evidence["budget"] = price_range.group()
        else:
            unresolved.append("Budget range is invalid; enter it in the form.")
    elif budget:
        value = amount(budget[1], budget[2])
        if value is not None and value > 0:
            draft.budget_max_inr = value
            evidence["budget"] = budget.group()
    for field, pattern in {
        "goal": r"rental income|appreciation|balanced returns?",
        "risk_appetite": r"low risk|conservative|balanced risk|moderate risk|high risk|aggressive",
    }.items():
        found = matches(pattern)
        mapping = {
            "rental income": "rental_income",
            "appreciation": "appreciation",
            "low risk": "conservative",
            "conservative": "conservative",
            "high risk": "aggressive",
            "aggressive": "aggressive",
        }
        values = {mapping.get(m.group().lower(), "balanced") for m in found}
        if len(values) == 1:
            enum_type = InvestmentGoal if field == "goal" else RiskAppetite
            setattr(draft, field, enum_type(values.pop()))
            evidence[field] = found[0].group()
        elif len(values) > 1:
            unresolved.append(f"Conflicting {field.replace('_', ' ')} phrases; choose in the form.")
    roi = re.search(r"\btarget\s+(?:roi\s*)?(\d+(?:\.\d+)?)\s*%", text, re.I)
    if roi and 0 <= float(roi[1]) <= 100:
        draft.target_roi_pct = float(roi[1])
        evidence["target_roi_pct"] = roi.group()
    for field, cue in (
        ("size_min_sqft", r"at least|minimum size(?: of)?"),
        ("size_max_sqft", r"up to|maximum size(?: of)?"),
    ):
        size = re.search(r"\b(?:" + cue + r")\s*(\d[\d,]*)\s*(?:sq\.?\s*ft|sqft)\b", text, re.I)
        if size and int(size[1].replace(",", "")) > 0:
            setattr(draft, field, int(size[1].replace(",", "")))
            evidence[field] = size.group()
    if draft.segment == Segment.COMMERCIAL:
        business = matches("|".join(re.escape(v) for v in market.business_type_suggestions))
        if len({m.group().lower() for m in business}) == 1:
            draft.business_type = business[0].group().lower()
            evidence["business_type"] = business[0].group()
    if matches(r"near metro"):
        draft.must_haves.append("near metro")
        evidence["must_haves"] = "near metro"
    for field in (
        "segment",
        "localities",
        "budget_max_inr",
        "goal",
        "risk_appetite",
        "target_roi_pct",
    ):
        if getattr(draft, field) is None or getattr(draft, field) == []:
            unresolved.append(f"Complete {field.replace('_', ' ')} in the form.")
    if draft.segment == Segment.COMMERCIAL and draft.business_type is None:
        unresolved.append("Complete business type in the form.")
    return LanguageProfileResult(draft=draft, matched_phrases=evidence, unresolved=unresolved)
