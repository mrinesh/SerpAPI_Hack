from pydantic import BaseModel, Field

from app.schemas.profile import InvestmentGoal, PropertyType, RiskAppetite, Segment


class LanguageProfileIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    city: str = "Bengaluru"


class ProfileDraft(BaseModel):
    segment: Segment | None = None
    property_types: list[PropertyType] = Field(default_factory=list)
    localities: list[str] = Field(default_factory=list)
    budget_min_inr: int | None = None
    budget_max_inr: int | None = None
    size_min_sqft: int | None = None
    size_max_sqft: int | None = None
    goal: InvestmentGoal | None = None
    target_roi_pct: float | None = None
    risk_appetite: RiskAppetite | None = None
    business_type: str | None = None
    must_haves: list[str] = Field(default_factory=list)


class LanguageProfileResult(BaseModel):
    draft: ProfileDraft
    matched_phrases: dict[str, str]
    unresolved: list[str]
    note: str = (
        "Recognized phrases only; no AI guesses or network calls. Review every filled "
        "field and complete missing criteria before saving. No profile or search is created."
    )
