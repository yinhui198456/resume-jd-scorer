import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from digest.jobs.daily import PipelineDependencies, run_daily
from digest.models import AppConfig, RawItem


class FakeCollector:
    def __init__(self, items, failures=None):
        self.items = items
        self.failures = failures or []
        self.call_count = 0

    def __call__(self, config, run_id, now):
        self.call_count += 1
        return self.items, self.failures


class FakeGenerator:
    def __init__(self):
        self.call_count = 0

    def __call__(self, item):
        self.call_count += 1
        return {"chinese_title": "MCP 更新", "summary": "发布新版本", "why_it_matters": "影响工具集成", "translation_status": "translated"}


@dataclass
class Result:
    message_id: str = "om_1"


class FakeDelivery:
    def __init__(self):
        self.text_count = 0
        self.post_count = 0
        self.last_post = None

    def send_text(self, text, delivery_key):
        self.text_count += 1
        return Result()

    def send_post(self, payload, delivery_key):
        self.post_count += 1
        self.last_post = payload
        return Result()


def learning_plan_values(*rows):
    return [
        ["任务序号", "方向", "任务项", "输出", "状态", "月份", "优先级", "备注", "链接"],
        *rows,
    ]


def config(root: Path) -> AppConfig:
    return AppConfig(str(root), {"blocked_domains": ["csdn.com"]}, {"allowed_languages": ["en", "zh"], "max_age_hours": 72, "thresholds": {"digest": 0.70, "candidate": 0.55}, "weights": {"source_trust": 0.30, "topic_match": 0.25, "information_density": 0.15, "recency": 0.15, "originality": 0.10, "evidence": 0.05}, "quotas": {"top_stories": 8, "candidates": 3}}, {"primary": ["MCP", "Codex"]}, {}, "key", "url", "model", "app", "secret", "chat")


def section_config(root: Path) -> AppConfig:
    return AppConfig(
        str(root),
        {
            "blocked_domains": ["csdn.com"],
            "html_indexes": [
                {"id": "openai-news", "tier": 1, "candidate_pool": False},
                {"id": "openai-codex-changelog", "tier": 1, "candidate_pool": True},
                {"id": "simon-willison-ai-practice", "tier": 2, "content_group": "practice_methodology", "candidate_pool": True},
            ],
            "github_repository_search": [
                {"id": "github-hot-ai-projects", "tier": 2, "content_group": "github_projects", "candidate_pool": True},
            ],
        },
        {
            "allowed_languages": ["en", "zh"],
            "max_age_hours": 72,
            "thresholds": {"digest": 0.70, "candidate": 0.55},
            "weights": {"source_trust": 0.30, "topic_match": 0.25, "information_density": 0.15, "recency": 0.15, "originality": 0.10, "evidence": 0.05},
            "quotas": {"top_stories": 6, "productivity_projects": 9},
            "practice_methodology": {
                "include_keywords": ["workflow", "productivity", "skills", "agent", "coding", "automation", "tools", "project", "implementation", "prompt", "MCP", "RAG"],
                "exclude_keywords": ["legal", "liability", "safety", "security", "policy", "governance", "regulation", "risk"],
            },
        },
        {"primary": ["Agent", "MCP", "Codex", "AI coding", "Methodology"]},
        {},
        "key",
        "url",
        "model",
        "app",
        "secret",
        "chat",
    )


def raw(run_id="run-1") -> RawItem:
    body = "MCP Codex release notes with benchmark, demo, code and documentation links."
    return RawItem(run_id, 1, "raw-1", "openai-codex", 1, "https://developers.openai.com/codex/changelog", "https://example.com/release", "Codex MCP release", body, None, "2026-06-22T00:40:00Z", "2026-06-22T08:45:00+08:00", "en", "hash")


def raw_ranked(index: int, high_score: bool, run_id: str = "run-quota") -> RawItem:
    body = (
        "Agent release with benchmark demo code documentation links and detailed notes " * 2
        if high_score
        else "brief"
    )
    return RawItem(run_id, 1, f"raw-{index}", "official", 1, "https://example.com", f"https://example.com/{index}", f"Update {index}", body, None, "2026-06-22T00:40:00Z", "2026-06-22T08:45:00+08:00", "en", f"hash-{index}")


def raw_section(index: int, source_id: str, tier: int, title: str, run_id: str = "run-sections") -> RawItem:
    body = "Agent MCP Codex AI coding methodology benchmark demo code documentation links " * 2
    return RawItem(
        run_id,
        1,
        f"raw-section-{index}",
        source_id,
        tier,
        f"https://example.com/{source_id}",
        f"https://example.com/{source_id}/{index}",
        title,
        body,
        None,
        "2026-06-22T00:40:00Z",
        "2026-06-22T08:45:00+08:00",
        "en",
        f"hash-section-{index}",
    )


def test_total_source_failure_delivers_fault_digest(tmp_path):
    collector = FakeCollector([], [{"source_id": "all", "error_code": "FETCH_TIMEOUT"}])
    delivery = FakeDelivery()
    deps = PipelineDependencies(collector, FakeGenerator(), delivery)

    report = run_daily(tmp_path, config(tmp_path), deps, "run-fault", datetime(2026, 6, 22, 8, 45, tzinfo=ZoneInfo("Asia/Shanghai")))

    assert report.status == "degraded"
    assert "故障简报" in Path(report.digest_path).read_text(encoding="utf-8")
    assert delivery.text_count == 1
    assert delivery.post_count == 0


def test_success_writes_all_stage_checkpoints_and_retry_is_idempotent(tmp_path):
    collector = FakeCollector([raw()])
    delivery = FakeDelivery()
    deps = PipelineDependencies(collector, FakeGenerator(), delivery)
    now = datetime(2026, 6, 22, 8, 45, tzinfo=ZoneInfo("Asia/Shanghai"))

    first = run_daily(tmp_path, config(tmp_path), deps, "run-1", now)
    second = run_daily(tmp_path, config(tmp_path), deps, "run-1", now)

    stage_dir = tmp_path / "data/state/runs/run-1/stages"
    assert len(list(stage_dir.glob("*.json"))) == 10
    assert first.status == second.status == "succeeded"
    assert collector.call_count == 1
    assert delivery.text_count == 0
    assert delivery.post_count == 1


def test_fault_run_can_recollect_with_same_run_id(tmp_path):
    collector = FakeCollector([], [{"source_id": "all", "error_code": "FETCH_TIMEOUT"}])
    delivery = FakeDelivery()
    deps = PipelineDependencies(collector, FakeGenerator(), delivery)
    now = datetime(2026, 6, 22, 8, 45, tzinfo=ZoneInfo("Asia/Shanghai"))

    first = run_daily(tmp_path, config(tmp_path), deps, "run-retry", now)
    collector.items = [raw("run-retry")]
    collector.failures = []
    second = run_daily(tmp_path, config(tmp_path), deps, "run-retry", now)

    assert first.status == "degraded"
    assert second.status == "succeeded"
    assert collector.call_count == 2
    assert delivery.text_count == 1
    assert delivery.post_count == 1


def test_digest_applies_top_story_quota_without_candidates(tmp_path):
    items = [raw_ranked(i, i < 12) for i in range(24)]
    collector = FakeCollector(items)
    generator = FakeGenerator()
    deps = PipelineDependencies(collector, generator, FakeDelivery())

    report = run_daily(tmp_path, config(tmp_path), deps, "run-quota", datetime(2026, 6, 22, 8, 45, tzinfo=ZoneInfo("Asia/Shanghai")))

    generated = json.loads((tmp_path / "data/state/runs/run-quota/generated.json").read_text())
    assert report.item_count == 8
    assert generator.call_count == 8
    assert Counter(item["section"] for item in generated) == {"重点资讯": 8}


def test_digest_reserves_sections_for_github_and_practice_sources(tmp_path):
    items = [
        *(raw_section(i, "openai-news", 1, f"Official Agent update {i}") for i in range(10)),
        *(raw_section(100 + i, "github-hot-ai-projects", 2, f"GitHub AI project {i}") for i in range(4)),
        *(raw_section(200 + i, "simon-willison-ai-practice", 2, f"AI methodology practice {i}") for i in range(5)),
        *(raw_section(300 + i, "openai-codex-changelog", 1, f"Codex changelog {i}") for i in range(5)),
    ]
    generator = FakeGenerator()

    report = run_daily(
        tmp_path,
        section_config(tmp_path),
        PipelineDependencies(FakeCollector(items), generator, FakeDelivery()),
        "run-sections",
        datetime(2026, 6, 22, 8, 45, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    generated = json.loads((tmp_path / "data/state/runs/run-sections/generated.json").read_text())
    assert report.item_count == 15
    assert generator.call_count == 15
    assert Counter(item["section"] for item in generated) == {
        "重点资讯": 6,
        "生产力项目": 9,
    }


def test_digest_backfills_productivity_when_top_stories_are_short(tmp_path):
    items = [
        *(raw_section(i, "openai-news", 1, f"Official Agent update {i}") for i in range(2)),
        *(raw_section(100 + i, "github-hot-ai-projects", 2, f"GitHub AI project {i}") for i in range(8)),
        *(raw_section(200 + i, "simon-willison-ai-practice", 2, f"Claude Code skills workflow {i}") for i in range(8)),
    ]
    generator = FakeGenerator()

    report = run_daily(
        tmp_path,
        section_config(tmp_path),
        PipelineDependencies(FakeCollector(items), generator, FakeDelivery()),
        "run-backfill-productivity",
        datetime(2026, 6, 22, 8, 45, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    generated = json.loads((tmp_path / "data/state/runs/run-backfill-productivity/generated.json").read_text())
    assert report.item_count == 15
    assert generator.call_count == 15
    assert Counter(item["section"] for item in generated) == {
        "重点资讯": 2,
        "生产力项目": 13,
    }


def test_productivity_sources_do_not_enter_top_stories(tmp_path):
    items = [
        *(raw_section(i, "openai-news", 1, f"Broad AI policy story {i}") for i in range(12)),
        *(raw_section(100 + i, "github-hot-ai-projects", 2, f"GitHub AI project {i}") for i in range(4)),
        *(raw_section(200 + i, "simon-willison-ai-practice", 2, f"AI methodology practice {i}") for i in range(5)),
        *(raw_section(300 + i, "openai-codex-changelog", 1, f"Codex changelog {i}") for i in range(3)),
    ]

    run_daily(
        tmp_path,
        section_config(tmp_path),
        PipelineDependencies(FakeCollector(items), FakeGenerator(), FakeDelivery()),
        "run-candidate-quality",
        datetime(2026, 6, 22, 8, 45, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    raw_items = json.loads((tmp_path / "data/raw/run-candidate-quality.json").read_text())
    filtered = json.loads((tmp_path / "data/filtered/run-candidate-quality.json").read_text())
    generated = json.loads((tmp_path / "data/state/runs/run-candidate-quality/generated.json").read_text())
    raw_by_id = {item["raw_id"]: item for item in raw_items}
    news_by_id = {item["news_id"]: item for item in filtered}
    top_sources = set()
    for digest_item in generated:
        if digest_item["section"] != "重点资讯":
            continue
        for news_id in digest_item["news_ids"]:
            for raw_id in news_by_id[news_id]["raw_ids"]:
                top_sources.add(raw_by_id[raw_id]["source_id"])

    assert "github-hot-ai-projects" not in top_sources
    assert "simon-willison-ai-practice" not in top_sources


def test_maintenance_only_patch_releases_are_not_selected(tmp_path):
    items = [
        raw_section(
            1,
            "openai-codex-changelog",
            1,
            "Codex 0.142.3 maintenance-only patch release",
        ),
        *(raw_section(100 + i, "github-hot-ai-projects", 2, f"GitHub AI project {i}") for i in range(15)),
    ]
    items[0].raw_body = (
        "Maintenance-only patch release with no user-facing changes. "
        "No user-visible capability changes since the previous version."
    )

    run_daily(
        tmp_path,
        section_config(tmp_path),
        PipelineDependencies(FakeCollector(items), FakeGenerator(), FakeDelivery()),
        "run-maintenance-release",
        datetime(2026, 6, 22, 8, 45, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    raw_items = json.loads((tmp_path / "data/raw/run-maintenance-release.json").read_text())
    filtered = json.loads((tmp_path / "data/filtered/run-maintenance-release.json").read_text())
    generated = json.loads((tmp_path / "data/state/runs/run-maintenance-release/generated.json").read_text())
    raw_by_id = {item["raw_id"]: item for item in raw_items}
    news_by_id = {item["news_id"]: item for item in filtered}
    selected_titles = []
    for digest_item in generated:
        for news_id in digest_item["news_ids"]:
            for raw_id in news_by_id[news_id]["raw_ids"]:
                selected_titles.append(raw_by_id[raw_id]["title"])

    assert "Codex 0.142.3 maintenance-only patch release" not in selected_titles


def test_github_project_summaries_include_star_count(tmp_path):
    item = raw_section(
        1,
        "github-hot-ai-projects",
        2,
        "GitHub AI project with stars",
        run_id="run-github-stars",
    )
    item.raw_body = (
        "Agent workflow tool with benchmark demo code documentation links.\n"
        "stars: 12345\n"
        "forks: 100"
    )

    run_daily(
        tmp_path,
        section_config(tmp_path),
        PipelineDependencies(FakeCollector([item]), FakeGenerator(), FakeDelivery()),
        "run-github-stars",
        datetime(2026, 6, 22, 8, 45, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    generated = json.loads((tmp_path / "data/state/runs/run-github-stars/generated.json").read_text())

    assert generated[0]["section"] == "生产力项目"
    assert generated[0]["summary"].startswith("⭐ 12,345 · ")


def test_learning_plan_existing_project_is_not_recommended_again(tmp_path):
    item = raw_section(
        1,
        "github-hot-ai-projects",
        2,
        "safishamsi/graphify",
        run_id="run-learning-suppress",
    )
    item.canonical_url = "https://github.com/safishamsi/graphify"
    item.published_at = "2026-06-29T00:40:00Z"
    item.fetched_at = "2026-06-29T08:45:00+08:00"
    item.raw_body = (
        "Code graph productivity tool with benchmark demo code documentation links.\n"
        "stars: 5154"
    )
    deps = PipelineDependencies(
        FakeCollector([item]),
        FakeGenerator(),
        FakeDelivery(),
        learning_plan_values=(
            lambda config: learning_plan_values(
                ["L36", "Agentic Coding", "Graphify 项目学习", "", "待开始", "2026 年 6 月", "中", "", "https://github.com/safishamsi/graphify"]
            )
        ),
    )

    report = run_daily(
        tmp_path,
        section_config(tmp_path),
        deps,
        "run-learning-suppress",
        datetime(2026, 6, 29, 8, 45, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    assert report.status == "degraded"
    assert report.item_count == 0


def test_learning_plan_existing_project_with_new_feature_is_recommended(tmp_path):
    item = raw_section(
        1,
        "github-hot-ai-projects",
        2,
        "safishamsi/graphify v2 release",
        run_id="run-learning-feature",
    )
    item.canonical_url = "https://github.com/safishamsi/graphify/releases/tag/v2.0.0"
    item.published_at = "2026-06-29T00:40:00Z"
    item.fetched_at = "2026-06-29T08:45:00+08:00"
    item.raw_body = (
        "New feature release: adds repository dependency maps for coding productivity. "
        "Benchmark demo code documentation links.\n"
        "stars: 5154"
    )
    deps = PipelineDependencies(
        FakeCollector([item]),
        FakeGenerator(),
        FakeDelivery(),
        learning_plan_values=(
            lambda config: learning_plan_values(
                ["L36", "Agentic Coding", "Graphify 项目学习", "", "待开始", "2026 年 6 月", "中", "", "https://github.com/safishamsi/graphify"]
            )
        ),
    )

    report = run_daily(
        tmp_path,
        section_config(tmp_path),
        deps,
        "run-learning-feature",
        datetime(2026, 6, 29, 8, 45, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    generated = json.loads((tmp_path / "data/state/runs/run-learning-feature/generated.json").read_text())
    assert report.status == "succeeded"
    assert generated[0]["section"] == "生产力项目"


def test_learning_plan_existing_project_with_fast_star_growth_is_recommended(tmp_path):
    item = raw_section(
        1,
        "github-hot-ai-projects",
        2,
        "safishamsi/graphify",
        run_id="run-learning-stars",
    )
    item.canonical_url = "https://github.com/safishamsi/graphify"
    item.published_at = "2026-06-29T00:40:00Z"
    item.fetched_at = "2026-06-29T08:45:00+08:00"
    item.raw_body = (
        "Code graph productivity tool with benchmark demo code documentation links.\n"
        "stars: 5154"
    )
    history_path = tmp_path / "data/state/github_star_history.json"
    history_path.parent.mkdir(parents=True)
    history_path.write_text(
        json.dumps(
            {
                "https://github.com/safishamsi/graphify": {
                    "stars": 4000,
                    "updated_at": "2026-06-28T08:45:00+08:00",
                }
            }
        ),
        encoding="utf-8",
    )
    deps = PipelineDependencies(
        FakeCollector([item]),
        FakeGenerator(),
        FakeDelivery(),
        learning_plan_values=(
            lambda config: learning_plan_values(
                ["L36", "Agentic Coding", "Graphify 项目学习", "", "待开始", "2026 年 6 月", "中", "", "https://github.com/safishamsi/graphify"]
            )
        ),
    )

    report = run_daily(
        tmp_path,
        section_config(tmp_path),
        deps,
        "run-learning-stars",
        datetime(2026, 6, 29, 8, 45, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    generated = json.loads((tmp_path / "data/state/runs/run-learning-stars/generated.json").read_text())
    assert report.status == "succeeded"
    assert generated[0]["summary"].startswith("⭐ 5,154 · ")


def test_learning_plan_lookup_failure_does_not_block_digest(tmp_path):
    item = raw_section(
        1,
        "github-hot-ai-projects",
        2,
        "safishamsi/graphify",
        run_id="run-learning-fail-open",
    )
    item.canonical_url = "https://github.com/safishamsi/graphify"
    item.published_at = "2026-06-29T00:40:00Z"
    item.fetched_at = "2026-06-29T08:45:00+08:00"
    item.raw_body = (
        "Code graph productivity tool with benchmark demo code documentation links.\n"
        "stars: 5154"
    )

    def fail(_config):
        raise RuntimeError("FEISHU_SHEETS_READ_999")

    report = run_daily(
        tmp_path,
        section_config(tmp_path),
        PipelineDependencies(FakeCollector([item]), FakeGenerator(), FakeDelivery(), learning_plan_values=fail),
        "run-learning-fail-open",
        datetime(2026, 6, 29, 8, 45, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    generated = json.loads((tmp_path / "data/state/runs/run-learning-fail-open/generated.json").read_text())
    assert report.status == "succeeded"
    assert generated[0]["section"] == "生产力项目"


def test_practice_section_excludes_legal_safety_and_keeps_productivity_items(tmp_path):
    items = [
        *(raw_section(i, "openai-news", 1, f"Official Agent update {i}") for i in range(8)),
        *(raw_section(100 + i, "github-hot-ai-projects", 2, f"GitHub AI project {i}") for i in range(4)),
        raw_section(200, "simon-willison-ai-practice", 2, "AI liability and legal risk for model providers"),
        raw_section(201, "simon-willison-ai-practice", 2, "Claude Code skills workflow for agent productivity"),
        raw_section(202, "simon-willison-ai-practice", 2, "Project automation tools for AI coding teams"),
        raw_section(203, "simon-willison-ai-practice", 2, "Prompt workflow implementation patterns"),
        raw_section(204, "simon-willison-ai-practice", 2, "datasette-export-database 0.3a2 fixes pyproject.toml dependency pin"),
        *(raw_section(300 + i, "openai-codex-changelog", 1, f"Codex changelog {i}") for i in range(5)),
    ]

    run_daily(
        tmp_path,
        section_config(tmp_path),
        PipelineDependencies(FakeCollector(items), FakeGenerator(), FakeDelivery()),
        "run-practice-quality",
        datetime(2026, 6, 22, 8, 45, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    raw_items = json.loads((tmp_path / "data/raw/run-practice-quality.json").read_text())
    filtered = json.loads((tmp_path / "data/filtered/run-practice-quality.json").read_text())
    generated = json.loads((tmp_path / "data/state/runs/run-practice-quality/generated.json").read_text())
    raw_by_id = {item["raw_id"]: item for item in raw_items}
    news_by_id = {item["news_id"]: item for item in filtered}
    practice_titles = []
    all_selected_titles = []
    for digest_item in generated:
        for news_id in digest_item["news_ids"]:
            for raw_id in news_by_id[news_id]["raw_ids"]:
                all_selected_titles.append(raw_by_id[raw_id]["title"])
                if digest_item["section"] == "生产力项目":
                    practice_titles.append(raw_by_id[raw_id]["title"])

    assert "AI liability and legal risk for model providers" not in practice_titles
    assert "AI liability and legal risk for model providers" not in all_selected_titles
    assert "datasette-export-database 0.3a2 fixes pyproject.toml dependency pin" not in all_selected_titles
    assert {
        "Claude Code skills workflow for agent productivity",
        "Project automation tools for AI coding teams",
        "Prompt workflow implementation patterns",
    } <= set(practice_titles)


def test_partial_source_failure_persists_source_health(tmp_path):
    failures = [{"source_id": "openai-news", "error_code": "HTTP_403"}]
    deps = PipelineDependencies(FakeCollector([raw()], failures), FakeGenerator(), FakeDelivery())

    run_daily(tmp_path, config(tmp_path), deps, "run-partial", datetime(2026, 6, 22, 8, 45, tzinfo=ZoneInfo("Asia/Shanghai")))

    per_run = json.loads((tmp_path / "data/state/runs/run-partial/source_health.json").read_text())
    latest = json.loads((tmp_path / "data/state/source_health.json").read_text())
    collect = json.loads((tmp_path / "data/state/runs/run-partial/stages/collect.json").read_text())
    assert per_run == latest
    assert per_run["failures"] == failures
    assert collect["error_code"] == "PARTIAL_SOURCE_FAILURE"


def test_normal_digest_uses_compact_post_and_one_primary_link(tmp_path):
    first = raw("run-post")
    second = RawItem(
        "run-post", 1, "raw-2", "openai-news", 1,
        "https://openai.com/news/rss.xml", "https://example.com/second",
        first.title, first.raw_body + " extra", None,
        first.published_at, first.fetched_at, "en", "hash-2",
    )
    delivery = FakeDelivery()

    run_daily(
        tmp_path,
        config(tmp_path),
        PipelineDependencies(FakeCollector([first, second]), FakeGenerator(), delivery),
        "run-post",
        datetime(2026, 6, 22, 8, 45, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    generated = json.loads((tmp_path / "data/state/runs/run-post/generated.json").read_text())
    assert delivery.post_count == 1
    assert delivery.text_count == 0
    assert "why_it_matters" not in json.dumps(delivery.last_post)
    assert len(generated[0]["source_links"]) == 1
