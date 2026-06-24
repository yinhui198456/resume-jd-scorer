import hashlib

from digest.models import NewsItem


def _title_key(item: NewsItem) -> str:
    return " ".join(item.normalized_title.casefold().split())


def cluster_items(items: list[NewsItem]) -> list[list[NewsItem]]:
    groups: dict[str, list[NewsItem]] = {}
    for item in items:
        groups.setdefault(_title_key(item), []).append(item)
    clusters = list(groups.values())
    for cluster in clusters:
        cluster_id = hashlib.sha256("\0".join(sorted(item.news_id for item in cluster)).encode()).hexdigest()
        for item in cluster:
            item.cluster_id = cluster_id
    return clusters
