"""In-process background scheduler (CHECKLIST I-11).

APScheduler instead of Celery/Redis keeps the local run to a single process. Off unless
`SCHEDULER_ENABLED=true`, because every scheduled alert check spends live searches.
"""

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import get_settings
from app.jobs.alerts import run_alert_check

log = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> None:
    global _scheduler
    settings = get_settings()
    _scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
    _scheduler.add_job(
        run_alert_check,
        "interval",
        minutes=settings.alert_check_interval_minutes,
        id="alert_check",
        max_instances=1,
    )
    _scheduler.start()
    log.info("Scheduler started; alert check every %s min", settings.alert_check_interval_minutes)


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
