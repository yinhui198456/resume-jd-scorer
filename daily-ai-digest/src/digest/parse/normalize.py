import hashlib
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from digest.models import NewsItem, RawItem


TRACKING_PARAMETERS = {"fbclid", "gclid"}


def canonicalize_url(url: str) -> str:
    parts = urlsplit(url)
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_")
        and key.lower() not in TRACKING_PARAMETERS
    ]
    path = parts.path.rstrip("/") or "/"
    if path == "/" and not query:
        normalized_path = "/"
    else:
        normalized_path = path
    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            normalized_path,
            urlencode(sorted(query)),
            "",
        )
    )


def normalize_text(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).split())


def normalize_raw_item(raw: RawItem) -> NewsItem:
    canonical_url = canonicalize_url(raw.canonical_url)
    title = normalize_text(raw.title)
    body = normalize_text(raw.raw_body)
    content_hash = hashlib.sha256(body.encode()).hexdigest()
    news_id = hashlib.sha256(
        f"{canonical_url}\0{content_hash}".encode()
    ).hexdigest()
    return NewsItem(
        run_id=raw.run_id,
        schema_version=raw.schema_version,
        news_id=news_id,
        raw_ids=[raw.raw_id],
        canonical_url=canonical_url,
        dedupe_key=f"{canonical_url}\0{content_hash}",
        normalized_title=title,
        normalized_body=body,
        language=raw.language,
        published_at=raw.published_at,
        fetched_at=raw.fetched_at,
        source_tier=raw.source_tier,
    )
