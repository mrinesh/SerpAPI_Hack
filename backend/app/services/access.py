"""Ownership predicates reused by every private view; legacy data belongs to local mode."""

from sqlalchemy import or_, select, true
from sqlalchemy.orm import Session

from app.db.models import ProfileOwnerRow, ProfileRow


def owner_id(db: Session) -> str:
    return db.info.get("owner_id", "local")


def profile_condition(db: Session):
    if db.info.get("system_job"):
        return true()
    owned = select(ProfileOwnerRow.profile_id).where(ProfileOwnerRow.owner_id == owner_id(db))
    if owner_id(db) == "local":
        return or_(
            ProfileRow.id.in_(owned), ProfileRow.id.not_in(select(ProfileOwnerRow.profile_id))
        )
    return ProfileRow.id.in_(owned)


def profile_ids(db: Session):
    return select(ProfileRow.id).where(profile_condition(db))


def set_pipeline_owner(db: Session, profile_id: str) -> None:
    row = db.get(ProfileOwnerRow, profile_id)
    db.info["owner_id"] = row.owner_id if row else "local"
