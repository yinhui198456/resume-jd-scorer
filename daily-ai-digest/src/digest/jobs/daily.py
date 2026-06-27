import hashlib
import argparse
import json
import re
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable
from zoneinfo import ZoneInfo

from digest.cluster.group import cluster_items
from digest.collect.github import collect_github_releases, collect_github_repository_search
from digest.collect.html_index import collect_html_index
from digest.config import load_config
from digest.deliver.feishu import FeishuDelivery
from digest.filter.quality import dedupe_exact, hard_filter, tag_topics, weighted_score
from digest.generate.render import render_digest, render_fault_digest, render_feishu_section_posts
from digest.generate.minimax import MiniMaxGenerator
from digest.generate.common import fallback_generation
from digest.models import AppConfig, DigestItem, NewsItem, RawItem, StageCheckpoint, StageStatus
from digest.parse.normalize import normalize_raw_item
from digest.storage.state import StateStore, atomic_write_json, run_lock


STAGES = ["collect", "extract", "normalize", "deduplicate", "filter", "cluster", "translate", "summarize", "render", "deliver"]


@dataclass(slots=True)
class PipelineDependencies:
    collector: Callable
    generator: Callable
    delivery: object


@dataclass(slots=True)
class RunReport:
    run_id: str
    status: str
    digest_path: str
    delivery_key: str
    item_count: int


def _checkpoint(store: StateStore, run_id: str, stage: str, status: StageStatus, now: datetime, count: int = 0, outputs: list[str] | None = None, error_code: str | None = None, error_message: str | None = None) -> None:
    store.save_checkpoint(run_id, StageCheckpoint(stage, status, [], outputs or [], count, count, now.isoformat(), now.isoformat(), error_code, error_message))


def _read_items(path: Path, item_type):
    return [item_type(**value) for value in json.loads(path.read_text(encoding="utf-8"))]


def _score(item: NewsItem, config: AppConfig) -> None:
    text = f"{item.normalized_title} {item.normalized_body}".casefold()
    evidence_words = ("code", "demo", "benchmark", "release", "documentation", "link")
    components = {
        "source_trust": 1.0 if item.source_tier == 1 else 0.6,
        "topic_match": 1.0 if item.topic_tags else 0.0,
        "information_density": min(len(item.normalized_body) / 100, 1.0),
        "recency": 1.0,
        "originality": 1.0,
        "evidence": 1.0 if any(word in text for word in evidence_words) else 0.0,
    }
    item.score_components = components
    item.score = weighted_score(components, config.filters["weights"])


def _source_groups(config: AppConfig) -> dict[str, str]:
    groups: dict[str, str] = {}
    for section in ("html_indexes", "github_releases", "github_repository_search"):
        for source in config.sources.get(section, []):
            if source.get("content_group"):
                groups[str(source["id"])] = str(source["content_group"])
    return groups


def _candidate_flags(config: AppConfig) -> dict[str, bool]:
    flags: dict[str, bool] = {}
    for section in ("html_indexes", "github_releases", "github_repository_search"):
        for source in config.sources.get(section, []):
            if "candidate_pool" in source:
                flags[str(source["id"])] = bool(source["candidate_pool"])
    return flags


def _published_at_requirements(config: AppConfig) -> dict[str, bool]:
    requirements: dict[str, bool] = {}
    for section in ("html_indexes", "github_releases", "github_repository_search"):
        for source in config.sources.get(section, []):
            if "require_published_at" in source:
                requirements[str(source["id"])] = bool(source["require_published_at"])
    return requirements


def _requires_published_at(
    item: NewsItem, raw_by_id: dict[str, RawItem], requirements: dict[str, bool]
) -> bool:
    return any(
        requirements.get(raw_by_id[raw_id].source_id, False)
        for raw_id in item.raw_ids
        if raw_id in raw_by_id
    )


def _cluster_group(
    cluster: list[NewsItem],
    raw_by_id: dict[str, RawItem],
    groups: dict[str, str],
) -> str:
    for news in cluster:
        for raw_id in news.raw_ids:
            source_id = raw_by_id.get(raw_id).source_id if raw_id in raw_by_id else ""
            if source_id in groups:
                return groups[source_id]
    return "default"


def _cluster_candidate_allowed(
    cluster: list[NewsItem],
    raw_by_id: dict[str, RawItem],
    flags: dict[str, bool],
) -> bool:
    if not flags:
        return True
    saw_configured_source = False
    for news in cluster:
        for raw_id in news.raw_ids:
            raw = raw_by_id.get(raw_id)
            if not raw:
                continue
            if raw.source_id in flags:
                saw_configured_source = True
                if flags[raw.source_id]:
                    return True
    return not saw_configured_source


def _cluster_text(cluster: list[NewsItem]) -> str:
    return " ".join(
        f"{item.normalized_title} {item.normalized_body}" for item in cluster
    ).casefold()


def _practice_allowed(cluster: list[NewsItem], config: AppConfig) -> bool:
    rules = config.filters.get("practice_methodology", {})
    include = [str(keyword).casefold() for keyword in rules.get("include_keywords", [])]
    exclude = [str(keyword).casefold() for keyword in rules.get("exclude_keywords", [])]
    text = _cluster_text(cluster)
    if any(keyword in text for keyword in exclude):
        return False
    if re.search(r"\b\d+\.\d+(?:\.\d+)?[a-z]?\d*\b", text) and any(
        keyword in text
        for keyword in ("fix", "fixes", "bugfix", "dependency pin", "pyproject.toml")
    ):
        return False
    return not include or any(keyword in text for keyword in include)


def run_daily(root: Path, config: AppConfig, dependencies: PipelineDependencies, run_id: str, now: datetime) -> RunReport:
    data_dir = root / "data"
    state_dir = data_dir / "state"
    store = StateStore(state_dir)
    run_path = state_dir / "runs" / run_id / "run.json"
    with run_lock(state_dir):
        if run_path.exists():
            existing = json.loads(run_path.read_text(encoding="utf-8"))
            if existing.get("status") == "succeeded" or (
                existing.get("status") == "degraded" and existing.get("item_count", 0) > 0
            ):
                return RunReport(run_id, existing["status"], existing["digest_path"], existing["delivery_key"], existing["item_count"])

        config_hash = hashlib.sha256(json.dumps({"sources": config.sources, "filters": config.filters, "topics": config.topics, "schedule": config.schedule}, sort_keys=True).encode()).hexdigest()
        if not run_path.exists():
            store.create_run(run_id, config_hash, None)

        run_dir = state_dir / "runs" / run_id
        raw_path = data_dir / "raw" / f"{run_id}.json"
        source_health_path = run_dir / "source_health.json"
        cached_raw = (
            _read_items(raw_path, RawItem)
            if raw_path.exists() and store.resume_stage(run_id, STAGES) != "collect"
            else []
        )
        if cached_raw:
            health = json.loads(source_health_path.read_text(encoding="utf-8")) if source_health_path.exists() else {}
            raw_items, failures = cached_raw, health.get("failures", [])
        else:
            raw_items, failures = dependencies.collector(config, run_id, now)
            atomic_write_json(raw_path, [asdict(item) for item in raw_items])
            health = {"run_id": run_id, "status": "degraded" if failures else "healthy", "failures": failures, "updated_at": now.isoformat()}
            atomic_write_json(source_health_path, health)
            atomic_write_json(state_dir / "source_health.json", health)
            _checkpoint(
                store,
                run_id,
                "collect",
                StageStatus.DEGRADED if failures else StageStatus.SUCCEEDED,
                now,
                len(raw_items),
                [str(raw_path), str(source_health_path)],
                "PARTIAL_SOURCE_FAILURE" if failures and raw_items else "TOTAL_SOURCE_FAILURE" if failures else None,
                json.dumps(failures, ensure_ascii=False) if failures else None,
            )

        if not raw_items:
            for stage in STAGES[1:8]:
                _checkpoint(store, run_id, stage, StageStatus.SKIPPED, now)
            text = render_fault_digest(run_id, now.isoformat(), failures or [{"source_id": "all", "error_code": "NO_USABLE_ITEMS"}])
            post_payload = None
            delivery_mode = "text"
            status = "degraded"
            item_count = 0
        else:
            _checkpoint(store, run_id, "extract", StageStatus.SUCCEEDED, now, len(raw_items), [str(raw_path)])
            news_items = [normalize_raw_item(item) for item in raw_items]
            normalized_path = data_dir / "normalized" / f"{run_id}.json"
            atomic_write_json(normalized_path, [asdict(item) for item in news_items])
            _checkpoint(store, run_id, "normalize", StageStatus.SUCCEEDED, now, len(news_items), [str(normalized_path)])
            news_items = dedupe_exact(news_items)
            _checkpoint(store, run_id, "deduplicate", StageStatus.SUCCEEDED, now, len(news_items), [str(normalized_path)])
            eligible: list[NewsItem] = []
            raw_by_id = {item.raw_id: item for item in raw_items}
            published_requirements = _published_at_requirements(config)
            for item in news_items:
                if hard_filter(
                    item,
                    config.sources.get("blocked_domains", []),
                    config.filters["allowed_languages"],
                    int(config.filters["max_age_hours"]),
                    now,
                    require_published_at=_requires_published_at(item, raw_by_id, published_requirements),
                )[0]:
                    tag_topics(item, config.topics.get("primary", []))
                    _score(item, config)
                    if item.score >= float(config.filters["thresholds"]["candidate"]):
                        eligible.append(item)
            filtered_path = data_dir / "filtered" / f"{run_id}.json"
            atomic_write_json(filtered_path, [asdict(item) for item in eligible])
            _checkpoint(store, run_id, "filter", StageStatus.SUCCEEDED, now, len(eligible), [str(filtered_path)])
            clusters = cluster_items(eligible)
            _checkpoint(store, run_id, "cluster", StageStatus.SUCCEEDED, now, len(clusters), [str(filtered_path)])
            ranked_clusters = sorted(
                (sorted(cluster, key=lambda item: (-item.score, item.news_id)) for cluster in clusters),
                key=lambda cluster: (-cluster[0].score, cluster[0].news_id),
            )
            source_groups = _source_groups(config)
            candidate_flags = _candidate_flags(config)
            top_limit = int(config.filters.get("quotas", {}).get("top_stories", 10))
            productivity_limit = int(
                config.filters.get("quotas", {}).get(
                    "productivity_projects",
                    int(config.filters.get("quotas", {}).get("github_projects", 0))
                    + int(config.filters.get("quotas", {}).get("practice_methodology", 0)),
                )
            )
            target_total = top_limit + productivity_limit
            digest_threshold = float(config.filters["thresholds"]["digest"])
            selected: list[tuple[str, list[NewsItem]]] = []
            selected_keys: set[str] = set()
            counts = {"重点资讯": 0, "生产力项目": 0}
            for cluster in ranked_clusters:
                cluster_key = cluster[0].news_id
                group = _cluster_group(cluster, raw_by_id, source_groups)
                if group == "practice_methodology" and not _practice_allowed(cluster, config):
                    continue
                if group in {"github_projects", "practice_methodology"} and counts["生产力项目"] < productivity_limit:
                    selected.append(("生产力项目", cluster))
                    selected_keys.add(cluster_key)
                    counts["生产力项目"] += 1
                elif group == "default" and cluster[0].score >= digest_threshold and counts["重点资讯"] < top_limit:
                    selected.append(("重点资讯", cluster))
                    selected_keys.add(cluster_key)
                    counts["重点资讯"] += 1
            for cluster in ranked_clusters:
                if len(selected) >= target_total:
                    break
                cluster_key = cluster[0].news_id
                if cluster_key in selected_keys:
                    continue
                group = _cluster_group(cluster, raw_by_id, source_groups)
                if group == "practice_methodology" and not _practice_allowed(cluster, config):
                    continue
                if group in {"github_projects", "practice_methodology"} and counts["生产力项目"] < productivity_limit:
                    selected.append(("生产力项目", cluster))
                    selected_keys.add(cluster_key)
                    counts["生产力项目"] += 1
                elif group == "default" and counts["重点资讯"] < top_limit:
                    selected.append(("重点资讯", cluster))
                    selected_keys.add(cluster_key)
                    counts["重点资讯"] += 1
            digest_items: list[DigestItem] = []
            section_counts: dict[str, int] = {}
            for section, cluster in selected:
                primary = cluster[0]
                section_counts[section] = section_counts.get(section, 0) + 1
                generated = dependencies.generator(primary)
                digest_items.append(DigestItem(run_id, 1, hashlib.sha256(primary.news_id.encode()).hexdigest(), [item.news_id for item in cluster], section, section_counts[section], generated["chinese_title"], generated["summary"], generated["why_it_matters"], primary.language, generated.get("translation_status", "translated"), [primary.canonical_url] if primary.canonical_url else [], now.isoformat()))
            generation_path = run_dir / "generated.json"
            atomic_write_json(generation_path, [asdict(item) for item in digest_items])
            _checkpoint(store, run_id, "translate", StageStatus.SUCCEEDED, now, len(digest_items), [str(generation_path)])
            _checkpoint(store, run_id, "summarize", StageStatus.SUCCEEDED, now, len(digest_items), [str(generation_path)])
            if digest_items:
                sections = {
                    section: [item for item in digest_items if item.section == section]
                    for section in ("重点资讯", "生产力项目")
                }
                text = render_digest(run_id, now.isoformat(), sections, health)
                post_payloads = render_feishu_section_posts(now.isoformat(), sections, health)
                delivery_mode = "posts"
                status = "succeeded"
            else:
                text = render_fault_digest(run_id, now.isoformat(), [{"source_id": "all", "error_code": "NO_USABLE_ITEMS"}])
                post_payloads = []
                delivery_mode = "text"
                status = "degraded"
            item_count = len(digest_items)

        digest_path = data_dir / "digests" / f"{run_id}.md"
        digest_path.parent.mkdir(parents=True, exist_ok=True)
        digest_path.write_text(text, encoding="utf-8")
        _checkpoint(store, run_id, "render", StageStatus.SUCCEEDED, now, item_count, [str(digest_path)])
        delivery_key = f"{run_id}:{hashlib.sha256(text.encode()).hexdigest()}"
        delivery_log = state_dir / "delivery_log.json"
        log = json.loads(delivery_log.read_text(encoding="utf-8")) if delivery_log.exists() else {}
        if log.get(delivery_key, {}).get("status") != "succeeded":
            atomic_write_json(delivery_log, {**log, delivery_key: {"status": "attempting"}})
            if delivery_mode == "posts":
                message_ids = []
                for index, post_payload in enumerate(post_payloads, 1):
                    result = dependencies.delivery.send_post(post_payload, f"{delivery_key}:{index}")
                    message_ids.append(result.message_id)
                result = type("DeliveryBatch", (), {"message_id": ",".join(message_ids)})()
            else:
                result = dependencies.delivery.send_text(text, delivery_key)
            atomic_write_json(delivery_log, {**log, delivery_key: {"status": "succeeded", "message_id": result.message_id}})
        _checkpoint(store, run_id, "deliver", StageStatus.SUCCEEDED, now, item_count, [str(delivery_log)])
        report_data = {"run_id": run_id, "status": status, "digest_path": str(digest_path), "delivery_key": delivery_key, "item_count": item_count, "finished_at": now.isoformat()}
        atomic_write_json(run_path, report_data)
        atomic_write_json(state_dir / "run_state.json", report_data)
        return RunReport(run_id, status, str(digest_path), delivery_key, item_count)


def within_catch_up_window(now: datetime, start_time: str, window_hours: int) -> bool:
    hour, minute = (int(part) for part in start_time.split(":"))
    scheduled = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    delay = (now - scheduled).total_seconds()
    return 0 <= delay <= window_hours * 3600


def _default_collector(config: AppConfig, run_id: str, now: datetime):
    items: list[RawItem] = []
    failures: list[dict[str, str]] = []
    for source in config.sources.get("html_indexes", []):
        try:
            items.extend(collect_html_index(source, run_id=run_id, now=now))
        except Exception as error:
            status = getattr(getattr(error, "response", None), "status_code", None)
            failures.append({"source_id": source["id"], "error_code": f"HTTP_{status}" if status else type(error).__name__})
    for source in config.sources.get("github_releases", []):
        try:
            items.extend(collect_github_releases(source, run_id=run_id, now=now))
        except Exception as error:
            status = getattr(getattr(error, "response", None), "status_code", None)
            failures.append({"source_id": source["id"], "error_code": f"HTTP_{status}" if status else type(error).__name__})
    for source in config.sources.get("github_repository_search", []):
        try:
            items.extend(collect_github_repository_search(source, run_id=run_id, now=now))
        except Exception as error:
            status = getattr(getattr(error, "response", None), "status_code", None)
            failures.append({"source_id": source["id"], "error_code": f"HTTP_{status}" if status else type(error).__name__})
    return items, failures


def _dependencies(config: AppConfig) -> PipelineDependencies:
    minimax = MiniMaxGenerator(
        config.minimax_api_key, config.minimax_base_url, config.minimax_model
    )

    def generate(item: NewsItem):
        try:
            return {**minimax.generate_text(f"Title: {item.normalized_title}\nBody: {item.normalized_body}"), "translation_status": "translated"}
        except Exception:
            return fallback_generation(item.normalized_title, item.normalized_body, item.language)

    return PipelineDependencies(
        _default_collector,
        generate,
        FeishuDelivery(config.feishu_app_id, config.feishu_app_secret, config.feishu_chat_id),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the daily AI digest")
    parser.add_argument("--run-id")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--smoke-minimax", action="store_true")
    parser.add_argument("--smoke-feishu", action="store_true")
    parser.add_argument("--message", default="Daily AI Digest delivery test")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[3]
    config = load_config(root)
    deps = _dependencies(config)
    now = datetime.now(ZoneInfo(config.schedule.get("timezone", "Asia/Shanghai")))
    if args.smoke_minimax:
        generator = MiniMaxGenerator(
            config.minimax_api_key, config.minimax_base_url, config.minimax_model
        )
        result = generator.generate_text(
            "Title: MiniMax smoke test\nBody: Return a concise Chinese summary."
        )
        print(json.dumps(result, ensure_ascii=False))
        return 0
    if args.smoke_feishu:
        result = deps.delivery.send_text(args.message, f"smoke:{uuid.uuid4().hex}")
        print(result.message_id)
        return 0
    if not args.force and not within_catch_up_window(now, config.schedule["start_time"], int(config.schedule["catch_up_window_hours"])):
        atomic_write_json(root / "data/state/run_state.json", {"status": "missed", "checked_at": now.isoformat()})
        return 0
    run_id = args.run_id or f"{now.strftime('%Y%m%dT%H%M%S%z')}-{uuid.uuid4().hex[:8]}"
    report = run_daily(root, config, deps, run_id, now)
    print(json.dumps(asdict(report), ensure_ascii=False))
    return 0 if report.status in {"succeeded", "degraded"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
