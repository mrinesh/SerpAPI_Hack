"""Composite ranking, code reasons and the number guard on LLM explanations (F-04, ADR 0015)."""

import pytest

from app.pipeline.ranking import (
    COMPONENTS,
    Explanation,
    composite,
    display_figures,
    explain,
    guard,
    inr_short,
    score_candidates,
    value_score,
    weights_for,
)
from app.reference import load_market
from app.schemas.common import Level
from app.schemas.listing import MatchVerdict, QualityFlag, QualityFlagKind, Verification
from app.schemas.profile import InvestmentGoal, RiskAppetite
from app.schemas.provenance import ExtractionMethod, Sourced
from tests.unit.test_verification import FakeLLM, candidate, context

LEVEL = Sourced(value=10_000.0, confidence=0.7, method=ExtractionMethod.LLM)
MARKET = load_market("Bengaluru")


def checked(listing_id="a", score=70, verdict="partial", confidence=0.6, flags=(), **listing):
    item = candidate(id=listing_id, **listing)
    check = Verification(
        listing_id=listing_id,
        match_score=score,
        verdict=verdict,
        confidence=confidence,
        model="fake",
        flags=list(flags),
    )
    return item, check


def levels():
    return {("whitefield", "apartment"): LEVEL}


@pytest.mark.parametrize("goal", list(InvestmentGoal))
@pytest.mark.parametrize("risk", list(RiskAppetite))
def test_weights_cover_every_component_and_sum_to_100(goal, risk):
    weights = weights_for(goal, risk)
    assert set(weights) == set(COMPONENTS) and sum(weights.values()) == 100
    assert all(weight > 0 for weight in weights.values())


def test_risk_appetite_moves_weight_between_evidence_and_value():
    conservative = weights_for(InvestmentGoal.BALANCED, RiskAppetite.CONSERVATIVE)
    aggressive = weights_for(InvestmentGoal.BALANCED, RiskAppetite.AGGRESSIVE)
    assert conservative["evidence"] > aggressive["evidence"]
    assert aggressive["value"] > conservative["value"]


def test_missing_components_are_left_out_and_the_rest_renormalised():
    parts = {"relevance": 80.0, "roi": None, "value": 50.0, "evidence": 60.0, "area": None}
    score, breakdown = composite(parts, weights_for("balanced", "balanced"), 0)
    assert breakdown["roi"] is None and breakdown["area"] is None
    # relevance 40, value 20, evidence 12 -> shares of 72
    assert breakdown["relevance"] == round(40 / 72 * 80, 1)
    assert score == round(40 / 72 * 80 + 20 / 72 * 50 + 12 / 72 * 60, 1)


@pytest.mark.parametrize(("rate", "expected"), [(6_000, 100), (10_000, 50), (14_000, 0)])
def test_value_curve_is_50_at_the_area_level(rate, expected):
    item, check = checked()
    item.price_inr.value = None
    item.price_per_sqft = Sourced(value=rate, confidence=0.8, method=ExtractionMethod.REGEX)
    assert value_score(item, check, LEVEL) == pytest.approx(expected)


def test_value_needs_a_rate_and_a_level():
    item, check = checked()
    item.price_inr.value = None
    assert value_score(item, check, LEVEL) is None
    assert value_score(*checked(), None) is None


TOO_GOOD = QualityFlag(kind=QualityFlagKind.TOO_GOOD_TO_BE_TRUE, severity=Level.HIGH, reason="x")


def test_a_suspicious_bargain_gets_no_value_points_and_a_penalty():
    item, check = checked(flags=[TOO_GOOD])
    assert value_score(item, check, LEVEL) is None
    [ranked] = score_candidates(context().profile, [(item, check)], levels(), MARKET)
    assert ranked.score_breakdown["value"] is None
    assert ranked.score_breakdown["flag_penalty"] == -25


def test_rejects_are_not_ranked_and_ties_are_deterministic():
    items = [
        checked("b", score=70),
        checked("a", score=70),
        checked("c", score=90, verdict="reject"),
        checked("d", score=40, verdict="weak"),
    ]
    ranked = score_candidates(context().profile, items, levels(), MARKET)
    assert [r.listing.id for r in ranked] == ["a", "b", "d"]
    assert [r.rank for r in ranked] == [1, 2, 3]


def test_code_reason_states_rank_match_and_price_against_the_area():
    [ranked] = score_candidates(context().profile, [checked()], levels(), MARKET)
    # candidate(): ₹60 L for 1,000 sq ft = ₹6,000/sq ft against ₹10,000/sq ft.
    assert ranked.reason == (
        "#1 of 1: partial match, relevance 70/100. "
        "Quoted at ₹60 L, 40% below Whitefield's ₹10,000/sq ft level."
    )
    assert not ranked.explained


def test_code_reason_without_a_price():
    item, check = checked(verdict="weak")
    item.price_inr.value = None
    [ranked] = score_candidates(context().profile, [(item, check)], levels(), MARKET)
    assert ranked.reason.endswith("No price is quoted yet.")


@pytest.mark.parametrize(
    ("value", "text"),
    [(7_600_000, "₹76 L"), (11_500_000, "₹1.15 Cr"), (230_000_000, "₹23 Cr"), (45_000, "₹45,000")],
)
def test_inr_short(value, text):
    assert inr_short(value) == text


def ranked_one():
    [ranked] = score_candidates(context().profile, [checked()], levels(), MARKET)
    return ranked


def figures():
    return display_figures(ranked_one(), 1, LEVEL, "Whitefield", context().profile)


def test_display_figures_include_the_budget_and_target():
    shown = figures()
    assert shown["price"] == "₹60 L" and shown["rate"] == "₹6,000/sq ft"
    assert shown["budget"] == "up to ₹80 L" and shown["target_roi"] == "4% target ROI"


def test_guard_keeps_an_explanation_that_quotes_only_given_figures():
    explanation = Explanation(
        reason="At ₹60 L and ₹6,000/sq ft it is 40% below the ₹10,000/sq ft level.",
        highlights=["Within the up to ₹80 L budget"],
        risks=["Rank #1 of 1 rests on a snippet"],
    )
    reason, highlights, risks, explained = guard(explanation, figures(), "fallback")
    assert explained and reason.startswith("At ₹60 L") and highlights and risks


def test_guard_falls_back_when_the_reason_invents_a_number():
    explanation = Explanation(
        reason="Expected rent of ₹25,000 a month gives a 5% yield.",
        highlights=["A 3.2% yield", "Within budget"],
        risks=[],
    )
    reason, highlights, _, explained = guard(explanation, figures(), "fallback")
    assert (reason, explained) == ("fallback", False)
    assert highlights == ["Within budget"]


def test_explain_uses_the_lite_tier_and_never_sends_profile_identity():
    llm = FakeLLM()
    result = explain(context(llm), ranked_one(), 1, LEVEL, "Whitefield")
    call = next(c for c in llm.calls if c["task"] == "explain_recommendation")
    assert call["tier"] == "lite"
    assert "profile-1" not in call["prompt"]
    assert result.explained and result.reason == "A fake explanation without numbers."


def test_verdict_words_cover_every_rankable_verdict():
    for verdict in (MatchVerdict.STRONG, MatchVerdict.PARTIAL, MatchVerdict.WEAK):
        [ranked] = score_candidates(context().profile, [checked(verdict=verdict)], {}, MARKET)
        assert ranked.reason
