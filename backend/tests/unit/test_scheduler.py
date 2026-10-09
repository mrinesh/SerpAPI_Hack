from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.jobs import alerts, scheduler
from app.schemas.views import AlertCheckIssue, AlertCheckResult
from app.services.alerts import AlertCheckBusy


def test_scheduler_registers_one_coalesced_job_and_can_restart(monkeypatch):
    instances = []

    class FakeScheduler:
        def __init__(self, **kwargs):
            self.running = False
            self.jobs = []
            self.options = kwargs
            instances.append(self)

        def add_job(self, func, trigger, **kwargs):
            self.jobs.append((func, trigger, kwargs))

        def start(self):
            self.running = True

        def shutdown(self, **kwargs):
            self.running = False

    monkeypatch.setattr(scheduler, "BackgroundScheduler", FakeScheduler)
    monkeypatch.setattr(scheduler, "_scheduler", None)
    monkeypatch.setattr(
        scheduler, "get_settings", lambda: SimpleNamespace(alert_check_interval_minutes=10)
    )
    scheduler.start_scheduler()
    scheduler.start_scheduler()
    assert len(instances) == 1
    [(func, trigger, options)] = instances[0].jobs
    assert func == scheduler.run_alert_check and trigger == "interval"
    assert options == {
        "minutes": 10,
        "id": "alert_check",
        "max_instances": 1,
        "coalesce": True,
        "misfire_grace_time": 300,
    }
    scheduler.shutdown_scheduler()
    scheduler.shutdown_scheduler()
    scheduler.start_scheduler()
    assert len(instances) == 2
    scheduler.shutdown_scheduler()


def test_alert_job_uses_session_and_reports_profile_errors(db, monkeypatch, caplog):
    class ManagedSession:
        def __enter__(self):
            return db

        def __exit__(self, *args):
            pass

    monkeypatch.setattr(alerts, "SessionLocal", ManagedSession)
    monkeypatch.setattr(
        alerts,
        "check_alerts",
        lambda session: AlertCheckResult(
            checked_profiles=1, errors=[AlertCheckIssue(profile_id="failed", message="Replay miss")]
        ),
    )
    alerts.run_alert_check()
    assert "failed" in caplog.text and "Replay miss" in caplog.text


def test_busy_scheduled_check_is_logged_and_interval_must_be_positive(db, monkeypatch, caplog):
    class ManagedSession:
        def __enter__(self):
            return db

        def __exit__(self, *args):
            pass

    def busy(session):
        raise AlertCheckBusy("Already checking")

    monkeypatch.setattr(alerts, "SessionLocal", ManagedSession)
    monkeypatch.setattr(alerts, "check_alerts", busy)
    alerts.run_alert_check()
    assert "Already checking" in caplog.text
    with pytest.raises(ValidationError):
        Settings(alert_check_interval_minutes=0)
    assert not Settings().scheduler_enabled
