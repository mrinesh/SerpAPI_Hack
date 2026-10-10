from datetime import UTC, datetime

from app.schemas.area import AreaIntel, NewsItem
from app.schemas.common import SerpEngine
from app.schemas.provenance import SourceRef
from app.services.risk import assess_risk


def test_missing_evidence_never_means_low_risk():
    report = assess_risk(None)
    assert report.reported_concern_score is None and report.coverage_pct == 0
    assert all(item.score is None and item.status == "unknown" for item in report.indicators)


def test_news_concerns_keep_sources_and_do_not_certify_unit():
    ref = SourceRef(engine=SerpEngine.GOOGLE_NEWS, url="https://example.org/news")
    now = datetime.now(UTC)
    area = AreaIntel(
        locality_key="bengaluru/whitefield",
        locality="Whitefield",
        city="Bengaluru",
        fetched_at=now,
        expires_at=now,
        news=[NewsItem(title="Whitefield flooding reported", url=ref.url, source=ref)],
    )
    report = assess_risk(area)
    assert report.indicators[0].score == 50
    assert report.indicators[0].sources == [ref]
    assert report.indicators[1].score is None
    assert "not safe" in report.note
