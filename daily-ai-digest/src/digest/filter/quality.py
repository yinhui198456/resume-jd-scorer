from datetime import datetime
from urllib.parse import urlsplit

from digest.models import NewsItem


def weighted_score(components: dict[str, float], weights: dict[str, float]) -> float:
    if components.keys() != weights.keys():
        raise ValueError("score component mismatch")
    if any(value < 0 or value > 1 for value in components.values()):
        raise ValueError("score components must be between 0 and 1")
    return round(sum(components[name] * weights[name] for name in weights), 6)


def hard_filter(
    item: NewsItem,
    blocked_domains: list[str],
    allowed_languages: list[str],
    max_age_hours: int,
    now: datetime,
    require_published_at: bool = False,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    host = (urlsplit(item.canonical_url).hostname or "").lower()
    if any(host == domain or host.endswith(f".{domain}") for domain in blocked_domains):
        reasons.append("blocked_domain")
    if item.language not in allowed_languages:
        reasons.append("unsupported_language")
    if require_published_at and not item.published_at:
        reasons.append("missing_published_at")
    timestamp = datetime.fromisoformat((item.published_at or item.fetched_at).replace("Z", "+00:00"))
    if (now - timestamp).total_seconds() > max_age_hours * 3600:
        reasons.append("stale")
    item.filter_reasons = reasons
    item.filter_decision = "rejected" if reasons else "eligible"
    return not reasons, reasons


def dedupe_exact(items: list[NewsItem]) -> list[NewsItem]:
    seen_urls: set[str] = set()
    seen_keys: set[str] = set()
    result: list[NewsItem] = []
    for item in items:
        if item.canonical_url in seen_urls or item.dedupe_key in seen_keys:
            continue
        seen_urls.add(item.canonical_url)
        seen_keys.add(item.dedupe_key)
        result.append(item)
    return result


def tag_topics(item: NewsItem, topics: list[str]) -> list[str]:
    haystack = f"{item.normalized_title} {item.normalized_body}".casefold()
    item.topic_tags = [topic for topic in topics if topic.casefold() in haystack]
    return item.topic_tags
