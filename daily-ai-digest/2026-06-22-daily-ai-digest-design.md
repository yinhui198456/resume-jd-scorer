# Daily AI Digest Design

## Overview

This project builds a daily AI news pipeline for a single user. It starts at 08:45 every morning, ingests content from curated sources, filters noise, merges overlapping items, translates English items into Chinese, and delivers a concise digest after processing completes.

The product goal is not broad search or social feed aggregation. The goal is a stable, low-noise, readable briefing that helps the user quickly scan useful AI updates.

## Goals

- Start one daily digest run at 08:45 in `Asia/Shanghai` and deliver it after processing completes.
- Prioritize application-layer AI news, industry updates, and Codex/CC practice notes.
- Translate English content into Chinese while preserving key technical terms.
- Keep original source links for verification.
- Reduce noise through whitelist-first collection, hard filtering, and quality scoring.

## Non-Goals

- No multi-user workflow.
- No public feed or community posting.
- No open-web search product.
- No personalized long-term recommendation engine in the first version.
- No dashboard as the primary interface.

## Workspace Root

The shared project root is:

`/opt/personal-agent-workspace/daily-ai-digest`

This root is treated as the source of truth for project files, non-secret configs, and runtime data. Shared secrets are loaded from `/opt/personal-agent-workspace/.env` so sibling personal-agent projects can reuse the same credentials without copying them.

## Source Strategy

Sources are split into three priority tiers:

- Tier 1: official sources
  - Company blogs
  - Product release notes
  - GitHub release pages
  - Documentation updates
  - Papers and official announcements
- Tier 2: signal sources
  - GitHub AI hotspot projects
  - X accounts from known AI practitioners
  - Domestic AI creators and practitioners
- Tier 3: supplemental sources
  - Trending lists
  - Community discussion threads
  - Secondary aggregators

CSDN is blocked by default at the domain level.

The MVP source whitelist is:

- Tier 1 HTML indexes:
  - `https://openai.com/news/`
  - `https://developers.openai.com/codex/changelog`
  - `https://www.anthropic.com/news`
- Tier 1 GitHub releases:
  - `openai/codex`
  - `anthropics/claude-code`
  - `modelcontextprotocol/python-sdk`

Tier 2 is empty in the MVP. `36kr.com` is allowed as Tier 3 but is not actively collected in the initial whitelist.

## Content Scope

The digest focuses on:

- Agent
- RAG
- MCP
- Function Calling
- Tool calling
- Evaluation
- Observability
- Code assistants
- Codex / CC practice

Secondary content includes:

- Model releases
- Inference improvements
- Open source framework updates
- Product launches
- Policy and funding news

## Pipeline

The system runs as a single sequential pipeline once per day at 08:45:

1. Collect
2. Extract
3. Normalize
4. Deduplicate
5. Filter
6. Cluster
7. Translate
8. Summarize
9. Render
10. Deliver

The pipeline is sequential in time, but each step is independently recoverable. Every step reads persisted input, writes persisted output, and records a checkpoint before the next step starts. A resumed run starts from the first `failed` or interrupted `running` stage. A `skipped` stage remains terminal unless its recorded skip condition has changed.

Each stage has one of the following states:

- `pending`: the stage has not started.
- `running`: the stage started but has not committed its checkpoint.
- `succeeded`: the normal output was committed.
- `degraded`: fallback output was committed and later stages may continue.
- `failed`: no usable output was produced.
- `skipped`: the stage was intentionally bypassed because its input was unavailable or unnecessary.

Stage output is written to a temporary file and atomically renamed into place. A stage may not be marked `succeeded` or `degraded` until its output is durable. Re-running a completed stage for the same `run_id` must produce the same logical result unless the operator explicitly requests reprocessing with a new configuration snapshot.

## Data Model

The system uses three core item types. All timestamps use ISO 8601 with an explicit timezone, and all item types carry `run_id` and `schema_version`.

- `RawItem`
  - `raw_id`: stable hash of canonical URL, source ID, and source-native item ID
  - `source_id`, `source_tier`, `source_url`, `canonical_url`
  - `title`, `raw_body`, `author`
  - `published_at`, `fetched_at`, `language`
  - `content_hash`, `fetch_status`, `fetch_error`
- `NewsItem`
  - `news_id`, `raw_ids`, `canonical_url`, `dedupe_key`
  - `normalized_title`, `normalized_body`, `language`
  - `published_at`, `fetched_at`
  - `topic_tags`, `cluster_id`
  - `score`, `score_components`, `filter_decision`, `filter_reasons`
- `DigestItem`
  - `digest_item_id`, `news_ids`, `section`, `rank`
  - `chinese_title`, `summary`, `why_it_matters`
  - `original_language`, `translation_status`
  - `source_links`, `generated_at`

The separation is deliberate:

- Raw data is kept for traceability.
- Intermediate data is kept for reprocessing.
- Final digest entries are kept for audit and replay.

## Filtering Rules

Filtering is split into hard filters and scoring.

Hard filters:

- Reject blocked domains before extraction.
- Keep English and Chinese content only.
- Reject items older than the configured `max_age_hours`; the MVP default is 72 hours based on `published_at`, falling back to `fetched_at` when publication time is unavailable.
- Reject exact duplicates by canonical URL or content hash.
- Merge near-duplicates during clustering while retaining all original source links.

The MVP uses deterministic, rule-based weighted scoring. Each component is normalized to `[0, 1]`, and the final score is the weighted sum:

- Source trust: `0.30`
- Topic match: `0.25`
- Information density: `0.15`
- Recency: `0.15`
- Originality: `0.10`
- Evidence such as code, demo, benchmark, release notes, or primary links: `0.05`

Weights, thresholds, and component rules live in `configs/filters.yml`. Every `NewsItem` stores its component values, final score, decision, and rejection reasons so the result can be reproduced without an LLM. LLM output is not used as a scoring input in the MVP.

Suggested thresholds:

- Include in digest at `score >= 0.70`
- Keep in candidate pool at `score >= 0.55`

Items below `0.55` are rejected. Section quotas are configured in `configs/filters.yml`; the default maximum is 10 top stories, 5 Codex / CC practice notes, 5 overseas signals, 5 domestic observations, and 10 candidate items. An item appears in only one primary section. Ties are resolved by score, publication time, source tier, and stable item ID, in that order.

## Digest Layout

The daily digest uses a fixed structure:

- Today’s conclusion
- Top stories
- Codex / CC practice notes
- Overseas signals
- Domestic observations
- Candidate pool

Each top story entry includes:

- Chinese title
- One-sentence summary
- Why it matters
- Source link

English items are translated into Chinese, but key technical terms remain in English where needed for readability.

## Generation Backend

Translation and summarization use the existing MiniMax CN configuration shared through `/opt/personal-agent-workspace/.env`:

- `MINIMAX_API_KEY`
- `MINIMAX_BASE_URL=https://api.minimaxi.com/v1/`
- `MINIMAX_MODEL=MiniMax-M3`

The client uses MiniMax's OpenAI-compatible API surface. Deterministic filtering and scoring do not call the model. If MiniMax is unavailable or returns invalid output, the pipeline records the generation error, preserves English text with `translation_status=pending`, and uses the rule-based summary fallback.

## Scheduling

The scheduler starts the pipeline once per day at 08:45 in `Asia/Shanghai`. The time is a run start time, not a delivery deadline. The run records its scheduled time, actual start time, completion time, and duration.

There are no separate prefetch and postfetch execution windows in the first version.

This keeps the scheduler simple and avoids conflicts between a primary digest and late supplemental updates.

Only one run may execute at a time. The job acquires a process lock before creating a run; a second invocation exits without starting another pipeline and records the lock conflict. Manual retries reuse the original `run_id`. Intentional full reprocessing creates a new `run_id` and records the prior run as its parent.

If the scheduled invocation is missed, the scheduler may start one catch-up run when the service returns, provided the missed time is within `catch_up_window_hours` in `configs/schedule.yml`. Outside that window, it records a missed run and waits for the next scheduled execution.

## Failure Handling

The system degrades locally instead of failing globally.

- Source fetch failure:
  - Log the error and continue with other sources.
- Text extraction failure:
  - Fall back to title, source, and URL.
- Translation failure:
  - Keep the English summary and mark translation as pending.
- Clustering failure:
  - Fall back to source-grouped output.
- LLM summary failure:
  - Use a rule-based template summary.
- Delivery failure:
  - Retry according to bounded settings in `configs/schedule.yml`, then persist the rendered digest and delivery state for a later retry.

The digest must not silently fail and must not emit an empty report. If all configured sources fail or no usable items remain after filtering, the system renders and delivers a fault digest containing the run ID, failure summary, affected sources, and operator-facing recovery note. It must not reuse old news as if it were current.

Rendering always completes to `data/digests/` before delivery begins. The MVP delivery adapter sends the rendered digest to the current Feishu group using the existing internal Feishu application robot. It obtains a tenant access token from `FEISHU_APP_ID` and `FEISHU_APP_SECRET`, and sends to the `FEISHU_CHAT_ID` loaded from the shared environment file. The robot must be present in the group and have permission to speak.

## Runtime State

Each run has a unique `run_id` and stores immutable configuration metadata plus per-stage checkpoints under `data/state/runs/<run_id>/`. Minimum runtime state is:

- `run_state.json`: current run pointer and latest overall outcome
- `source_health.json`
- `dedupe_index.json`
- `delivery_log.json`
- `runs/<run_id>/run.json`: schedule, configuration snapshot hash, stage states, counts, timings, errors, and parent run
- `runs/<run_id>/stages/<stage>.json`: stage input references, output references, status, counts, timing, and error summary

These files are sufficient to answer:

- Did today’s run succeed?
- Which source failed?
- Which items were deduped?
- Was delivery successful?
- Which stage should a retry resume from?
- Which configuration and inputs produced the digest?

State updates use atomic file replacement. Error entries contain a stable error code and sanitized message; credentials and authorization headers must never be persisted.

## Retention and Idempotency

Raw, intermediate, digest, and state records are retained for traceability in the MVP. The system does not delete historical data automatically. Operators may archive old run directories after generating a separate cleanup proposal and verifying that referenced digests remain replayable.

Collection and delivery are idempotent within a `run_id`. The delivery adapter records a deterministic delivery key before and after each attempt so a retry does not intentionally send the same digest twice. The dedupe index is updated only after a digest is rendered successfully.

## MVP Scope

The first version includes:

- Source whitelist and blacklist
- Unified collection
- Deduplication
- Basic filtering
- Topic tagging and scoring
- English-to-Chinese translation
- Daily run starting at 08:45 in `Asia/Shanghai`
- Source links in all digest entries

The first version excludes:

- User profiling
- Weekly or monthly reports
- Multi-user collaboration
- Visualization dashboards
- Unbounded web search

## MVP Acceptance Criteria

The MVP is accepted when automated tests and a controlled end-to-end run demonstrate all of the following:

- A scheduled run starts at 08:45 in `Asia/Shanghai`, or is recorded as missed according to the configured catch-up policy.
- Concurrent invocation does not create a second active run.
- Every stage commits a recoverable checkpoint with input and output counts.
- Restarting an interrupted run resumes from the first incomplete stage without duplicating committed outputs.
- Every delivered news entry has at least one original source link.
- Blocked domains, unsupported languages, stale items, and exact duplicates are excluded deterministically.
- The same fixture data and configuration produce the same scores, ordering, and filter decisions.
- English items preserve required technical terms and record translation status.
- A partial source failure produces a normal digest with source-health information in runtime state.
- A total source failure produces a non-empty fault digest.
- A delivery failure leaves a rendered digest and retryable delivery record.
- Unit tests cover normalization, filtering, scoring, deduplication, state transitions, and rendering; integration tests cover recovery and delivery idempotency.

## Directory Layout

```text
/opt/personal-agent-workspace/daily-ai-digest/
├── README.md
├── pyproject.toml
├── .env.example
├── configs/
│   ├── sources.yml
│   ├── filters.yml
│   ├── topics.yml
│   └── schedule.yml
├── src/
│   └── digest/
│       ├── collect/
│       ├── parse/
│       ├── filter/
│       ├── cluster/
│       ├── generate/
│       ├── deliver/
│       ├── storage/
│       └── jobs/
├── data/
│   ├── raw/
│   ├── normalized/
│   ├── filtered/
│   ├── digests/
│   └── state/
│       └── runs/
├── templates/
│   ├── daily_digest.md
│   └── prompt/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── scripts/
│   ├── run_daily.sh
│   ├── sync_sources.sh
│   └── validate_config.sh
└── docs/
    ├── architecture.md
    ├── source-policy.md
    └── operations.md
```

## Resolved Implementation Decisions

- The first delivery target is the current Feishu group through the existing internal application robot.
- Tier 2 X and domestic account lists remain empty in the MVP.
- `36kr.com` is allowed as Tier 3 but is not actively collected in the initial whitelist.
- Translation and summarization use the shared MiniMax `MiniMax-M3` configuration.
