# Graph Report - /opt/personal-agent-workspace/daily-ai-digest/output/graphify-pilot-full  (2026-06-28)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 247 nodes · 488 edges · 31 communities (13 shown, 18 thin omitted)
- Extraction: 82% EXTRACTED · 18% INFERRED · 0% AMBIGUOUS · INFERRED: 87 edges (avg confidence: 0.77)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `cde97372`
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
- [[_COMMUNITY_Interactive Cards|Interactive Cards]]
- [[_COMMUNITY_Requirements|Requirements]]
- [[_COMMUNITY_Rich Text Briefing|Rich Text Briefing]]
- [[_COMMUNITY_Interactive Cards|Interactive Cards]]
- [[_COMMUNITY_Message Splitting|Message Splitting]]
- [[_COMMUNITY_Manual Pipeline|Manual Pipeline]]

## God Nodes (most connected - your core abstractions)
1. `run_daily()` - 28 edges
2. `PipelineDependencies` - 17 edges
3. `FakeDelivery` - 15 edges
4. `FakeCollector` - 14 edges
5. `FakeGenerator` - 14 edges
6. `FeishuDelivery` - 10 edges
7. `DigestItem` - 10 edges
8. `test_normal_digest_uses_compact_post_and_one_primary_link()` - 10 edges
9. `FakeSession` - 10 edges
10. `StateStore` - 9 edges

## Surprising Connections (you probably didn't know these)
- `test_atomic_write_replaces_complete_json()` --calls--> `atomic_write_json()`  [INFERRED]
  tests/unit/test_state.py → src/digest/storage/state.py
- `test_default_collector_includes_github_repository_search()` --calls--> `_default_collector()`  [INFERRED]
  tests/unit/test_default_collector.py → src/digest/jobs/daily.py
- `test_catch_up_window_rejects_late_start()` --calls--> `within_catch_up_window()`  [INFERRED]
  tests/unit/test_schedule.py → src/digest/jobs/daily.py
- `test_equal_normalized_titles_cluster()` --calls--> `cluster_items()`  [INFERRED]
  tests/unit/test_cluster.py → src/digest/cluster/group.py
- `test_same_github_release_repository_versions_cluster()` --calls--> `cluster_items()`  [INFERRED]
  tests/unit/test_cluster.py → src/digest/cluster/group.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Configuration Files** — filters_yml, schedule_yml, sources_yml, topics_yml [EXTRACTED 0.75]
- **Documentation Files** — architecture_doc, operations_doc, source_policy_doc, compact_feishu_post_plan, compact_feishu_post_design [EXTRACTED 0.75]
- **Project Artifacts** — daily_ai_digest_design_project, daily_ai_digest_readme, daily_ai_digest_findings, daily_ai_digest_progress, daily_ai_digest_task_plan [EXTRACTED 0.75]

## Communities (31 total, 18 thin omitted)

### Community 0 - "Digest Pipeline Stages"
Cohesion: 0.14
Nodes (30): AppConfig, cluster_items(), _cluster_key(), _release_family_key(), _title_key(), _version_title_family_key(), _candidate_flags(), _checkpoint() (+22 more)

### Community 1 - "Application Configuration"
Cohesion: 0.12
Nodes (20): load_config(), AppConfig, StageCheckpoint, StageStatus, MonkeyPatch, Path, atomic_write_json(), run_lock() (+12 more)

### Community 2 - "Content Collection"
Cohesion: 0.12
Nodes (16): collect_html_index(), extract_index_entries(), _published_at(), datetime, FakeResponse, FakeSession, SequencedSession, test_collect_github_releases_falls_back_to_atom_on_rate_limit() (+8 more)

### Community 3 - "Pipeline Components"
Cohesion: 0.23
Nodes (21): config(), FakeCollector, FakeDelivery, FakeGenerator, raw(), raw_ranked(), raw_section(), Result (+13 more)

### Community 4 - "Pipeline State Management"
Cohesion: 0.19
Nodes (6): DeliveryResult, FeishuDelivery, FakeResponse, FakeSession, test_send_post_targets_chat_with_post_payload(), test_send_targets_chat_id()

### Community 5 - "Feishu Delivery System"
Cohesion: 0.24
Nodes (14): DigestItem, compact_text(), render_digest(), render_fault_digest(), render_feishu_post(), render_feishu_section_posts(), _section_block(), test_compact_text_caps_output_at_100_characters() (+6 more)

### Community 6 - "Digest Rendering"
Cohesion: 0.18
Nodes (8): fallback_generation(), parse_generation(), MiniMaxGenerator, FakeCompletions, test_fallback_marks_english_translation_pending(), test_minimax_generator_uses_configured_model(), test_parse_generation_accepts_minimax_think_prefix(), test_parse_generation_rejects_non_json()

### Community 7 - "Content Clustering"
Cohesion: 0.27
Nodes (10): _collect_atom_releases(), collect_github_releases(), collect_github_repository_search(), RawItem, canonicalize_url(), normalize_raw_item(), normalize_text(), raw_item() (+2 more)

### Community 8 - "Text Generation"
Cohesion: 0.29
Nodes (12): Compact Feishu Post Design, Compact Feishu Post Implementation Plan, Daily AI Digest Project, Daily AI Digest Findings, Daily AI Digest Progress, Daily AI Digest Task Plan, Filters Configuration, Operations Document (+4 more)

### Community 9 - "Configuration Management"
Cohesion: 0.30
Nodes (10): NewsItem, dedupe_exact(), hard_filter(), tag_topics(), weighted_score(), item(), test_dedupe_exact_keeps_first_stable_item(), test_hard_filter_rejects_blocked_and_stale_items() (+2 more)

## Knowledge Gaps
- **11 isolated node(s):** `daily-ai-digest`, `run_daily.sh script`, `validate_config.sh script`, `graphify_refresh.sh script`, `Daily AI Digest README` (+6 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **18 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `run_daily()` connect `Digest Pipeline Stages` to `Application Configuration`, `Content Collection`, `Pipeline Components`?**
  _High betweenness centrality (0.112) - this node is a cross-community bridge._
- **Why does `RawItem` connect `Content Clustering` to `Application Configuration`, `Content Collection`?**
  _High betweenness centrality (0.042) - this node is a cross-community bridge._
- **Are the 18 inferred relationships involving `datetime` (e.g. with `test_digest_applies_top_story_quota_without_candidates()` and `test_digest_backfills_productivity_when_top_stories_are_short()`) actually correct?**
  _`datetime` has 18 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `run_daily()` (e.g. with `test_digest_applies_top_story_quota_without_candidates()` and `test_digest_backfills_productivity_when_top_stories_are_short()`) actually correct?**
  _`run_daily()` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `PipelineDependencies` (e.g. with `FakeCollector` and `FakeDelivery`) actually correct?**
  _`PipelineDependencies` has 14 INFERRED edges - model-reasoned connections that need verification._
- **What connects `daily-ai-digest`, `run_daily.sh script`, `validate_config.sh script` to the rest of the system?**
  _20 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Digest Pipeline Stages` be split into smaller, more focused modules?**
  _Cohesion score 0.13636363636363635 - nodes in this community are weakly interconnected._