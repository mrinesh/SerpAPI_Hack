"""Scheduled job entry point for alerts. The logic lives in app/services/alerts.py."""

import logging

from app.core.errors import AppError
from app.db.session import SessionLocal
from app.services.alerts import check_alerts

log = logging.getLogger(__name__)


def run_alert_check() -> None:
    with SessionLocal() as db:
        try:
            result = check_alerts(db)
            log.info(
                "Alert check: %d profiles checked, %d active skipped, %d alerts created",
                result.checked_profiles,
                result.skipped_profiles,
                len(result.alerts),
            )
            for issue in result.errors:
                log.warning("Alert check failed profile=%s: %s", issue.profile_id, issue.message)
        except AppError as exc:
            log.warning("Alert check skipped: %s", exc.message)
        except Exception:
            log.exception("Scheduled alert check failed")
