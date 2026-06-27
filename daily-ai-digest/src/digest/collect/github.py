import hashlib
import os
import xml.etree.ElementTree as ET
from datetime import datetime

import requests

from digest.models import RawItem


USER_AGENT = "daily-ai-digest/0.1 (+personal briefing collector)"
ATOM_NAMESPACE = "{http://www.w3.org/2005/Atom}"


def _collect_atom_releases(
    source: dict[str, object],
    session: object,
    run_id: str,
    fetched_at: str,
) -> list[RawItem]:
    repository = str(source["repository"])
    response = session.get(
        f"https://github.com/{repository}/releases.atom",
        headers={"User-Agent": USER_AGENT},
        timeout=20,
    )
    response.raise_for_status()
    root = ET.fromstring(response.text)
    items: list[RawItem] = []
    for entry in root.findall(f"{ATOM_NAMESPACE}entry")[:50]:
        title = entry.findtext(f"{ATOM_NAMESPACE}title") or "Untitled release"
        native_id = entry.findtext(f"{ATOM_NAMESPACE}id") or title
        link = next(
            (
                node.get("href", "")
                for node in entry.findall(f"{ATOM_NAMESPACE}link")
                if node.get("rel", "alternate") == "alternate"
            ),
            "",
        )
        body = entry.findtext(f"{ATOM_NAMESPACE}content") or title
        raw_id = hashlib.sha256(
            f"{source['id']}\0{native_id}\0{link}".encode()
        ).hexdigest()
        items.append(
            RawItem(
                run_id=run_id,
                schema_version=1,
                raw_id=raw_id,
                source_id=str(source["id"]),
                source_tier=int(source["tier"]),
                source_url=f"https://github.com/{repository}/releases",
                canonical_url=link,
                title=title,
                raw_body=body,
                author=None,
                published_at=entry.findtext(f"{ATOM_NAMESPACE}updated"),
                fetched_at=fetched_at,
                language="en",
                content_hash=hashlib.sha256(body.encode()).hexdigest(),
            )
        )
    return items


def collect_github_releases(
    source: dict[str, object],
    session: object = requests,
    run_id: str = "",
    now: datetime | None = None,
) -> list[RawItem]:
    repository = str(source["repository"])
    headers = {"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = session.get(
        f"https://api.github.com/repos/{repository}/releases",
        params={"per_page": 20},
        headers=headers,
        timeout=20,
    )
    fetched_at = (now or datetime.now().astimezone()).isoformat()
    if response.status_code in {403, 429}:
        return _collect_atom_releases(source, session, run_id, fetched_at)
    response.raise_for_status()
    items: list[RawItem] = []
    for release in response.json()[:50]:
        url = str(release["html_url"])
        title = str(release.get("name") or release.get("tag_name") or url)
        body = str(release.get("body") or title)
        native_id = str(release.get("id") or url)
        raw_id = hashlib.sha256(
            f"{source['id']}\0{native_id}\0{url}".encode()
        ).hexdigest()
        items.append(
            RawItem(
                run_id=run_id,
                schema_version=1,
                raw_id=raw_id,
                source_id=str(source["id"]),
                source_tier=int(source["tier"]),
                source_url=f"https://github.com/{repository}/releases",
                canonical_url=url,
                title=title,
                raw_body=body,
                author=(release.get("author") or {}).get("login"),
                published_at=release.get("published_at"),
                fetched_at=fetched_at,
                language="en",
                content_hash=hashlib.sha256(body.encode()).hexdigest(),
            )
        )
    return items


def collect_github_repository_search(
    source: dict[str, object],
    session: object = requests,
    run_id: str = "",
    now: datetime | None = None,
) -> list[RawItem]:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    limit = int(source.get("limit", 20))
    response = session.get(
        "https://api.github.com/search/repositories",
        params={
            "q": str(source["query"]),
            "sort": str(source.get("sort", "stars")),
            "order": str(source.get("order", "desc")),
            "per_page": limit,
        },
        headers=headers,
        timeout=20,
    )
    response.raise_for_status()
    fetched_at = (now or datetime.now().astimezone()).isoformat()
    items: list[RawItem] = []
    for repository in response.json().get("items", [])[:limit]:
        url = str(repository["html_url"])
        full_name = str(repository.get("full_name") or url)
        description = str(repository.get("description") or "")
        topics = [str(topic) for topic in repository.get("topics", [])]
        body = "\n".join(
            part
            for part in [
                description or full_name,
                f"stars: {repository.get('stargazers_count', 0)}",
                f"forks: {repository.get('forks_count', 0)}",
                f"language: {repository.get('language') or 'unknown'}",
                f"created_at: {repository.get('created_at')}" if repository.get("created_at") else "",
                f"pushed_at: {repository.get('pushed_at')}" if repository.get("pushed_at") else "",
                f"topics: {', '.join(topics)}" if topics else "",
            ]
            if part
        )
        native_id = str(repository.get("id") or url)
        raw_id = hashlib.sha256(
            f"{source['id']}\0{native_id}\0{url}".encode()
        ).hexdigest()
        items.append(
            RawItem(
                run_id=run_id,
                schema_version=1,
                raw_id=raw_id,
                source_id=str(source["id"]),
                source_tier=int(source["tier"]),
                source_url="https://api.github.com/search/repositories",
                canonical_url=url,
                title=full_name,
                raw_body=body,
                author=(repository.get("owner") or {}).get("login"),
                published_at=repository.get("pushed_at")
                or repository.get("updated_at"),
                fetched_at=fetched_at,
                language="en",
                content_hash=hashlib.sha256(body.encode()).hexdigest(),
            )
        )
    return items
