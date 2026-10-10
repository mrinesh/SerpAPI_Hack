import warnings

from app.schemas.language import LanguageProfileIn
from app.services.language import parse_profile


def test_recognized_criteria_have_exact_evidence_and_do_not_invent_missing_fields():
    text = "Flat in Whitefield under 90 lakh, rental income, low risk, target ROI 6%, near metro"
    result = parse_profile(LanguageProfileIn(text=text))
    assert result.draft.localities == ["whitefield"]
    assert result.draft.budget_max_inr == 9000000
    assert result.draft.goal == "rental_income" and result.draft.target_roi_pct == 6
    assert result.draft.risk_appetite == "conservative"
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert '"apartment"' in result.model_dump_json()
    assert all(phrase.lower() in text.lower() for phrase in result.matched_phrases.values())
    unknown = parse_profile(LanguageProfileIn(text="somewhere nice"))
    assert unknown.draft.budget_max_inr is None and unknown.unresolved


def test_negations_conflicts_ranges_and_commercial_business():
    result = parse_profile(
        LanguageProfileIn(text="Not Whitefield, flat in Koramangala, budget 80 lakh to 1 crore")
    )
    assert result.draft.localities == ["koramangala"]
    assert result.draft.budget_min_inr == 8000000 and result.draft.budget_max_inr == 10000000
    result = parse_profile(
        LanguageProfileIn(text="Flat or office in Whitefield, low risk or aggressive")
    )
    assert result.draft.segment is None and result.draft.risk_appetite is None
    result = parse_profile(LanguageProfileIn(text="Shop for cafe in Indiranagar under 2 crore"))
    assert result.draft.segment == "commercial" and result.draft.business_type == "cafe"


def test_parser_does_not_confuse_size_with_price_or_make_roi_assumptions():
    result = parse_profile(
        LanguageProfileIn(text="Apartment in Whitefield up to 1500 sqft, at least 1000 sqft")
    )
    assert result.draft.size_min_sqft == 1000 and result.draft.size_max_sqft == 1500
    assert result.draft.budget_max_inr is None and result.draft.target_roi_pct is None
