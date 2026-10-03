"""Scheduled job entry point for alerts. The logic lives in app/services/alerts.py."""

import logging

from app.core.errors import AppError
from app.db.session import SessionLocal
from app.services.alerts import check_alerts

log = logging.getLogger(__name__)


def run_alert_check() -> None:
    with SessionLocal() as db:
        try:
            created = check_alerts(db)
            log.info("Alert check created %d alerts", len(created))
        except AppError as exc:
            log.warning("Alert check skipped: %s", exc.message)
