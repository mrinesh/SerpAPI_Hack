"""Record F-09 inputs for demo profiles, reusing all existing F-02/03/05 recordings.

From backend: uv run python scripts/record_investment_metrics.py --profile both
Only backend/fixtures is written. The run and profile use a disposable database.
"""

import argparse
import os
import tempfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=["residential", "commercial", "both"], default="both")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="realty-investment-record-") as temporary:
        os.environ["DATABASE_URL"] = f"sqlite:///{(Path(temporary) / 'record.db').as_posix()}"
        os.environ["SERPAPI_MODE"] = "record"
        os.environ["LLM_MODE"] = "record"
        from app.core.logging import configure_logging
        from app.db.session import SessionLocal, engine, init_db
        from app.pipeline import orchestrator
        from app.reference.demo_profiles import DEMO_PROFILES
        from app.schemas.profile import InvestorProfileIn
        from app.services.profiles import create_profile
        from app.services.runs import get_metrics, get_run

        configure_logging()
        init_db()
        orchestrator._launch = orchestrator.run_pipeline
        names = list(DEMO_PROFILES) if args.profile == "both" else [args.profile]
        failed = False
        try:
            for name in names:
                with SessionLocal() as db:
                    profile = create_profile(
                        db, InvestorProfileIn.model_validate(DEMO_PROFILES[name])
                    )
                    run = orchestrator.start_run(db, profile.id)
                    db.expire_all()
                    run = get_run(db, run.id)
                    metrics = get_metrics(db, run.id)
                    event = next(e for e in run.events if e.stage == "enrich")
                    rents = sum(m.metrics.est_monthly_rent_inr.value is not None for m in metrics)
                    growths = sum(m.metrics.price_growth_pct.value is not None for m in metrics)
                    print(
                        f"{name}: {run.status}, {len(metrics)} metrics, "
                        f"{rents} rents, {growths} growth inputs"
                    )
                    print(f"  {event.message}; live searches: {run.searches_used}")
                    if run.error:
                        print(f"  {run.error}")
                    failed |= run.status != "succeeded" or bool(
                        event.counts.get("investment_warnings")
                    )
            return 1 if failed else 0
        finally:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
