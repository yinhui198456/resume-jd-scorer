import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from digest.collect.github import collect_github_releases, collect_github_repository_search
from digest.collect.html_index import collect_html_index, extract_index_entries


class FakeResponse:
    def __init__(self, payload, status_code=200, text=None):
        self._payload = payload
        self.status_code = status_code
        self.text = text or ""

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests

            response = requests.Response()
            response.status_code = self.status_code
            raise requests.HTTPError(response=response)

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return FakeResponse(self.payload)


class SequencedSession:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return next(self.responses)


def test_extract_index_entries_keeps_article_links():
    html = Path("tests/fixtures/openai-news.html").read_text(encoding="utf-8")

    entries = extract_index_entries(html, "https://openai.com/news/")

    assert [entry["title"] for entry in entries] == ["Agents release", "Codex update"]
    assert all(entry["url"].startswith("https://openai.com/") for entry in entries)


def test_extract_index_entries_accepts_openai_rss():
    rss = """<rss><channel><item><title>OpenAI update</title><link>https://openai.com/index/update/</link></item></channel></rss>"""

    entries = extract_index_entries(rss, "https://openai.com/news/rss.xml")

    assert entries == [{"title": "OpenAI update", "url": "https://openai.com/index/update/"}]


def test_collect_html_index_accepts_configured_allowed_hosts_for_practice_sources():
    rss = """<rss><channel><item><title>AI workflow practice</title><link>https://example.com/ai-workflow</link></item></channel></rss>"""
    session = FakeSession(None)
    session.payload = None

    def get(url, **kwargs):
        session.calls.append((url, kwargs))
        return FakeResponse(None, text=rss)

    session.get = get

    items = collect_html_index(
        {
            "id": "ai-practice-feed",
            "tier": 2,
            "url": "https://example.com/feed.xml",
            "allowed_hosts": ["example.com"],
        },
        session,
        "run-practice",
        datetime(2026, 6, 25, 8, 45, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    assert len(items) == 1
    assert items[0].source_id == "ai-practice-feed"
    assert items[0].canonical_url == "https://example.com/ai-workflow"


def test_collect_html_index_uses_rss_description_as_raw_body():
    rss = """<rss><channel><item><title>Agent workflow practice</title><link>https://example.com/agent-workflow</link><description>Concrete production lessons for agent evaluation and deployment.</description></item></channel></rss>"""
    session = FakeSession(None)
    session.get = lambda url, **kwargs: FakeResponse(None, text=rss)

    items = collect_html_index(
        {
            "id": "ai-practice-feed",
            "tier": 2,
            "url": "https://example.com/feed.xml",
            "allowed_hosts": ["example.com"],
        },
        session,
        "run-practice",
        datetime(2026, 6, 25, 8, 45, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    assert items[0].raw_body == "Concrete production lessons for agent evaluation and deployment."


def test_collect_html_index_extracts_rss_pubdate():
    rss = """<rss><channel><item><title>Recent AI workflow</title><link>https://example.com/recent</link><pubDate>Thu, 25 Jun 2026 02:00:00 GMT</pubDate></item></channel></rss>"""
    session = FakeSession(None)
    session.get = lambda url, **kwargs: FakeResponse(None, text=rss)

    items = collect_html_index(
        {
            "id": "ai-practice-feed",
            "tier": 2,
            "url": "https://example.com/feed.xml",
            "allowed_hosts": ["example.com"],
        },
        session,
        "run-practice",
        datetime(2026, 6, 25, 8, 45, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    assert items[0].published_at == "2026-06-25T02:00:00+00:00"


def test_collect_html_index_extracts_atom_published_date():
    atom = """<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Recent AI workflow</title><link href="https://example.com/recent"/><published>2026-06-25T22:28:46+00:00</published></entry></feed>"""
    session = FakeSession(None)
    session.get = lambda url, **kwargs: FakeResponse(None, text=atom)

    items = collect_html_index(
        {
            "id": "ai-practice-feed",
            "tier": 2,
            "url": "https://example.com/feed.xml",
            "allowed_hosts": ["example.com"],
        },
        session,
        "run-practice",
        datetime(2026, 6, 25, 8, 45, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    assert items[0].published_at == "2026-06-25T22:28:46+00:00"


def test_extract_index_entries_sorts_feed_entries_by_published_date_descending():
    rss = """<rss><channel>
    <item><title>A old item</title><link>https://example.com/old</link><pubDate>Thu, 01 Jan 2024 00:00:00 GMT</pubDate></item>
    <item><title>Z new item</title><link>https://example.com/new</link><pubDate>Thu, 25 Jun 2026 02:00:00 GMT</pubDate></item>
    </channel></rss>"""

    entries = extract_index_entries(rss, "https://example.com/feed.xml", {"example.com"})

    assert [entry["title"] for entry in entries] == ["Z new item", "A old item"]


def test_collect_github_releases_maps_api_payload():
    payload = json.loads(
        Path("tests/fixtures/github-releases.json").read_text(encoding="utf-8")
    )
    session = FakeSession(payload)
    now = datetime(2026, 6, 22, 8, 45, tzinfo=ZoneInfo("Asia/Shanghai"))

    items = collect_github_releases(
        {"id": "openai-codex", "tier": 1, "repository": "openai/codex"},
        session,
        "run-1",
        now,
    )

    assert len(items) == 1
    assert items[0].title == "Codex v1.2.3"
    assert items[0].source_id == "openai-codex"
    assert session.calls[0][0].endswith("/repos/openai/codex/releases")


def test_collect_github_releases_falls_back_to_atom_on_rate_limit():
    atom = """<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>tag:github.com,2008:Repository/1/v1.2.3</id><title>v1.2.3</title><link rel="alternate" href="https://github.com/openai/codex/releases/tag/v1.2.3"/><updated>2026-06-22T00:40:00Z</updated><content type="html">Release notes</content></entry></feed>"""
    session = SequencedSession([FakeResponse([], status_code=403), FakeResponse(None, text=atom)])

    items = collect_github_releases(
        {"id": "openai-codex", "tier": 1, "repository": "openai/codex"},
        session,
        "run-1",
        datetime(2026, 6, 22, 8, 45, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    assert len(items) == 1
    assert items[0].title == "v1.2.3"
    assert session.calls[1][0] == "https://github.com/openai/codex/releases.atom"


def test_collect_github_repository_search_maps_hot_ai_projects():
    payload = {
        "items": [
            {
                "id": 101,
                "full_name": "example/agent-kit",
                "html_url": "https://github.com/example/agent-kit",
                "description": "Agent workflow framework with MCP tools",
                "stargazers_count": 12345,
                "forks_count": 321,
                "updated_at": "2026-06-24T12:00:00Z",
                "pushed_at": "2026-06-24T11:00:00Z",
                "language": "Python",
                "topics": ["agents", "mcp", "llm"],
                "owner": {"login": "example"},
            }
        ]
    }
    session = FakeSession(payload)
    now = datetime(2026, 6, 25, 8, 45, tzinfo=ZoneInfo("Asia/Shanghai"))

    items = collect_github_repository_search(
        {
            "id": "github-hot-ai-projects",
            "tier": 2,
            "query": "topic:agents topic:llm stars:>500",
            "limit": 5,
        },
        session,
        "run-hot",
        now,
    )

    assert len(items) == 1
    assert items[0].source_id == "github-hot-ai-projects"
    assert items[0].source_tier == 2
    assert items[0].canonical_url == "https://github.com/example/agent-kit"
    assert items[0].title == "example/agent-kit"
    assert "stars: 12345" in items[0].raw_body
    assert "topics: agents, mcp, llm" in items[0].raw_body
    assert items[0].author == "example"
    assert session.calls[0][0] == "https://api.github.com/search/repositories"
    assert session.calls[0][1]["params"] == {
        "q": "topic:agents topic:llm stars:>500",
        "sort": "stars",
        "order": "desc",
        "per_page": 5,
    }


def test_collect_github_repository_search_uses_pushed_at_as_published_at():
    payload = {
        "items": [
            {
                "id": 101,
                "full_name": "example/agent-kit",
                "html_url": "https://github.com/example/agent-kit",
                "description": "Agent workflow framework with MCP tools",
                "stargazers_count": 12345,
                "forks_count": 321,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2026-06-20T12:00:00Z",
                "pushed_at": "2026-06-25T11:00:00Z",
                "language": "Python",
                "topics": ["agents", "mcp", "llm"],
                "owner": {"login": "example"},
            }
        ]
    }
    session = FakeSession(payload)

    items = collect_github_repository_search(
        {
            "id": "github-hot-ai-projects",
            "tier": 2,
            "query": "topic:agents topic:llm stars:>500",
            "limit": 5,
        },
        session,
        "run-hot",
        datetime(2026, 6, 25, 8, 45, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    assert items[0].published_at == "2026-06-25T11:00:00Z"
