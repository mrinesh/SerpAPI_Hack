"""Investor profile CRUD (CHECKLIST F-01)."""

from sqlalchemy.orm import Session

from app.core.errors import NotImplementedYet
from app.schemas.profile import InvestorProfile, InvestorProfileIn


def create_profile(db: Session, data: InvestorProfileIn) -> InvestorProfile:
    raise NotImplementedYet("F-01", "Creating a profile")


def list_profiles(db: Session) -> list[InvestorProfile]:
    raise NotImplementedYet("F-01", "Listing profiles")


def get_profile(db: Session, profile_id: str) -> InvestorProfile:
    raise NotImplementedYet("F-01", "Reading a profile")


def update_profile(db: Session, profile_id: str, data: InvestorProfileIn) -> InvestorProfile:
    raise NotImplementedYet("F-01", "Updating a profile")
