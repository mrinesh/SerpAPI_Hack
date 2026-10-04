"""Provenance: where each data point came from and how far to trust it.

Every investor-facing fact (price, size, rent, yield...) is wrapped in `Sourced[T]` so the UI
can always show a source link and a confidence badge next to it. See
docs/decisions/0004-provenance-on-every-field.md.
"""

from enum import StrEnum
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

from app.schemas.common import SerpEngine

T = TypeVar("T")


class ExtractionMethod(StrEnum):
    SERPAPI_FIELD = "serpapi_field"  # read directly from a structured SerpApi field
    REGEX = "regex"  # parsed deterministically from result text
    LLM = "llm"  # extracted or inferred by the LLM
    COMPUTED = "computed"  # derived from other sourced values (e.g. price per sq ft)
    QUERY = "query"  # taken from the search that found it (the locality or type searched for)


class SourceRef(BaseModel):
    engine: SerpEngine
    url: str | None = None
    title: str | None = None
    # SerpApi `search_metadata.id`; the original response can be re-fetched for free with the
    # Search Archive API.
    search_id: str | None = None


class Sourced(BaseModel, Generic[T]):
    value: T | None = None
    confidence: float = Field(default=0.0, ge=0, le=1)
    method: ExtractionMethod
    sources: list[SourceRef] = Field(default_factory=list)
    note: str | None = None  # e.g. "price shown as a range; lower bound used"
