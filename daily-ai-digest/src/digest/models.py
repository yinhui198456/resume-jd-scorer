from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class StageStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    DEGRADED = "degraded"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(slots=True)
class RawItem:
    run_id: str
    schema_version: int
    raw_id: str
    source_id: str
    source_tier: int
    source_url: str
    canonical_url: str
    title: str
    raw_body: str
    author: str | None
    published_at: str | None
    fetched_at: str
    language: str
    content_hash: str
    fetch_status: str = "ok"
    fetch_error: str | None = None


@dataclass(slots=True)
class NewsItem:
    run_id: str
    schema_version: int
    news_id: str
    raw_ids: list[str]
    canonical_url: str
    dedupe_key: str
    normalized_title: str
    normalized_body: str
    language: str
    published_at: str | None
    fetched_at: str
    source_tier: int
    topic_tags: list[str] = field(default_factory=list)
    cluster_id: str | None = None
    score: float = 0.0
    score_components: dict[str, float] = field(default_factory=dict)
    filter_decision: str = "pending"
    filter_reasons: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DigestItem:
    run_id: str
    schema_version: int
    digest_item_id: str
    news_ids: list[str]
    section: str
    rank: int
    chinese_title: str
    summary: str
    why_it_matters: str
    original_language: str
    translation_status: str
    source_links: list[str]
    generated_at: str


@dataclass(slots=True)
class StageCheckpoint:
    stage: str
    status: StageStatus
    input_paths: list[str]
    output_paths: list[str]
    input_count: int
    output_count: int
    started_at: str
    finished_at: str | None = None
    error_code: str | None = None
    error_message: str | None = None


@dataclass(slots=True)
class AppConfig:
    root: str
    sources: dict[str, Any]
    filters: dict[str, Any]
    topics: dict[str, Any]
    schedule: dict[str, Any]
    minimax_api_key: str
    minimax_base_url: str
    minimax_model: str
    feishu_app_id: str
    feishu_app_secret: str
    feishu_chat_id: str
    learning_plan_spreadsheet_token: str = "R4LAsRmQKhfMXYtV7UacSeaGngg"
    learning_plan_sheet_title: str = "主任务"
