"""Record real F-05 responses through existing gateways, using an isolated temporary DB.

From backend: uv run python scripts/record_area_intel.py --profile both
At most five new SerpApi searches and two DeepSeek calls per locality. Existing recordings
are reused. No developer app database or .env is changed; only backend/fixtures is written.
"""

import argparse
import os
import tempfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=["residential", "commercial", "both"], default="both")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="realty-area-record-") as temporary:
        os.environ["DATABASE_URL"] = f"sqlite:///{(Path(temporary) / 'record.db').as_posix()}"
        os.environ["SERPAPI_MODE"] = "record"
        os.environ["LLM_MODE"] = "record"
        from app.config import get_settings
        from app.core.logging import configure_logging
        from app.db.session import SessionLocal, engine, init_db
        from app.integrations.llm.factory import get_llm
        from app.integrations.serpapi.gateway import SerpApiGateway
        from app.pipeline.context import PipelineContext
        from app.pipeline.enrichment.area import get_area_intel
        from app.reference.demo_profiles import DEMO_PROFILES
        from app.schemas.profile import InvestorProfileIn
        from app.services.profiles import create_profile

        settings = get_settings()
        configure_logging()
        init_db()
        names = list(DEMO_PROFILES) if args.profile == "both" else [args.profile]
        failed = False
        try:
            for name in names:
                with SessionLocal() as db:
                    profile = create_profile(
                        db, InvestorProfileIn.model_validate(DEMO_PROFILES[name])
                    )
                    ctx = PipelineContext(
                        run_id=f"f05-record-{name}",
                        profile=profile,
                        settings=settings,
                        db=db,
                        serp=SerpApiGateway(settings, db),
                        llm=get_llm(settings, db),
                        emit=lambda _: None,
                    )
                    for locality in profile.localities:
                        area = get_area_intel(ctx, locality)
                        print(
                            f"{area.locality_key}: {len(area.amenities)} amenities, "
                            f"{len(area.news)} news, "
                            f"{len(area.infrastructure)} infrastructure facts"
                        )
                        for issue in area.warnings:
                            print(f"  {issue.operation}: {issue.code}: {issue.message}")
                        failed |= bool(area.warnings)
            return 1 if failed else 0
        finally:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
