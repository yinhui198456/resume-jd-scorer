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


def config(root: Path) -> AppConfig:
    return AppConfig(str(root), {"blocked_domains": ["csdn.com"]}, {"allowed_languages": ["en", "zh"], "max_age_hours": 72, "thresholds": {"digest": 0.70, "candidate": 0.55}, "weights": {"source_trust": 0.30, "topic_match": 0.25, "information_density": 0.15, "recency": 0.15, "originality": 0.10, "evidence": 0.05}, "quotas": {"top_stories": 8, "candidates": 3}}, {"primary": ["MCP", "Codex"]}, {}, "key", "url", "model", "app", "secret", "chat")


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


def test_digest_applies_top_story_and_candidate_quotas(tmp_path):
    items = [raw_ranked(i, i < 12) for i in range(24)]
    collector = FakeCollector(items)
    generator = FakeGenerator()
    deps = PipelineDependencies(collector, generator, FakeDelivery())

    report = run_daily(tmp_path, config(tmp_path), deps, "run-quota", datetime(2026, 6, 22, 8, 45, tzinfo=ZoneInfo("Asia/Shanghai")))

    generated = json.loads((tmp_path / "data/state/runs/run-quota/generated.json").read_text())
    assert report.item_count == 11
    assert generator.call_count == 11
    assert Counter(item["section"] for item in generated) == {"重点资讯": 8, "候选池": 3}


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
