from datetime import date, timedelta

from app.schemas.common import SerpEngine
from app.schemas.development import InterestPoint, SearchMomentum
from app.schemas.provenance import SourceRef
from app.services.forecast import project_interest


def series(values):
    start = date(2026, 1, 5)
    return SearchMomentum(
        kind="locality_interest",
        query="Whitefield",
        unit="relative_interest_0_100",
        history=[
            InterestPoint(week=start + timedelta(weeks=i), value=v) for i, v in enumerate(values)
        ],
        note="",
        source=SourceRef(engine=SerpEngine.GOOGLE_TRENDS, url="https://trends.google.com"),
    )


def test_linear_series_projects_with_exact_holdout_and_retains_source():
    signal = series(list(range(10, 36)))
    result = project_interest(signal, signal.history[-1].week)
    assert result.status == "projected" and result.holdout_mae == 0
    assert [p.value for p in result.points] == [39, 47]
    assert result.source == signal.source


def test_sparse_stale_gapped_missing_and_app_history_are_unavailable():
    signal = series([0] * 26)
    assert project_interest(signal, signal.history[-1].week).status == "unavailable"
    signal = series([40] * 26)
    assert project_interest(signal, date(2027, 1, 1)).status == "unavailable"
    signal.history[3].week += timedelta(days=1)
    assert project_interest(signal, signal.history[-1].week).status == "unavailable"
    signal = series([40] * 25)
    assert project_interest(signal, signal.history[-1].week).status == "unavailable"
    signal = series([40] * 26)
    signal.source = None
    assert project_interest(signal, signal.history[-1].week).status == "unavailable"


def test_outputs_are_bounded_for_steep_trends():
    signal = series([i * 4 for i in range(26)])
    result = project_interest(signal, signal.history[-1].week)
    assert all(0 <= p.lower <= p.value <= p.upper <= 100 for p in result.points)
