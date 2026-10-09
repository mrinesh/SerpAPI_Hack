"""F-10: verified new matches and conservative quoted-price changes, per profile.

Diff successful frozen run snapshots, not mutable shared listings. Price-sensitive candidate
IDs cannot prove two portal quotes are the same unit; cross-ID comparison needs an explicit
project, stated size, same portal/locality/type and unambiguous one-to-one observations.
"""

import hashlib
import logging
import re
import threading
from collections import defaultdict
from datetime import UTC

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError, NotFound
from app.db.base import utcnow
from app.db.models import AlertRow, ProfileRow, RunResultRow, RunRow
from app.pipeline.cleaning import _caps_name, _nobroker_name
from app.pipeline.orchestrator import start_run
from app.schemas.listing import Listing
from app.schemas.views import Alert, AlertCheckIssue, AlertCheckResult

_check_lock = threading.Lock()
log = logging.getLogger(__name__)


class AlertCheckBusy(AppError):
    status_code = 409
    code = "alert_check_busy"


def list_alerts(db: Session, *, unread_only: bool = False) -> list[Alert]:
    query = select(AlertRow).order_by(AlertRow.created_at.desc(), AlertRow.id)
    if unread_only:
        query = query.where(AlertRow.read_at.is_(None))
    return [_view(row) for row in db.scalars(query)]


def mark_read(db: Session, alert_id: str) -> Alert:
    row = db.get(AlertRow, alert_id)
    if row is None:
        raise NotFound(f"Alert {alert_id} not found")
    if row.read_at is None:
        row.read_at = utcnow()
        db.commit()
    return _view(row)


def _view(row: AlertRow) -> Alert:
    return Alert(
        id=row.id,
        profile_id=row.profile_id,
        kind=row.kind,
        listing_id=row.listing_id,
        message=row.message,
        created_at=row.created_at.replace(tzinfo=row.created_at.tzinfo or UTC),
        read_at=row.read_at.replace(tzinfo=row.read_at.tzinfo or UTC) if row.read_at else None,
    )


def price_identity(listing: Listing) -> tuple | None:
    """Only explicit project + stated size can link different price-sensitive IDs."""
    size = listing.size_sqft
    if size.value is None or size.method != "regex" or not listing.evidence:
        return None
    evidence = listing.evidence
    head = re.split(r"₹|\brs\.?\s*\d", evidence, maxsplit=1, flags=re.I)[0]
    project = _caps_name(head) or _nobroker_name(evidence)
    if not project:
        return None
    return (
        listing.portal,
        listing.locality.value,
        listing.property_type.value,
        " ".join(project.lower().split()),
        size.value,
        listing.bedrooms.value,
    )


def diff_matches(
    previous: list[Listing], current: list[Listing], seen_ids: set[str]
) -> list[tuple[str, Listing, str]]:
    """Pure diff; ambiguous cross-ID matches never produce a price-drop claim."""
    old_ids = {item.id: item for item in previous}
    old_groups, new_groups = defaultdict(list), defaultdict(list)
    for item in previous:
        if key := price_identity(item):
            old_groups[key].append(item)
    for item in current:
        if key := price_identity(item):
            new_groups[key].append(item)
    events = []
    for item in current:
        old = old_ids.get(item.id)
        key = price_identity(item)
        if old is None and key and len(old_groups[key]) == len(new_groups[key]) == 1:
            old = old_groups[key][0]
        price = item.price_inr.value
        if (
            old
            and price is not None
            and old.price_inr.value is not None
            and price < old.price_inr.value
        ):
            message = (
                f"{item.name}: quoted price fell from INR {old.price_inr.value:,} "
                f"to INR {price:,}. "
                "Matched project and size; confirm the same unit at the source."
            )
            events.append(("price_drop", item, message))
        elif old is None and item.id not in seen_ids:
            events.append(("new_match", item, f"New verified match: {item.name}."))
    return events


def _matches(db: Session, run_id: str) -> list[Listing]:
    matches = []
    for row in db.scalars(select(RunResultRow).where(RunResultRow.run_id == run_id)):
        check = row.recommendation.get("verification") or {}
        if check.get("verdict") in {"strong", "partial"}:
            matches.append(Listing.model_validate(row.recommendation["listing"]))
    return matches


def check_alerts(db: Session) -> AlertCheckResult:
    """Refresh profiles serially through the budgeted pipeline; isolate per-profile failures."""
    if not _check_lock.acquire(blocking=False):
        raise AlertCheckBusy("An alert check is already running. Try again after it finishes.")
    result = AlertCheckResult()
    try:
        profile_ids = list(db.scalars(select(ProfileRow.id).order_by(ProfileRow.id)))
        for profile_id in profile_ids:
            active = db.scalar(
                select(RunRow.id)
                .where(RunRow.profile_id == profile_id, RunRow.status.in_(["pending", "running"]))
                .limit(1)
            )
            if active:
                result.skipped_profiles += 1
                continue
            try:
                history = list(
                    db.scalars(
                        select(RunRow)
                        .where(RunRow.profile_id == profile_id, RunRow.status == "succeeded")
                        .order_by(RunRow.created_at.desc(), RunRow.id.desc())
                    )
                )
                previous = _matches(db, history[0].id) if history else []
                seen_ids = {item.id for run in history for item in _matches(db, run.id)}
                run = start_run(db, profile_id, background=False)
                if run.status != "succeeded":
                    result.errors.append(
                        AlertCheckIssue(profile_id=profile_id, message=run.error or "Search failed")
                    )
                    continue
                created = []
                for kind, item, message in diff_matches(previous, _matches(db, run.id), seen_ids):
                    event_id = hashlib.sha256(
                        f"{profile_id}|{run.id}|{kind}|{item.id}".encode()
                    ).hexdigest()[:32]
                    if db.get(AlertRow, event_id) is None:
                        row = AlertRow(
                            id=event_id,
                            profile_id=profile_id,
                            kind=kind,
                            listing_id=item.id,
                            message=message,
                        )
                        db.add(row)
                        db.flush()
                        created.append(_view(row))
                db.commit()
                result.alerts.extend(created)
                result.checked_profiles += 1
            except Exception as exc:
                db.rollback()
                log.exception("Alert check failed for profile %s", profile_id)
                message = (
                    exc.message
                    if isinstance(exc, AppError)
                    else "Alert check failed; see backend log."
                )
                result.errors.append(AlertCheckIssue(profile_id=profile_id, message=message))
        return result
    finally:
        _check_lock.release()
