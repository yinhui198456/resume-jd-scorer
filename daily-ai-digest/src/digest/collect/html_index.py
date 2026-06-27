import hashlib
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup

from digest.models import RawItem


ALLOWED_HOSTS = {"openai.com", "developers.openai.com", "www.anthropic.com"}
USER_AGENT = "daily-ai-digest/0.1 (+personal briefing collector)"


def _published_at(item) -> str | None:
    for tag in ("pubDate", "published", "updated", "dc:date"):
        node = item.find(tag)
        if not node:
            continue
        value = node.get_text(" ", strip=True)
        if not value:
            continue
        try:
            if tag == "pubDate":
                return parsedate_to_datetime(value).isoformat()
            return datetime.fromisoformat(value.replace("Z", "+00:00")).isoformat()
        except ValueError:
            continue
    return None


def extract_index_entries(
    html: str, base_url: str, allowed_hosts: set[str] | None = None
) -> list[dict[str, str]]:
    hosts = allowed_hosts or ALLOWED_HOSTS
    if html.lstrip().startswith(("<rss", "<?xml", "<feed")):
        feed = BeautifulSoup(html, "xml")
        entries = {}
        for item in feed.select("item, entry"):
            title_node = item.find("title")
            link_node = item.find("link")
            body_node = (
                item.find("description")
                or item.find("summary")
                or item.find("content")
                or item.find("content:encoded")
            )
            title = " ".join(title_node.get_text(" ", strip=True).split()) if title_node else ""
            body = " ".join(body_node.get_text(" ", strip=True).split()) if body_node else ""
            published_at = _published_at(item)
            href = (link_node.get("href") or link_node.get_text(strip=True)) if link_node else ""
            url = urljoin(base_url, href)
            if title and urlsplit(url).hostname in hosts:
                entries[url] = {"title": title, "url": url}
                if body:
                    entries[url]["body"] = body
                if published_at:
                    entries[url]["published_at"] = published_at
        return sorted(
            entries.values(),
            key=lambda item: (item.get("published_at", ""), item["title"], item["url"]),
            reverse=True,
        )[:50]

    soup = BeautifulSoup(html, "html.parser")
    entries: dict[str, dict[str, str]] = {}
    for anchor in soup.select("article a[href], main a[href]"):
        title = " ".join(anchor.get_text(" ", strip=True).split())
        url = urljoin(base_url, anchor.get("href", ""))
        if title and urlsplit(url).hostname in hosts:
            entries[url] = {"title": title, "url": url}
    return sorted(entries.values(), key=lambda item: (item["title"], item["url"]))[:50]


def collect_html_index(
    source: dict[str, object],
    session: object = requests,
    run_id: str = "",
    now: datetime | None = None,
) -> list[RawItem]:
    fetched_at = (now or datetime.now().astimezone()).isoformat()
    response = session.get(
        str(source["url"]), headers={"User-Agent": USER_AGENT}, timeout=20
    )
    response.raise_for_status()
    items: list[RawItem] = []
    allowed_hosts = set(source.get("allowed_hosts") or ALLOWED_HOSTS)
    for entry in extract_index_entries(response.text, str(source["url"]), allowed_hosts):
        identity = hashlib.sha256(
            f"{source['id']}\0{entry['url']}".encode()
        ).hexdigest()
        items.append(
            RawItem(
                run_id=run_id,
                schema_version=1,
                raw_id=identity,
                source_id=str(source["id"]),
                source_tier=int(source["tier"]),
                source_url=str(source["url"]),
                canonical_url=entry["url"],
                title=entry["title"],
                raw_body=entry.get("body") or entry["title"],
                author=None,
                published_at=entry.get("published_at"),
                fetched_at=fetched_at,
                language="en",
                content_hash=hashlib.sha256((entry.get("body") or entry["title"]).encode()).hexdigest(),
            )
        )
    return items
