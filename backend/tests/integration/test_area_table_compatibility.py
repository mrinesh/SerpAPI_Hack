from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import ProfileRow, RunAreaRow, RunRow
from app.pipeline.persist import save_run_area
from app.reference.demo_profiles import DEMO_PROFILES
from app.schemas.area import AreaIntel


@pytest.mark.parametrize("surrogate_id", [True, False])
def test_area_snapshots_work_with_both_existing_table_layouts(surrogate_id):
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        key = "id INTEGER PRIMARY KEY," if surrogate_id else ""
        suffix = "" if surrogate_id else ", PRIMARY KEY (run_id, locality_key)"
        connection.exec_driver_sql(
            f"CREATE TABLE run_area_intel ({key} run_id TEXT NOT NULL, "
            f"locality_key TEXT NOT NULL, data JSON NOT NULL{suffix})"
        )
    Base.metadata.create_all(engine)
    now = datetime.now(UTC)
    with Session(engine) as db:
        db.add(ProfileRow(id="profile", data=DEMO_PROFILES["residential"]))
        db.flush()
        db.add(RunRow(id="run", profile_id="profile", status="succeeded"))
        db.commit()
        area = AreaIntel(
            locality_key="bengaluru/whitefield",
            locality="Whitefield",
            city="Bengaluru",
            fetched_at=now,
            expires_at=now,
            summary="Preserved evidence",
        )
        save_run_area(db, "run", area)
        db.expire_all()
        assert db.scalar(select(RunAreaRow)).data["summary"] == "Preserved evidence"
        area.summary = "Updated snapshot"
        save_run_area(db, "run", area)
        assert len(list(db.scalars(select(RunAreaRow)))) == 1
        assert db.scalar(select(RunAreaRow)).data["summary"] == "Updated snapshot"
    engine.dispose()
