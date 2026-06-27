# Graph Report - /opt/personal-agent-workspace/daily-ai-digest/output/graphify-pilot-full  (2026-06-27)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 253 nodes · 523 edges · 29 communities (12 shown, 17 thin omitted)
- Extraction: 76% EXTRACTED · 24% INFERRED · 0% AMBIGUOUS · INFERRED: 125 edges (avg confidence: 0.72)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a9486642`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Digest Pipeline Stages|Digest Pipeline Stages]]
- [[_COMMUNITY_Application Configuration|Application Configuration]]
- [[_COMMUNITY_Content Collection|Content Collection]]
- [[_COMMUNITY_Pipeline Components|Pipeline Components]]
- [[_COMMUNITY_Pipeline State Management|Pipeline State Management]]
- [[_COMMUNITY_Feishu Delivery System|Feishu Delivery System]]
- [[_COMMUNITY_Digest Rendering|Digest Rendering]]
- [[_COMMUNITY_Content Clustering|Content Clustering]]
- [[_COMMUNITY_Text Generation|Text Generation]]
- [[_COMMUNITY_Configuration Management|Configuration Management]]
- [[_COMMUNITY_Content Normalization|Content Normalization]]
- [[_COMMUNITY_Near-duplicate Clustering|Near-duplicate Clustering]]
- [[_COMMUNITY_Curated Source Collectors|Curated Source Collectors]]
- [[_COMMUNITY_Outbound Delivery Adapters|Outbound Delivery Adapters]]
- [[_COMMUNITY_Daily AI Digest Pipeline|Daily AI Digest Pipeline]]
- [[_COMMUNITY_Filtering and Scoring|Filtering and Scoring]]
- [[_COMMUNITY_Translation and Summarization|Translation and Summarization]]
- [[_COMMUNITY_Runnable Digest Jobs|Runnable Digest Jobs]]
- [[_COMMUNITY_Content Parsing Normalization|Content Parsing Normalization]]
- [[_COMMUNITY_Persistent Storage Helpers|Persistent Storage Helpers]]
- [[_COMMUNITY_Daily Script Execution|Daily Script Execution]]
- [[_COMMUNITY_Config Validation|Config Validation]]
- [[_COMMUNITY_Plain Text Format|Plain Text Format]]
- [[_COMMUNITY_Interactive Cards|Interactive Cards]]
- [[_COMMUNITY_Requirements|Requirements]]
- [[_COMMUNITY_Rich Text Briefing|Rich Text Briefing]]
- [[_COMMUNITY_Interactive Cards|Interactive Cards]]

## God Nodes (most connected - your core abstractions)
1. `run_daily()` - 37 edges
2. `PipelineDependencies` - 25 edges
3. `RawItem` - 20 edges
4. `AppConfig` - 19 edges
5. `NewsItem` - 18 edges
6. `FakeDelivery` - 16 edges
7. `FakeCollector` - 15 edges
8. `FakeGenerator` - 15 edges
9. `FeishuDelivery` - 13 edges
10. `DigestItem` - 13 edges

## Surprising Connections (you probably didn't know these)
- `test_extract_index_entries_accepts_openai_rss()` --calls--> `extract_index_entries()`  [INFERRED]
  tests/unit/test_collect.py → src/digest/collect/html_index.py
- `test_extract_index_entries_keeps_article_links()` --calls--> `extract_index_entries()`  [INFERRED]
  tests/unit/test_collect.py → src/digest/collect/html_index.py
- `test_extract_index_entries_sorts_feed_entries_by_published_date_descending()` --calls--> `extract_index_entries()`  [INFERRED]
  tests/unit/test_collect.py → src/digest/collect/html_index.py
- `test_digest_applies_top_story_quota_without_candidates()` --calls--> `run_daily()`  [INFERRED]
  tests/integration/test_daily.py → src/digest/jobs/daily.py
- `test_digest_reserves_sections_for_github_and_practice_sources()` --calls--> `run_daily()`  [INFERRED]
  tests/integration/test_daily.py → src/digest/jobs/daily.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Daily AI Digest Pipeline Stages** — daily_ai_digest_design_collect_stage, daily_ai_digest_design_extract_stage, daily_ai_digest_design_normalize_stage, daily_ai_digest_design_deduplicate_stage, daily_ai_digest_design_filter_stage, daily_ai_digest_design_cluster_stage, daily_ai_digest_design_translate_stage, daily_ai_digest_design_summarize_stage, daily_ai_digest_design_render_stage, daily_ai_digest_design_deliver_stage [EXTRACTED 0.75]
- **Daily AI Digest Data Models** — daily_ai_digest_design_raw_item, daily_ai_digest_design_news_item, daily_ai_digest_design_digest_item [EXTRACTED 0.75]
- **Implementation Artifacts** — findings_findings, progress_progress, task_plan_task_plan [EXTRACTED 0.75]

## Communities (29 total, 17 thin omitted)

### Community 0 - "Digest Pipeline Stages"
Cohesion: 0.10
Nodes (24): _collect_atom_releases(), collect_github_releases(), collect_github_repository_search(), collect_html_index(), extract_index_entries(), _published_at(), datetime, _default_collector() (+16 more)

### Community 1 - "Application Configuration"
Cohesion: 0.14
Nodes (29): cluster_items(), _cluster_key(), _release_family_key(), _title_key(), AppConfig, NewsItem, dedupe_exact(), hard_filter() (+21 more)

### Community 2 - "Content Collection"
Cohesion: 0.07
Nodes (30): Architecture, Compact Feishu Post Design, Compact Feishu Post Implementation Plan, Cluster Stage, Collect Stage, Daily AI Digest, Deduplicate Stage, Deliver Stage (+22 more)

### Community 3 - "Pipeline Components"
Cohesion: 0.25
Nodes (20): RawItem, config(), FakeCollector, FakeDelivery, FakeGenerator, raw(), raw_ranked(), raw_section() (+12 more)

### Community 4 - "Pipeline State Management"
Cohesion: 0.18
Nodes (13): StageCheckpoint, StageStatus, _checkpoint(), RunReport, atomic_write_json(), run_lock(), StateStore, StrEnum (+5 more)

### Community 5 - "Feishu Delivery System"
Cohesion: 0.19
Nodes (6): DeliveryResult, FeishuDelivery, FakeResponse, FakeSession, test_send_post_targets_chat_with_post_payload(), test_send_targets_chat_id()

### Community 6 - "Digest Rendering"
Cohesion: 0.24
Nodes (14): DigestItem, compact_text(), render_digest(), render_fault_digest(), render_feishu_post(), render_feishu_section_posts(), _section_block(), test_compact_text_caps_output_at_100_characters() (+6 more)

### Community 7 - "Content Clustering"
Cohesion: 0.16
Nodes (10): fallback_generation(), parse_generation(), MiniMaxGenerator, _dependencies(), main(), FakeCompletions, test_fallback_marks_english_translation_pending(), test_minimax_generator_uses_configured_model() (+2 more)

### Community 8 - "Text Generation"
Cohesion: 0.42
Nodes (7): load_config(), MonkeyPatch, Path, set_required_environment(), test_config_loads_shared_environment(), test_config_rejects_weights_that_do_not_sum_to_one(), write_configs()

### Community 9 - "Configuration Management"
Cohesion: 0.43
Nodes (6): canonicalize_url(), normalize_raw_item(), normalize_text(), raw_item(), test_canonicalize_url_removes_tracking_parameters(), test_normalize_raw_item_is_stable()

## Knowledge Gaps
- **27 isolated node(s):** `daily-ai-digest`, `run_daily.sh script`, `validate_config.sh script`, `graphify_refresh.sh script`, `Extract Stage` (+22 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **17 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `run_daily()` connect `Application Configuration` to `Digest Pipeline Stages`, `Pipeline Components`, `Pipeline State Management`, `Digest Rendering`, `Content Clustering`, `Text Generation`, `Configuration Management`?**
  _High betweenness centrality (0.162) - this node is a cross-community bridge._
- **Why does `PipelineDependencies` connect `Pipeline Components` to `Application Configuration`, `Pipeline State Management`, `Feishu Delivery System`, `Digest Rendering`, `Content Clustering`?**
  _High betweenness centrality (0.119) - this node is a cross-community bridge._
- **Why does `FeishuDelivery` connect `Feishu Delivery System` to `Pipeline Components`, `Pipeline State Management`, `Content Clustering`?**
  _High betweenness centrality (0.100) - this node is a cross-community bridge._
- **Are the 20 inferred relationships involving `run_daily()` (e.g. with `test_digest_applies_top_story_quota_without_candidates()` and `test_digest_reserves_sections_for_github_and_practice_sources()`) actually correct?**
  _`run_daily()` has 20 INFERRED edges - model-reasoned connections that need verification._
- **Are the 22 inferred relationships involving `PipelineDependencies` (e.g. with `FakeCollector` and `FakeDelivery`) actually correct?**
  _`PipelineDependencies` has 22 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `RawItem` (e.g. with `FakeCollector` and `FakeDelivery`) actually correct?**
  _`RawItem` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `AppConfig` (e.g. with `FakeCollector` and `FakeDelivery`) actually correct?**
  _`AppConfig` has 7 INFERRED edges - model-reasoned connections that need verification._