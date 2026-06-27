from datetime import datetime
from zoneinfo import ZoneInfo

from digest.filter.quality import dedupe_exact, hard_filter, weighted_score
from digest.models import NewsItem


def item(url="https://example.com/a", published="2026-06-22T00:45:00Z"):
    return NewsItem(
        run_id="run-1", schema_version=1, news_id=url, raw_ids=[url],
        canonical_url=url, dedupe_key=url, normalized_title="Codex MCP release",
        normalized_body="Release notes benchmark code", language="en",
        published_at=published, fetched_at="2026-06-22T08:45:00+08:00", source_tier=1,
    )


def test_weighted_score_is_reproducible():
    components = {"source_trust": 1.0, "topic_match": 0.8, "information_density": 0.6, "recency": 1.0, "originality": 0.5, "evidence": 1.0}
    weights = {"source_trust": 0.30, "topic_match": 0.25, "information_density": 0.15, "recency": 0.15, "originality": 0.10, "evidence": 0.05}
    assert weighted_score(components, weights) == 0.84


def test_hard_filter_rejects_blocked_and_stale_items():
    now = datetime(2026, 6, 22, 8, 45, tzinfo=ZoneInfo("Asia/Shanghai"))
    allowed, reasons = hard_filter(item("https://blog.csdn.net/a", "2026-06-01T00:00:00Z"), ["csdn.net"], ["en", "zh"], 72, now)
    assert not allowed
    assert reasons == ["blocked_domain", "stale"]


def test_hard_filter_rejects_missing_published_at_when_required():
    now = datetime(2026, 6, 22, 8, 45, tzinfo=ZoneInfo("Asia/Shanghai"))
    news = item("https://example.com/a", None)

    allowed, reasons = hard_filter(news, [], ["en", "zh"], 72, now, require_published_at=True)

    assert not allowed
    assert reasons == ["missing_published_at"]


def test_dedupe_exact_keeps_first_stable_item():
    assert len(dedupe_exact([item(), item()])) == 1
