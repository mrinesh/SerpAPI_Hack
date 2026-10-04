"""Stage 4, verify: LLM extraction and relevance scoring (CHECKLIST F-03).

Two LLM calls per listing, kept separate so each is cheap and cacheable:
1. `extract` (lite model, prompt `extract_listing`): fill fields the regex parsers missed in a
   candidate's snippet text. Only runs when cleaning left gaps.
2. `verify` (reasoning model, prompt `verify_listing`): score the listing against the profile.

Listings whose verdict is `reject` are kept in the run results (with rank null) so the UI can
show what was filtered out and why.
"""

from pydantic import BaseModel

from app.core.errors import NotImplementedYet
from app.pipeline.context import PipelineContext
from app.schemas.listing import Listing, Verification


class ExtractedField(BaseModel):
    value: str | None
    confidence: float
    evidence: str | None  # exact text span the value came from


class ExtractedListing(BaseModel):
    """Output schema of the `extract_listing` prompt."""

    property_type: ExtractedField
    price_inr: ExtractedField
    size_sqft: ExtractedField
    bedrooms: ExtractedField
    status: ExtractedField


def extract(ctx: PipelineContext, listing: Listing) -> Listing:
    raise NotImplementedYet("F-03", "LLM field extraction")


def verify(ctx: PipelineContext, listing: Listing) -> Verification:
    raise NotImplementedYet("F-03", "LLM relevance verification")
