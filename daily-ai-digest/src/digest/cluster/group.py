import hashlib
import re
from urllib.parse import urlsplit

from digest.models import NewsItem

_VERSION_PATTERN = re.compile(r"\bv?\d+(?:\.\d+){1,4}(?:[-+._]?(?:alpha|beta|rc|preview|canary|dev)\d*)?\b", re.IGNORECASE)
_VERSION_NOISE = re.compile(r"\b(release|released|releases|version|versions|changelog|update|updates|patch)\b", re.IGNORECASE)
_SEPARATOR_PATTERN = re.compile(r"[-:|·,()[\]{}]+")


def _title_key(item: NewsItem) -> str:
    return " ".join(item.normalized_title.casefold().split())


def _release_family_key(item: NewsItem) -> str | None:
    parsed = urlsplit(item.canonical_url)
    if parsed.hostname != "github.com":
        return None
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) >= 4 and parts[2] == "releases" and parts[3] == "tag":
        return f"github-release:{parts[0].casefold()}/{parts[1].casefold()}"
    return None


def _version_title_family_key(item: NewsItem) -> str | None:
    title = _title_key(item)
    if not _VERSION_PATTERN.search(title):
        return None
    product = _VERSION_PATTERN.sub(" ", title)
    product = _VERSION_NOISE.sub(" ", product)
    product = _SEPARATOR_PATTERN.sub(" ", product)
    product = " ".join(part for part in product.split() if part)
    if len(product) < 3:
        return None
    return f"version-title:{product}"


def _cluster_key(item: NewsItem) -> str:
    return _release_family_key(item) or _version_title_family_key(item) or f"title:{_title_key(item)}"


def cluster_items(items: list[NewsItem]) -> list[list[NewsItem]]:
    groups: dict[str, list[NewsItem]] = {}
    for item in items:
        groups.setdefault(_cluster_key(item), []).append(item)
    clusters = list(groups.values())
    for cluster in clusters:
        cluster_id = hashlib.sha256("\0".join(sorted(item.news_id for item in cluster)).encode()).hexdigest()
        for item in cluster:
            item.cluster_id = cluster_id
    return clusters
