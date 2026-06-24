from digest.models import RawItem
from digest.parse.normalize import canonicalize_url, normalize_raw_item


def raw_item() -> RawItem:
    return RawItem(
        run_id="run-1",
        schema_version=1,
        raw_id="raw-1",
        source_id="openai-news",
        source_tier=1,
        source_url="https://openai.com/news/",
        canonical_url="https://example.com/post/?utm_source=x&id=7#section",
        title="  Codex   update  ",
        raw_body="New   MCP support.",
        author=None,
        published_at="2026-06-22T00:45:00Z",
        fetched_at="2026-06-22T08:45:00+08:00",
        language="en",
        content_hash="hash",
    )


def test_canonicalize_url_removes_tracking_parameters():
    assert canonicalize_url(raw_item().canonical_url) == "https://example.com/post?id=7"


def test_normalize_raw_item_is_stable():
    first = normalize_raw_item(raw_item())
    second = normalize_raw_item(raw_item())

    assert first.normalized_title == "Codex update"
    assert first.normalized_body == "New MCP support."
    assert first.news_id == second.news_id
    assert first.canonical_url == "https://example.com/post?id=7"
