"""Record F-03 using existing SerpApi demo fixtures; spends DeepSeek calls only.

Run from backend: uv run python scripts/record_verification.py --profile residential
Use --profile commercial for the Koramangala office example. No shared app DB is changed.
Existing fixtures are reused, so only requests without one are paid for. `--serpapi-record`
also records searches that have no fixture yet (the price-level lookups); it spends a SerpApi
search for each.
"""

import argparse
import os
import tempfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=["residential", "commercial"], default="residential")
    parser.add_argument(
        "--serpapi-record",
        action="store_true",
        help="record SerpApi searches that have no fixture (spends one search each)",
    )
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="realty-verification-") as temporary:
        os.environ["DATABASE_URL"] = f"sqlite:///{(Path(temporary) / 'record.db').as_posix()}"
        os.environ["SERPAPI_MODE"] = "record" if args.serpapi_record else "replay"
        os.environ["LLM_MODE"] = "record"
        # Imports follow the overrides so global session/settings use this isolated DB.
        from app.config import get_settings
        from app.db.models import RunRow
        from app.db.session import SessionLocal, engine, init_db
        from app.pipeline.orchestrator import run_pipeline
        from app.reference.demo_profiles import DEMO_PROFILES
        from app.schemas.profile import InvestorProfileIn
        from app.schemas.run import RunStatus
        from app.services.profiles import create_profile
        from app.services.runs import get_run, get_verifications

        if not get_settings().deepseek_api_key:
            print("DEEPSEEK_API_KEY is not configured. Add it to the repo's .env before recording.")
            return 1
        init_db()
        data = DEMO_PROFILES[args.profile]
        try:
            with SessionLocal() as db:
                profile = create_profile(db, InvestorProfileIn.model_validate(data))
                run = RunRow(profile_id=profile.id, status=RunStatus.PENDING, events=[])
                db.add(run)
                db.commit()
                run_id = run.id
            run_pipeline(run_id)
            with SessionLocal() as db:
                result = get_run(db, run_id)
                print(f"{result.status}: {len(get_verifications(db, run_id))} checks recorded")
                if result.error:
                    print(result.error)
                return 0 if result.status == RunStatus.SUCCEEDED else 1
        finally:
            engine.dispose()  # release SQLite before TemporaryDirectory cleanup on Windows


if __name__ == "__main__":
    raise SystemExit(main())
