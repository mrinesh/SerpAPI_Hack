from app.db.models import ProfileRow
from app.services.profiles import seed_demo_profiles


def test_seed_preserves_edited_demo_and_adds_idempotent_recorded_criteria(db):
    assert seed_demo_profiles(db) == 2
    from sqlalchemy import select

    original = db.scalars(select(ProfileRow)).first()
    old_data = dict(original.data)
    original.data = {**original.data, "target_roi_pct": 99}
    db.commit()
    assert seed_demo_profiles(db) == 1
    assert db.get(ProfileRow, original.id).data["target_roi_pct"] == 99
    assert seed_demo_profiles(db) == 0
    rows = list(db.scalars(select(ProfileRow)))
    assert len(rows) == 3
    assert any(
        row.data["name"].startswith(old_data["name"] + " (recorded criteria")
        and row.data["target_roi_pct"] == old_data["target_roi_pct"]
        for row in rows
    )
