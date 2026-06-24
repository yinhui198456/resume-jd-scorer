import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from digest.collect.github import collect_github_releases
from digest.collect.html_index import extract_index_entries


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
