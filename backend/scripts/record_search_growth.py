"""Record real Google Trends and grounded AI reviews for the existing demo profiles.

From backend: uv run python scripts/record_search_growth.py --profile both
App history is real data recorded by the app; no fake historical searches are inserted.
"""

import argparse
import os
import tempfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=["residential", "commercial", "both"], default="both")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="realty-search-growth-") as directory:
        os.environ["DATABASE_URL"] = f"sqlite:///{(Path(directory) / 'record.db').as_posix()}"
        os.environ["SERPAPI_MODE"] = "record"
        os.environ["LLM_MODE"] = "record"
        from app.core.logging import configure_logging
        from app.db.session import SessionLocal, engine, init_db
        from app.pipeline import orchestrator
        from app.reference.demo_profiles import DEMO_PROFILES
        from app.schemas.profile import InvestorProfileIn
        from app.services.profiles import create_profile
        from app.services.runs import get_development, get_run

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
                    print(f"{name}: {run.status}; {run.searches_used} live searches", flush=True)
                    if run.error:
                        print(run.error)
                    failed |= run.status != "succeeded"
                    for report in get_development(db, run.id):
                        print(
                            f"  {report.locality}: {report.signal}, "
                            f"score={report.evidence_score}, AI={report.ai_review}",
                            flush=True,
                        )
                        for history in report.public_interest:
                            print(
                                f"    {history.query}: {len(history.history)} weeks, "
                                f"{history.signal}, quarter={history.quarter_change_pct}, "
                                f"annual={history.annual_change_pct}",
                                flush=True,
                            )
                        for issue in report.warnings:
                            print(
                                f"    {issue.operation}: {issue.code}: {issue.message}", flush=True
                            )
                        failed |= bool(report.warnings)
            return 1 if failed else 0
        finally:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
