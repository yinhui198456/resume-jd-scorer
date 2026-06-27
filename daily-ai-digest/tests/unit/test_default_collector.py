from datetime import datetime
from zoneinfo import ZoneInfo

from digest.jobs.daily import _default_collector
from digest.models import AppConfig, RawItem


def test_default_collector_includes_github_repository_search(monkeypatch):
    now = datetime(2026, 6, 25, 8, 45, tzinfo=ZoneInfo("Asia/Shanghai"))
    observed = []

    def fake_collect_github_repository_search(source, run_id, now):
        observed.append((source["id"], run_id, now.isoformat()))
        return [
            RawItem(
                run_id,
                1,
                "raw-hot",
                source["id"],
                source["tier"],
                "https://api.github.com/search/repositories",
                "https://github.com/example/agent-kit",
                "example/agent-kit",
                "Agent workflow framework with MCP tools",
                "example",
                "2026-06-24T11:00:00Z",
                now.isoformat(),
                "en",
                "hash-hot",
            )
        ]

    monkeypatch.setattr(
        "digest.jobs.daily.collect_github_repository_search",
        fake_collect_github_repository_search,
    )
    config = AppConfig(
        root=".",
        sources={
            "github_repository_search": [
                {
                    "id": "github-hot-ai-projects",
                    "tier": 2,
                    "query": "topic:agents stars:>500",
                }
            ]
        },
        filters={},
        topics={},
        schedule={},
        minimax_api_key="key",
        minimax_base_url="url",
        minimax_model="model",
        feishu_app_id="app",
        feishu_app_secret="secret",
        feishu_chat_id="chat",
    )

    items, failures = _default_collector(config, "run-hot", now)

    assert failures == []
    assert [item.source_id for item in items] == ["github-hot-ai-projects"]
    assert observed == [("github-hot-ai-projects", "run-hot", now.isoformat())]
